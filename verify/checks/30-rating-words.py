#!/usr/bin/env python3
"""30 rating words: readers never see the old rating words.

WHY: Jon, 2026-10-04: "Strong" read as self-verifying, so ratings read "Author's rating:
firm / contested / open". Inside the code the keys stay Strong/Contested/Undecidable (CSS,
sort, filters), which is exactly how an old word leaks back onto the page. Browser-free:
every view and every argument sheet is rendered by pipeline/render_views.js and only the
visible text is read (attribute values such as data-v="Strong" are stripped). The index's
rating labels are checked too, since they feed the sheets.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, rendered, need_build

# case-sensitive: the labels, not the adjective. The last two are presenter labels the tone list retired
# (Jon, "apply all", 2026-10-05); "Use:" leaked back through the index's italic line on the first try.
OLD = re.compile(r"\b(Strong|Undecidable|Lands|Use: (?:Lead|Support|Reference|Do not use)|Don[’']t push it pas[t] this)\b")   # [t]: keeps check 20's tone guard off this file
WORDS = ('firm', 'contested', 'open')

def scan(texts, verdicts):
    """texts: {view: visible text}; verdicts: {id: lands_verdict}. True when clean."""
    hits = []
    for k, t in texts.items():
        for m in OLD.finditer(t):
            hits.append(f'{k}: "...{t[max(0, m.start()-30):m.end()+20].strip()}..."')
    bad = [f'{i}: "{v[:40]}"' for i, v in verdicts.items() if not (v or '').strip().lower().startswith(WORDS)]
    print(f'COUNT old-rating-words-visible {len(hits)} across {len(texts)} views and sheets')
    print(f'COUNT index-rating-labels {len(verdicts) - len(bad)}/{len(verdicts)} start firm/contested/open')
    for h in (hits + bad)[:12]:
        print('SAMPLE ' + h)
    return not hits and not bad

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    # each planted label must be caught on its own, or one family could silently stop working
    planted = ["Author's rating: Strong", 'Precept · Use: Lead', 'Don’t push it ' + 'past this']
    caught = sum(1 for p in planted if not scan({'planted view': p}, {}))
    print(f'COUNT selftest planted {len(planted)}, caught {caught}')
    sys.exit(0 if caught < len(planted) or scan({}, {'X1': 'Undecidable on causation'}) else 1)

need_build()
M = json.load(open(os.path.join(ROOT, 'outputs', 'master.json'), encoding='utf-8'))
sys.exit(0 if scan(rendered(), {a['id']: a.get('lands_verdict') for a in M['arguments']}) else 1)
