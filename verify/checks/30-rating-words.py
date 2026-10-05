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

ANS_SHORT, ANS_FULL, OWN_FULL = 'author’s answer rated', 'The author’s answer to it:', 'Author’s rating:'
OWN_RE = re.compile(r"Author['’]s rating:")   # the index's section heading uses a straight apostrophe

def scan_answers(texts, alt):
    """The other-view arguments (front_door alternative.ids) show the claim they answer; their rating
    is the author's answer to it (Jon's "Firm?" threads, 2026-10-05). On their sheets the rating must say
    so, and no other sheet may; the board and The arguments carry one short answer label per id. True when clean."""
    bad, sheets = [], {k[6:]: t for k, t in texts.items() if k.startswith('sheet ')}
    for i, t in sheets.items():
        if i in alt and (t.count(ANS_FULL) < 2 or OWN_RE.search(t)):   # tag and section heading both
            bad.append(f'sheet {i}: other-view rating not framed as the answer')
        if i not in alt and ANS_FULL in t:
            bad.append(f'sheet {i}: framed as an answer but not in alternative.ids')
    bad += [f'sheet {i}: missing' for i in alt if i not in sheets]   # a sheet that never rendered must not pass
    labels = {v: texts.get(v, '').count(ANS_SHORT) for v in ('v-board', 'list argslist')}
    bad += [f'{v}: {n} short answer labels, expected {len(alt)}' for v, n in labels.items() if n != len(alt)]
    brief = texts.get('v-brief', '').count(ANS_FULL)   # In brief's "The other view, fairly stated" list
    if brief != len(alt):
        bad.append(f'v-brief: {brief} answer ratings, expected {len(alt)}')
    print(f'COUNT answer-framed sheets {sum(1 for i in alt if sheets.get(i, "").count(ANS_FULL) >= 2)}/{len(alt)} (tag and heading); '
          f'short labels board {labels["v-board"]}, The arguments {labels["list argslist"]}; In brief {brief} (expected {len(alt)} each)')
    for b in bad[:12]:
        print('SAMPLE ' + b)
    return not bad

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    # each planted label must be caught on its own, or one family could silently stop working
    planted = ["Author's rating: Strong", 'Precept · Use: Lead', 'Don’t push it ' + 'past this']
    caught = sum(1 for p in planted if not scan({'planted view': p}, {}))
    good = {'sheet G1': ANS_FULL + ' firm. ' + ANS_FULL + ' firm', 'sheet C4': OWN_FULL + ' firm',
            'v-board': ANS_SHORT + ' firm', 'list argslist': ANS_SHORT + ' firm', 'v-brief': ANS_FULL + ' firm'}
    broken = [dict(good, **{'sheet G1': OWN_FULL + ' firm'}), dict(good, **{'sheet C4': ANS_FULL + ' firm'}),
              dict(good, **{'v-board': 'rated firm'}), dict(good, **{'list argslist': ''}),
              {k: v for k, v in good.items() if k != 'sheet G1'}, dict(good, **{'sheet G1': 'rated firm'}),
              dict(good, **{'sheet G1': 'rated firm. ' + ANS_FULL + ' firm'}),
              dict(good, **{'sheet G1': ANS_FULL + ' firm. ' + ANS_FULL + " firm. Author's rating: firm"}),   # OWN_RE alone
              dict(good, **{'v-brief': 'rated firm'})]
    caught_ans = sum(1 for b in broken if not scan_answers(b, ['G1']))
    print(f'COUNT selftest planted {len(planted) + len(broken)}, caught {caught + caught_ans}')
    ok = (caught == len(planted) and caught_ans == len(broken) and scan_answers(good, ['G1'])
          and not scan({}, {'X1': 'Undecidable on causation'}))
    sys.exit(1 if ok else 0)

need_build()
M = json.load(open(os.path.join(ROOT, 'outputs', 'master.json'), encoding='utf-8'))
# the same list the template reads (F.alternative.ids); a missing section means no other-view arguments, as on the page
ALT = (json.load(open(os.path.join(ROOT, 'sources', 'front_door.json'), encoding='utf-8')).get('alternative') or {}).get('ids') or []
T = rendered()
clean = scan(T, {a['id']: a.get('lands_verdict') for a in M['arguments']})
sys.exit(0 if scan_answers(T, ALT) and clean else 1)
