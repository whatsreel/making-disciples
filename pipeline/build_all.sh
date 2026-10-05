#!/usr/bin/env bash
# One command: sources -> master -> every view -> checks.
# Sources (hand-edited):  argument-index.md  args.json  front_door.json  dependencies.json
# Everything else is generated. Never hand-edit a generated file.
#
# FAILS LOUDLY (2026-10-04): every step prints its whole log when it fails, and the two checks
# at the end fail the build. Before, both checks ran under '|| true' and a failure printed one
# line while the build carried on to "done".
set -euo pipefail
WORK="${WORK:-/home/claude}"; OUT="${OUT:-/mnt/user-data/outputs}"; export WORK OUT
cd "$WORK"
LOG="$WORK/_logs"; mkdir -p "$LOG"

step() {  # step <log-name> <command...>: first line on success, whole log and exit 1 on failure
  local name="$1"; shift
  if "$@" > "$LOG/$name.log" 2>&1; then head -1 "$LOG/$name.log" | sed 's/^/   /'
  else echo "BUILD FAILED at $name:"; cat "$LOG/$name.log"; exit 1; fi
}

echo "1. master"
step master python3 build_master2.py
cp master.json "$OUT/master.json"

echo "2. spreadsheet"
step xlsx python3 gen_xlsx.py

echo "3. web page (both URLs publish the same file)"
step hubdata python3 gen_hub_data.py
python3 - <<'PY'
import os; W=os.environ['WORK']; O=os.environ['OUT']
tpl=open(W+'/hub_template.html',encoding='utf-8').read(); data=open(W+'/_hub_data.json',encoding='utf-8').read()
out=tpl.replace('__DATA__',data.replace('</script>','<\\/script>'))
for f in (O+'/argument-map.html',O+'/argument-hub.html'):
    open(f,'w',encoding='utf-8',newline='').write(out)  # newline='': no CRLF on Windows (smoke_hub.js matches '<script>\n')
print('   written', len(out), 'bytes')
PY

echo "4. PDFs"
# no-binary-check: pandoc/wkhtmltopdf are optional; the guard below prints a skip line when absent.
if command -v pandoc >/dev/null && command -v wkhtmltopdf >/dev/null; then
for doc in discipleship-session argument-index open-tasks; do
  if [ -f "$OUT/$doc.md" ]; then
    pandoc "$OUT/$doc.md" -s --css=style.css -o "/tmp/$doc.html" 2>/dev/null
    sed -i 's|<link rel="stylesheet" href="style.css" />|<style>'"$(tr '\n' ' ' < style.css)"'</style>|' "/tmp/$doc.html"
    wkhtmltopdf --enable-local-file-access --margin-top 18mm --margin-bottom 18mm --margin-left 18mm --margin-right 18mm \
      --footer-center '[page]' --footer-font-size 8 "/tmp/$doc.html" "$OUT/$doc.pdf" 2>/dev/null
    echo "   $doc.pdf $(pdfinfo "$OUT/$doc.pdf" | awk '/Pages/{print $2}')pp"
  fi
done
else echo "   (pandoc/wkhtmltopdf not installed - PDFs skipped; the page and spreadsheet are unaffected)"; fi

echo "5. checks"
rc=0
node smoke_hub.js > "$LOG/smoke.log" 2>&1 || rc=1; sed 's/^/   /' "$LOG/smoke.log"
python3 check_drift.py > "$LOG/drift.log" 2>&1 || rc=1; cat "$LOG/drift.log"
if [ "$rc" -ne 0 ]; then echo "BUILD FAILED: a check above failed."; exit 1; fi

mkdir -p "$OUT/pipeline"
for f in build_all.sh build_master2.py gen_xlsx.py gen_hub_data.py hub_template.html check_drift.py smoke_hub.js \
         render_views.js tone.py ratings.py paper.py manifest.py names.py falls.py front_door.json dependencies.json map_frame.txt; do
  if [ -f "$f" ]; then cp "$f" "$OUT/pipeline/"; fi
done
echo "done. publish $OUT/argument-map.html to the shared URL."
