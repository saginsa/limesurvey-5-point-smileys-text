#!/usr/bin/env bash
# Builds dist/5-Point-Smileys-Text-<version>.zip for "Upload & install" of question themes in LimeSurvey.
# The zip root holds survey/… (the theme) plus README, CHANGELOG and the licenses, as the theme folder on the server.
# LimeSurvey skips files with other extensions than its allowed theme uploads, so only those go in.
set -euo pipefail
cd "$(dirname "$0")/.."
name=5-Point-Smileys-Text
config=survey/questions/answer/5pointchoice/config.xml
version=$(sed -n 's:.*<version>\([0-9][0-9.]*\)</version>.*:\1:p' "$config" | head -1)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/$name" dist
cp -R survey README.md CHANGELOG.md LICENSE.txt LICENSE-fonts.txt "$tmp/$name/"
find "$tmp/$name" -name '.DS_Store' -delete
rm -f "dist/$name-$version.zip"
(cd "$tmp/$name" && COPYFILE_DISABLE=1 zip -qrX "$OLDPWD/dist/$name-$version.zip" .)
(cd dist && shasum -a 256 "$name-$version.zip" > "$name-$version.zip.sha256")
unzip -l "dist/$name-$version.zip"
cat "dist/$name-$version.zip.sha256"
