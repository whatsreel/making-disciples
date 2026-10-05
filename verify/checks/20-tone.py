#!/usr/bin/env python3
"""20 tone: no advocate-vs-adversary phrase in any public file or on the page.

WHY: the audience is the whole session, elders holding either view in good faith, and the
repo is going public. Two them-vs-us phrases reached the live page on 2026-10-04 (fixed in
276d5e6). This scans every text file in public_manifest.txt and the built page's visible
text, with the one regex in pipeline/tone.py. A keyword list cannot judge tone: before the
first public push a person reads every public file as well (plan of record, chunk C).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, rendered, need_build
import tone
from manifest import public_files as manifest, read_texts   # one reading of the manifest, shared with checks 25/50 and the export

def scan(texts):
    """texts: {label: text}. Prints COUNT/SAMPLE; returns True when clean."""
    found = []
    for label, txt in texts.items():
        for line, phrase in tone.hits(txt):
            found.append(f'{label}:{line} "{phrase}"')
    print(f'COUNT tone-hits {len(found)} across {len(texts)} files/views')
    for f in found[:15]:
        print('SAMPLE ' + f)
    return not found

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    # one planted line per phrase family; EACH must be caught on its own (round 14 of the chunk E
    # review found the A5 phrases were added to the guard with no selftest able to show they work)
    planted = ['our ' + 'side should answer ' + 'their ' + 'side',
               'his example can be ' + 'declined wholesale', 'declining it ' + 'wholesale',
               'an elder may decline ' + 'that whole category', 'decline to treat ' + "Christ's example",
               'holds even if it is set ' + 'aside entirely', 'set it ' + 'aside entirely',
               'set entirely ' + 'aside', 'survives if his ' + 'practice is set aside',
               'state it well or ' + 'lose the room', "don’t " + 'push it past this', 'in order to ' + 'win a point',
               'two of them will ' + 'damage us', 'it ' + 'buys credibility', 'a ' + 'thumb on the scale',
               'say so ' + 'before anyone else does', 'has ' + 'lost before starting']
    missed = [p for p in planted if not tone.hits(p)]
    print(f'COUNT selftest planted {len(planted)}, caught {len(planted) - len(missed)}')
    for p in missed:
        print(f'SAMPLE missed: "{p}"')
    sys.exit(0 if missed else 1)   # exit 0 = something slipped = the runner fails this check

need_build()
files, exempt = manifest(ROOT)
texts = read_texts(files, ROOT)
for k, v in rendered().items():
    texts['page ' + k] = v
print(f'COUNT public-files scanned {len(files)}; exempt {len(exempt)} (Scripture, the guard itself)')
sys.exit(0 if scan(texts) else 1)
