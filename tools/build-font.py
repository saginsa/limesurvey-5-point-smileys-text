#!/usr/bin/env python3
"""Builds the "Smileys Faces" font (five faces from Font Awesome Free, outline and solid) and puts it
into the stylesheet as two @font-face rules with inline woff2 (data: URIs).

    tools/build-font.py           rewrite the block between "font:begin" and "font:end" in smileys.css
    tools/build-font.py --check   exit 1 if the stylesheet is out of date (used by tests/static.sh)

Needs: pip install fonttools brotli. Downloads the pinned Font Awesome Free release (checked by sha256)
into tools/.cache/. Font Awesome Free fonts: SIL OFL 1.1 with the Reserved Font Name "Font Awesome",
so the subset is renamed. Copyright notice and license: LICENSE-fonts.txt.
"""
import base64
import hashlib
import io
import os
import re
import sys
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "survey/questions/answer/5pointchoice/assets/css/smileys.css")
CACHE = os.path.join(ROOT, "tools/.cache")
FA_VERSION = "6.7.2"
SOURCES = {
    # weight in CSS: (file in the Font Awesome Free package, sha256)
    400: ("fa-regular-400.ttf", "54cf6086f7bb21f9d072ad494a19b4681fa516dd0a14cee52da01d3651a913a3"),
    900: ("fa-solid-900.ttf", "d2f0593540b0e33ba6de255a54f272d466e31144806956bea8cfdbf7edffc9bd"),
}
# The characters the stylesheet uses (as in version 1.0) -> Font Awesome glyph
FACES = {
    0x1F620: "face-angry",   # 1 angry
    0x2639: "face-frown",    # 2 sad
    0x1F610: "face-meh",     # 3 neutral
    0x263A: "face-smile",    # 4 smile
    0x1F600: "face-grin",    # 5 happy
}
FAMILY = "Smileys Faces"
BLOCK = re.compile(r"(/\* font:begin[^*]*\*/\n)(.*?)(/\* font:end \*/)", re.S)


def source(name, sha):
    path = os.path.join(CACHE, FA_VERSION, name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        url = "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@%s/webfonts/%s" % (FA_VERSION, name)
        data = urllib.request.urlopen(url, timeout=60).read()
        with open(path, "wb") as f:
            f.write(data)
    data = open(path, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha:
        sys.exit("%s: sha256 %s, expected %s" % (name, digest, sha))
    return path


def build(weight):
    name, sha = SOURCES[weight]
    font = TTFont(source(name, sha))
    opts = subset.Options()
    opts.layout_features = []
    opts.name_IDs = []          # names are written below
    opts.notdef_outline = True
    opts.hinting = False
    opts.desubroutinize = True
    sub = subset.Subsetter(opts)
    sub.populate(glyphs=list(FACES.values()))
    sub.subset(font)
    # Exactly our characters, nothing else
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap = {cp: g for cp, g in FACES.items() if table.format != 4 or cp <= 0xFFFF}
    style = "Regular" if weight == 400 else "Solid"
    names = font["name"]
    names.names = []
    for nid, value in {
        0: "Copyright (c) 2024 Fonticons, Inc. (https://fontawesome.com). Subset of Font Awesome Free %s." % FA_VERSION,
        1: FAMILY if weight == 400 else FAMILY + " " + style,
        2: "Regular",
        3: "%s %s %s" % (FAMILY, style, FA_VERSION),
        4: "%s %s" % (FAMILY, style),
        5: "Version %s" % FA_VERSION,
        6: ("%s-%s" % (FAMILY, style)).replace(" ", ""),
        13: "SIL Open Font License, Version 1.1",
        14: "https://scripts.sil.org/OFL",
    }.items():
        names.setName(value, nid, 3, 1, 0x409)
    font.recalcTimestamp = False  # keep the dates of the source font: reproducible output
    font["OS/2"].usWeightClass = weight
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out, reorderTables=True)
    return out.getvalue()


def block():
    rules = []
    for weight in (400, 900):
        data = base64.b64encode(build(weight)).decode()
        rules.append('@font-face {\n    font-family: "%s";\n    font-style: normal;\n    font-weight: %d;\n'
                     '    font-display: block;\n    src: url("data:font/woff2;base64,%s") format("woff2");\n}'
                     % (FAMILY, weight, data))
    return "\n\n".join(rules) + "\n"


def main():
    css = open(CSS, encoding="utf-8").read()
    m = BLOCK.search(css)
    if not m:
        sys.exit("no font:begin / font:end block in " + CSS)
    new = css[:m.start(2)] + block() + css[m.end(2):]
    if "--check" in sys.argv:
        if new != css:
            print("smileys.css is out of date: run tools/build-font.py", file=sys.stderr)
            return 1
        return 0
    if new != css:
        open(CSS, "w", encoding="utf-8").write(new)
        print("updated " + os.path.relpath(CSS, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
