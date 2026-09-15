#!/bin/sh
# Export one application folder's resume and cover letter to PDF with headless Chrome.
#
#   sh scripts/export-pdf.sh <application-folder> <Company-Role-slug> [full name]
#
# Produces <folder>/<slug>-<Name>.pdf and <folder>/<slug>-Cover-Letter-<Name>.pdf and prints page counts.
# Set CHROME to your Chrome/Chromium binary if it is not found automatically.

set -e
DIR="$1"; SLUG="$2"; NAME="${3:-Resume}"
[ -d "$DIR" ] || { echo "usage: $0 <application-folder> <slug> [name]" >&2; exit 2; }
NAME_SAFE="$(printf '%s' "$NAME" | tr ' ' '-')"

if [ -z "$CHROME" ]; then
  for c in "/c/Program Files/Google/Chrome/Application/chrome.exe" \
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "$(command -v google-chrome 2>/dev/null)" "$(command -v chromium 2>/dev/null)" "$(command -v chromium-browser 2>/dev/null)"; do
    [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
  done
fi
[ -n "$CHROME" ] || { echo "Chrome not found; set CHROME=/path/to/chrome" >&2; exit 2; }

abs() { case "$1" in /*) printf '%s' "$1" ;; *) printf '%s/%s' "$(pwd)" "$1" ;; esac; }
DIR_ABS="$(abs "$DIR")"
if command -v cygpath >/dev/null 2>&1; then DIR_URL="$(cygpath -m "$DIR_ABS")"; else DIR_URL="$DIR_ABS"; fi
pages() { grep -a -o '/Count [0-9]*' "$1" | head -1 | sed 's#/Count ##'; }

TMP="$(mktemp -d)"
# Resume: rewrite the relative stylesheet link so headless Chrome resolves it from the temp copy.
sed "s#href=\"\.\./resume\.css\"#href=\"file:///$DIR_URL/../resume.css\"#" "$DIR/01-Resume.html" > "$TMP/resume.html"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$DIR_ABS/$SLUG-$NAME_SAFE.pdf" "file:///$( [ -n "$(command -v cygpath)" ] && cygpath -m "$TMP" || printf '%s' "$TMP")/resume.html" >/dev/null 2>&1
echo "resume: $(pages "$DIR/$SLUG-$NAME_SAFE.pdf") page(s)"

# Cover letter: the Markdown body after the first '---' rule becomes paragraphs.
{
  cat <<'H'
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Cover Letter</title><style>
@page{size:letter portrait;margin:0.7in 0.8in}
body{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;font-size:10pt;line-height:1.4;color:#222;margin:0}
p{margin:0 0 8pt 0}
</style></head><body>
H
  awk 'f{print} /^---$/{f=1}' "$DIR/02-Cover-Letter.md" \
    | awk 'BEGIN{RS="";ORS="\n"} {gsub(/\n/," "); gsub(/\*\*([^*]+)\*\*/,"<b>&</b>"); gsub(/\*\*/,""); print "<p>"$0"</p>"}'
  echo '</body></html>'
} > "$TMP/letter.html"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$DIR_ABS/$SLUG-Cover-Letter-$NAME_SAFE.pdf" "file:///$( [ -n "$(command -v cygpath)" ] && cygpath -m "$TMP" || printf '%s' "$TMP")/letter.html" >/dev/null 2>&1
echo "letter: $(pages "$DIR/$SLUG-Cover-Letter-$NAME_SAFE.pdf") page(s)"
rm -rf "$TMP"
