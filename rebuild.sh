#!/usr/bin/env bash
# Restore the layout the pipeline scripts expect, then build.
# On Windows:  PYTHONUTF8=1 WORK=$PWD/work OUT=$PWD/outputs ./rebuild.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-/home/claude}"; OUT="${OUT:-/mnt/user-data/outputs}"
export REPO="$HERE"     # check_drift looks for the private paper in docs/ or the folder .notes-expected names
mkdir -p "$WORK/bib" "$OUT/pipeline"
cp "$HERE"/sources/args.json "$HERE"/sources/front_door.json "$HERE"/sources/dependencies.json "$HERE"/sources/map_frame.txt "$WORK"/
for f in "$HERE"/pipeline/*; do if [ -f "$f" ]; then cp "$f" "$WORK"/; fi; done   # files only (skips __pycache__)
cp "$HERE"/kjv/*.json "$WORK/bib/"
cp "$HERE"/sources/argument-index.md "$OUT"/
if [ -d "$HERE/docs" ]; then cp "$HERE"/docs/*.md "$OUT"/; fi
chmod +x "$WORK/build_all.sh"
"$WORK/build_all.sh"
# master.json at the repo root is the committed copy of the generated master. Refresh it from
# this build so it can never go stale again (it had, until 2026-10-04). The gate's check 70
# compares the two byte for byte.
cp "$OUT/master.json" "$HERE/master.json"
