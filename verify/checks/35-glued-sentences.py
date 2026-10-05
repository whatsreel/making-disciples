#!/usr/bin/env python3
"""35 glued sentences: no two sentences run together without a space ("page.Carried").

WHY: on 2026-10-04 an edit to front_door.json dropped the space after a period and every
other check passed; a code review caught it. This reads the visible text of every view and
argument sheet (pipeline/render_views.js, attributes stripped).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import rendered, need_build

GLUED = re.compile(r'\b[a-z]{2,}[.!?;:][A-Z][a-z]')

def scan(texts):
    hits = []
    for k, t in texts.items():
        for m in GLUED.finditer(t):
            hits.append(f'{k}: "...{t[max(0, m.start()-25):m.end()+15].strip()}..."')
    print(f'COUNT glued-sentences {len(hits)} across {len(texts)} views and sheets')
    for h in hits[:10]:
        print('SAMPLE ' + h)
    return not hits

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    sys.exit(0 if scan({'planted': 'The strongest case on this page.Carried by precept'}) else 1)

need_build()
sys.exit(0 if scan(rendered()) else 1)
