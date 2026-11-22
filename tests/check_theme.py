#!/usr/bin/env python3
"""Static checks of the theme files (standard library only). Prints ok/FAIL lines, exits 1 on a failure."""
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(ROOT, "survey/questions/answer/5pointchoice")
CSS = os.path.join(THEME, "assets/css/smileys.css")
# The files LimeSurvey accepts in a theme upload (allowedthemeuploads + image formats) that we use
ALLOWED = {".xml", ".twig", ".css", ".png"}
failed = False


def result(cond, what, detail=None):
    global failed
    if cond:
        print("ok    " + what)
    else:
        failed = True
        print("FAIL  " + what + ("" if detail is None else "\n      " + str(detail)))


# ---- config.xml
config = ET.parse(os.path.join(THEME, "config.xml")).getroot()
meta = config.find("metadata")
missing = [f for f in ("name", "type", "title", "version", "author", "license", "description", "questionType")
           if not (meta.findtext(f) or "").strip()]
result(not missing, "config.xml: required metadata", missing)
result(meta.findtext("name") == "5-Point-Smileys-Text", "config.xml: name is 5-Point-Smileys-Text")
result(meta.findtext("type") == "question_theme" and meta.findtext("questionType") == "5",
       "config.xml: question theme for type 5")
result(len(config.findall("compatibility/version")) > 0, "config.xml: compatibility")
version = meta.findtext("version")
result(re.fullmatch(r"\d+\.\d+\.\d+", version or "") is not None, "config.xml: version x.y.z", version)
changelog = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
result(re.search(r"^## %s\b" % re.escape(version), changelog, re.M) is not None, "CHANGELOG has %s" % version)
for f in config.findall("files/css/filename") + config.findall("files/preview/filename"):
    path = os.path.join(THEME, "assets", f.text.strip())
    result(os.path.isfile(path), "config.xml: file exists: " + f.text.strip())
email = meta.findtext("authorEmail")
result(not email, "config.xml: no author e-mail (public metadata)", email)

# ---- file types in the theme folder
bad = []
for d, _, files in os.walk(THEME):
    for f in files:
        if os.path.splitext(f)[1].lower() not in ALLOWED and f != ".DS_Store":
            bad.append(os.path.relpath(os.path.join(d, f), ROOT))
result(not bad, "theme files have extensions LimeSurvey accepts in uploads", bad)

# ---- Twig templates
for name in ("answer.twig", "rows/item_row.twig"):
    text = open(os.path.join(THEME, name), encoding="utf-8").read()
    result(text.count("{{") == text.count("}}") and text.count("{%") == text.count("%}")
           and text.count("{#") == text.count("#}"), name + ": balanced Twig tags")
    result("|raw" not in text.replace(" ", ""), name + ": no |raw (output stays escaped)")
    result(not re.search(r'=\{\{', text), name + ": attribute values are quoted")

# ---- CSS
css = open(CSS, encoding="utf-8").read()
plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
plain_no_data = re.sub(r'url\("data:[^"]*"\)', "url()", plain)
result(plain.count("{") == plain.count("}"), "smileys.css: balanced braces")
result("@import" not in plain and "@font-face" not in plain, "smileys.css: no @import, no web fonts")
external = re.findall(r"url\((?!\))[^)]*\)", plain_no_data)
result(not external, "smileys.css: no url() besides inline data: icons", external)
result("!important" not in plain, "smileys.css: no !important (survey themes can override)")

# Every selector must be inside .smiley-list, so the theme does not change other questions on the page
selectors = []
for block in re.finditer(r"([^{}]+)\{", re.sub(r"@media[^{]*\{", "", plain_no_data)):
    for sel in block.group(1).split(","):
        sel = sel.strip()
        if sel:
            selectors.append(sel)
unscoped = [s for s in selectors if not s.startswith(".smiley-list")]
result(selectors and not unscoped, "smileys.css: %d selectors, all start with .smiley-list" % len(selectors), unscoped)

# The icons in the CSS are well-formed SVG
icons = re.findall(r'url\("data:image/svg\+xml,([^"]*)"\)', css)
result(len(icons) == 10, "smileys.css: 10 inline icons", len(icons))
import urllib.parse  # noqa: E402
broken = []
for i, data in enumerate(icons):
    try:
        ET.fromstring(urllib.parse.unquote(data))
    except ET.ParseError as e:
        broken.append((i, str(e)))
result(not broken, "smileys.css: inline icons parse as XML", broken)

sys.exit(1 if failed else 0)
