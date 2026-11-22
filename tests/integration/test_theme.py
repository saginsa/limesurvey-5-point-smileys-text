#!/usr/bin/env python3
"""Integration scenarios for the 5-Point-Smileys-Text question theme (run by run.sh; standard library only).

The containers come from docker-compose.yml: LimeSurvey is installed, the theme is not.
Steps go in order and share state; the first failure stops the run.
"""
import html.parser
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = ["docker", "compose", "-f", os.path.join(HERE, "docker-compose.yml")]
ROOT_URL = "http://localhost:%s" % os.environ.get("SMILEYS_PORT", "8098")
BASE = ROOT_URL + "/index.php"
ZIP = os.environ["SMILEYS_ZIP"]
VERSION = os.environ["SMILEYS_VERSION"]
ADMIN, PASSWORD = "admin", os.environ.get("SMILEYS_ADMIN_PASSWORD", "Smileys-test-2026")
THEME = "5-Point-Smileys-Text"
THEME_DIR = "/var/www/html/upload/themes/question/" + THEME
passed = 0


# ---------------------------------------------------------------- helpers

def step(title):
    print("\n== " + title, flush=True)


def check(cond, what, detail=None):
    global passed
    if not cond:
        print("FAIL  " + what + ("" if detail is None else "\n      " + str(detail)[:2000]))
        sys.exit(1)
    passed += 1
    print("ok    " + what)


def sh(args, stdin=None):
    r = subprocess.run(args, input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("%s\n%s%s" % (" ".join(args), r.stdout, r.stderr))
    return r.stdout


def sql(query):
    """Runs SQL in the test database, returns rows as lists of strings (NULL -> None)."""
    out = sh(COMPOSE + ["exec", "-T", "db", "mysql", "--default-character-set=utf8mb4", "-ulimesurvey", "-plimesurvey", "-N", "-B", "limesurvey"],
             stdin=query)
    return [[None if v == "NULL" else v for v in line.split("\t")] for line in out.splitlines()]


def scalar(query):
    rows = sql(query)
    return rows[0][0] if rows else None


def web_sh(command):
    return sh(COMPOSE + ["exec", "-T", "-u", "www-data", "web", "sh", "-c", command])


jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def http(url, data=None, headers=None):
    """Returns (status, final url, body)."""
    req = urllib.request.Request(url if url.startswith("http") else BASE + url, data=data, headers=headers or {})
    try:
        r = opener.open(req, timeout=120)
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.geturl(), e.read().decode("utf-8", "replace")


def csrf(page):
    m = re.search(r'name="YII_CSRF_TOKEN"[^>]*value="([^"]+)"', page) or \
        re.search(r'value="([^"]+)"[^>]*name="YII_CSRF_TOKEN"', page)
    if not m:
        raise RuntimeError("no CSRF token on the page")
    return m.group(1)


def post_form(url, fields):
    return http(url, urllib.parse.urlencode(fields).encode(), {"Content-Type": "application/x-www-form-urlencoded"})


def post_multipart(url, fields, file_field, filename, content):
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode())
    parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                  'Content-Type: application/zip\r\n\r\n' % (boundary, file_field, filename)).encode())
    parts.append(content + b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode())
    return http(url, b"".join(parts), {"Content-Type": "multipart/form-data; boundary=" + boundary})


def login():
    jar.clear()
    _, _, page = http("/admin/authentication/sa/login")
    _, _, body = post_form("/admin/authentication/sa/login", {
        "YII_CSRF_TOKEN": csrf(page), "authMethod": "Authdb", "user": ADMIN, "password": PASSWORD,
        "loginlang": "default", "action": "login", "width": "1600", "login_submit": "login"})
    return "authentication/sa/logout" in body


def rpc(method, *params):
    body = json.dumps({"method": method, "params": list(params), "id": 1}).encode()
    # Own request without cookies: RemoteControl would replace the admin's browser session
    req = urllib.request.Request(BASE + "/admin/remotecontrol", body, {"Content-Type": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=300).read().decode())
    if data.get("error"):
        raise RuntimeError("%s: %s" % (method, data["error"]))
    return data["result"]


def upload_theme():
    _, _, page = http("/admin/themes/sa/upload")
    with open(ZIP, "rb") as f:
        return post_multipart("/admin/themes/sa/upload", {
            "YII_CSRF_TOKEN": csrf(page), "action": "templateupload", "theme": "question"},
            "the_file", os.path.basename(ZIP), f.read())


class Page(html.parser.HTMLParser):
    """Collects the elements of a survey page we look at: inputs, labels, list items, stylesheets."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.inputs, self.items, self.labels, self.css, self.lists = [], [], {}, [], []
        self._label = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        a["_tag"] = tag
        if tag == "input":
            self.inputs.append(a)
        elif tag == "li" and "smiley-item" in a.get("class", ""):
            self.items.append(a)
        elif tag == "ul" and "smiley-list" in a.get("class", ""):
            self.lists.append(a)
        elif tag == "link" and a.get("rel") == "stylesheet":
            self.css.append(a.get("href", ""))
        elif tag == "label" and a.get("for"):
            self._label = a["for"]
            self.labels[self._label] = ""

    def handle_endtag(self, tag):
        if tag == "label":
            self._label = None

    def handle_data(self, data):
        if self._label:
            self.labels[self._label] += data


def survey_page(sid, extra=""):
    jar.clear()
    status, _, body = http("/%d?newtest=Y&lang=en%s" % (sid, extra))
    return status, body, Page(body)


def submit(page_html, answers):
    """Submits the survey form: its own hidden fields plus the given answers."""
    p = Page(page_html)
    fields = {}
    for i in p.inputs:
        if i.get("type") == "hidden" and i.get("name") and "disabled" not in i:
            fields[i["name"]] = i.get("value", "")
    fields.update(answers)
    fields["move"] = "movesubmit"
    m = re.search(r'<form[^>]+id="limesurvey"[^>]+action="([^"]+)"', page_html)
    action = m.group(1).replace("&amp;", "&") if m else BASE
    return post_form(action if action.startswith("http") else ROOT_URL + action, fields)


# ---------------------------------------------------------------- scenarios

step("Admin login")
check(login(), "logged in as admin")

step("Upload & install the theme zip")
status, _, body = upload_theme()
check(status == 200, "upload answered 200", status)
row = sql("SELECT name, version, question_type, extends, visible, author, xml_path FROM lime_question_themes "
          "WHERE name = '%s'" % THEME)
check(len(row) == 1, "theme registered in lime_question_themes", row)
name, version, qtype, extends, visible, author, xml_path = row[0]
check(version == VERSION, "version %s" % VERSION, version)
check(qtype == "5" and extends == "5", "theme for question type 5 (5 point choice)", (qtype, extends))
check(visible == "Y", "theme visible in the question type selector", visible)
check(author == "saginsa", "author from config.xml", author)
files = web_sh("cd %s && find . -type f | sort" % THEME_DIR).split()
for f in ["./survey/questions/answer/5pointchoice/config.xml",
          "./survey/questions/answer/5pointchoice/answer.twig",
          "./survey/questions/answer/5pointchoice/rows/item_row.twig",
          "./survey/questions/answer/5pointchoice/assets/css/smileys.css",
          "./survey/questions/answer/5pointchoice/assets/images/preview.png",
          "./README.md", "./LICENSE.txt"]:
    check(f in files, "installed " + f, files)

step("Survey with two 5 point choice questions on the theme")
sql("DELETE FROM lime_settings_global WHERE stg_name = 'RPCInterface';\n"
    "INSERT INTO lime_settings_global (stg_name, stg_value) VALUES ('RPCInterface', 'json');")
key = rpc("get_session_key", ADMIN, PASSWORD)
sid = int(rpc("add_survey", key, 0, "Smileys test", "en", "A"))
gid = int(rpc("add_group", key, sid, "Group 1", ""))
# Q1 optional (gets "No answer"), Q2 mandatory; Q3 a core 5 point choice for comparison
for order, (title, mandatory, theme) in enumerate([("Q1", "N", THEME), ("Q2", "Y", THEME), ("Q3", "N", "5pointchoice")]):
    sql("INSERT INTO lime_questions (sid, gid, type, title, mandatory, question_order, question_theme_name, "
        "relevance, encrypted) VALUES (%d, %d, '5', '%s', '%s', %d, '%s', '1', 'N');\n"
        "INSERT INTO lime_question_l10ns (qid, question, help, language) "
        "VALUES (LAST_INSERT_ID(), 'How was %s?', '', 'en');" % (sid, gid, title, mandatory, order, theme, title))
qids = {t: int(q) for t, q in sql("SELECT title, qid FROM lime_questions WHERE sid = %d" % sid)}
res = rpc("activate_survey", key, sid)
check(isinstance(res, dict) and res.get("status") == "OK", "survey activated", res)
# LimeSurvey 7: lime_responses_<sid>; LimeSurvey 6: lime_survey_<sid>
table = scalar("SELECT table_name FROM information_schema.tables WHERE table_schema = 'limesurvey' "
               "AND table_name IN ('lime_responses_%d', 'lime_survey_%d')" % (sid, sid))
check(table is not None, "response table created", table)
cols = [r[0] for r in sql("SELECT column_name FROM information_schema.columns WHERE table_schema = 'limesurvey' "
                          "AND table_name = '%s'" % table)]
column = {}
for t, q in qids.items():
    match = [c for c in cols if re.fullmatch(r"(%dX%dX%d|Q%d)" % (sid, gid, q, q), c)]
    check(len(match) == 1, "response column for %s" % t, cols)
    column[t] = match[0]

step("Survey page: markup of the theme")
status, page_html, page = survey_page(sid)
check(status == 200, "survey page answered 200", status)
check("smiley-list" in page_html, "theme template used (smiley-list)")
check(len(page.lists) == 2, "two questions on the theme, the core question not", len(page.lists))
for ul in page.lists:
    check(ul.get("role") == "radiogroup" and ul.get("aria-labelledby", "").startswith("ls-question-text-"),
          "list is a labelled radiogroup", ul)
radios = {}
for i in page.inputs:
    if i.get("type") == "radio":
        radios.setdefault(i["name"], []).append(i)
q1 = [n for n in radios if n.endswith(str(qids["Q1"]))]
q2 = [n for n in radios if n.endswith(str(qids["Q2"]))]
check(len(q1) == 1 and len(q2) == 1, "radio groups of Q1 and Q2", list(radios))
q1, q2 = q1[0], q2[0]
check([r["value"] for r in radios[q1]] == ["1", "2", "3", "4", "5", ""], "Q1: five faces and \"No answer\"",
      [r["value"] for r in radios[q1]])
check([r["value"] for r in radios[q2]] == ["1", "2", "3", "4", "5"], "Q2 (mandatory): five faces, no \"No answer\"",
      [r["value"] for r in radios[q2]])
q1_items = [i for i in page.items if i["id"].startswith("javatbd" + q1 + "_C")]
for n in range(1, 6):
    cls = q1_items[n - 1]["class"].split()
    check({"answer-item", "radio-item", "smiley-item", "smiley-face", "smiley-item-%d" % n} <= set(cls),
          "face %d has its classes" % n, cls)
    check(page.labels.get("answer%s%d" % (q1, n), "").strip() == str(n), "face %d label text for screen readers" % n,
          page.labels.get("answer%s%d" % (q1, n)))
noanswer = q1_items[5]["class"].split()
check("noanswer-item" in noanswer and "smiley-face" not in noanswer, "\"No answer\" is not drawn as a face", noanswer)
check(page.labels.get("answer" + q1, "").strip() == "No answer", "\"No answer\" keeps its visible text",
      page.labels.get("answer" + q1))
check(not any("checked" in r for r in radios[q1][:5] + radios[q2]), "nothing preselected")
java = [i for i in page.inputs if i.get("id") == "java" + q1]
check(java and java[0].get("value") == "" and "disabled" in java[0], "hidden java<SGQA> input quoted and empty", java)

step("Stylesheet of the theme")
css_urls = [u for u in page.css if "smileys.css" in u]
check(len(css_urls) == 1, "smileys.css linked once", page.css)
status, _, css = http(urllib.parse.urljoin(ROOT_URL + "/", css_urls[0]))
check(status == 200, "smileys.css answered 200", status)
check("--smiley-icon-5-selected" in css and "mask" in css, "icons and masks in the served stylesheet")
outside_data = re.sub(r'url\("data:[^"]*"\)', "", css)
check("url(" not in outside_data, "no url() besides inline data: icons (no requests to other sites)",
      re.findall(r"url\([^)]*\)", outside_data))
check("@font-face" not in css, "no web fonts")

step("Mandatory question: submitting without an answer stays on the page")
status, _, body = submit(page_html, {q1: "4"})
check(status == 200, "submit answered 200", status)
check(scalar("SELECT COUNT(*) FROM %s WHERE submitdate IS NOT NULL" % table) == "0",
      "no complete response")
check("smiley-list" in body and re.search(r"mandatory|required", body, re.I), "page shown again with the error")
check(re.search(r'id="answer%s4"[^>]*checked' % re.escape(q1), body, re.I) is not None,
      "Q1 answer kept and shown as selected")

step("Submit answers")
status, _, body = submit(body, {q1: "4", q2: "2"})
check(status == 200, "submit answered 200", status)
row = sql("SELECT `%s`, `%s`, submitdate IS NOT NULL FROM %s" % (column["Q1"], column["Q2"], table))
check(len(row) == 1 and row[0] == ["4", "2", "1"], "response saved: Q1=4, Q2=2, complete", row)

step("Prefilled answer from the URL is shown as selected")
status, page_html, page = survey_page(sid, "&Q1=5")
selected = [r["value"] for r in page.inputs if r.get("name") == q1 and "checked" in r]
check(selected == ["5"], "Q1 face 5 selected", selected)
java = [i for i in page.inputs if i.get("id") == "java" + q1]
check(java and java[0].get("value") == "5", "java<SGQA> holds the value", java)

step("Upload the zip again: update in place")
check(login(), "logged in as admin")
status, _, _ = upload_theme()
check(status == 200, "second upload answered 200", status)
check(scalar("SELECT COUNT(*) FROM lime_question_themes WHERE name = '%s'" % THEME) == "1", "still one theme row")
status, page_html, _ = survey_page(sid)
check(status == 200 and "smiley-list" in page_html, "survey still renders with the theme")

print("\n%d checks passed" % passed)
