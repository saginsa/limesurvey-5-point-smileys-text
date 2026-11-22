#!/usr/bin/env python3
"""Puts the icons from tools/icons/*.svg into the stylesheet as CSS variables (data: URIs).

    tools/build-css.py           rewrite the block between "icons:begin" and "icons:end"
    tools/build-css.py --check   exit 1 if the stylesheet is out of date (used by tests/static.sh)
"""
import glob
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "survey/questions/answer/5pointchoice/assets/css/smileys.css")
ICONS = os.path.join(ROOT, "tools/icons")
BLOCK = re.compile(r"(/\* icons:begin[^*]*\*/\n)(.*?)(\s*/\* icons:end \*/)", re.S)


def data_uri(path):
    svg = open(path, encoding="utf-8").read().strip()
    ET.fromstring(svg)  # must be well-formed XML
    svg = svg.replace('"', "'")
    return "url(\"data:image/svg+xml," + urllib.parse.quote(svg, safe=" '=:/;,.-()") + "\")"


def block():
    lines = []
    for path in sorted(glob.glob(os.path.join(ICONS, "*.svg"))):
        m = re.fullmatch(r"([1-5])-[a-z]+(-selected)?\.svg", os.path.basename(path))
        if not m:
            sys.exit("unexpected icon file name: " + path)
        name = "--smiley-icon-%s%s" % (m.group(1), m.group(2) or "")
        lines.append("    %s: %s;" % (name, data_uri(path)))
    if len(lines) != 10:
        sys.exit("expected 10 icons (5 faces, idle and selected), found %d" % len(lines))
    return "\n".join(lines)


def main():
    css = open(CSS, encoding="utf-8").read()
    m = BLOCK.search(css)
    if not m:
        sys.exit("no icons:begin / icons:end block in " + CSS)
    new = css[:m.start(2)] + block() + css[m.end(2):]
    if "--check" in sys.argv:
        if new != css:
            print("smileys.css is out of date: run tools/build-css.py", file=sys.stderr)
            return 1
        return 0
    if new != css:
        open(CSS, "w", encoding="utf-8").write(new)
        print("updated " + os.path.relpath(CSS, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
