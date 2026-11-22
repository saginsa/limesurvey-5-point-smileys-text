#!/usr/bin/env bash
# Static checks: config.xml, templates, stylesheet, generated icons, forbidden words / secrets, spelling.
# Needs: python3; optionally codespell (always in CI).
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0
ok()  { printf 'ok    %s\n' "$1"; }
bad() { printf 'FAIL  %s\n' "$1"; fail=1; }

# 1. Theme files: config.xml, Twig, CSS scoping, inline icons
python3 tests/check_theme.py || fail=1

# 2. The stylesheet is generated from tools/icons
if tools/build-css.py --check; then ok "smileys.css up to date with tools/icons"; else bad "smileys.css out of date"; fi

# 3. Python of the tests and tools compiles
if python3 -m py_compile tools/build-css.py tests/check_theme.py tests/integration/test_theme.py; then
    ok "python compiles"; else bad "python compiles"; fi

# 4. No company names, internal hosts or secrets in tracked files
files=$(git ls-files 2>/dev/null || find . -type f -not -path './.git/*' -not -path './dist/*')
# FORBIDDEN_WORDS="word1|word2" — e.g. company or host names that must not get into the public code
if [ -n "${FORBIDDEN_WORDS:-}" ]; then
    if grep -I -i -n -E "$FORBIDDEN_WORDS" $files; then bad "forbidden words"; else ok "no forbidden words"; fi
fi
if grep -I -n -E '(BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|password *= *["'\''][^"'\'' ]+)' $files \
    | grep -v '^tests/' ; then bad "possible secrets"; else ok "no secrets"; fi
if grep -I -n -E '\b10\.[0-9]+\.[0-9]+\.[0-9]+\b|\b192\.168\.[0-9]+\.[0-9]+' $files | grep -v '^tests/'; then bad "private IPs"; else ok "no private IPs"; fi
if grep -I -n -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' $files | grep -v -E '^(tests/|LICENSE)' | grep -v 'noreply'; then
    bad "e-mail addresses"; else ok "no e-mail addresses"; fi

# 5. Spelling, with the LimeSurvey core settings (optional locally, always in CI)
if command -v codespell >/dev/null; then
    if codespell --builtin clear,rare --check-filenames survey tools tests README.md CHANGELOG.md \
        --skip '*.png'; then ok "codespell"; else bad "codespell"; fi
else
    echo "skip  codespell (not installed)"
fi

exit $fail
