#!/usr/bin/env python3
"""40 every argument rated: each argument's rating maps to firm, contested or open.

WHY: the page sorts, filters and colors by rating; an unrated argument silently drops out
of every filter. Uses pipeline/ratings.py, the same function the build uses, so the gate
and the build cannot disagree about what counts as rated.
"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, need_build
from ratings import verdict_short, WORD

def scan(verdicts):
    keys = {i: verdict_short(v) for i, v in verdicts.items()}
    unrated = sorted(i for i, k in keys.items() if k == 'Unrated')
    tally = collections.Counter(WORD.get(k, k) for k in keys.values())
    print(f'COUNT rated {len(keys) - len(unrated)}/{len(keys)} ({", ".join(f"{k} {n}" for k, n in sorted(tally.items()))})')
    for i in unrated[:10]:
        print(f'SAMPLE unrated {i}: "{(verdicts[i] or "")[:50]}"')
    return bool(keys) and not unrated

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    sys.exit(0 if scan({'A1': 'firm', 'Z9': 'Persuasive, mostly'}) else 1)

need_build()
M = json.load(open(os.path.join(ROOT, 'outputs', 'master.json'), encoding='utf-8'))
sys.exit(0 if scan({a['id']: a.get('lands_verdict') for a in M['arguments']}) else 1)
