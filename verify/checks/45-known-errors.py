#!/usr/bin/env python3
"""45 known errors: a mistake CLAUDE.md lists as fixed ("do not let them regress") never comes back.

WHY: the list in CLAUDE.md is prose, and prose did not hold. On 2026-10-05 D4 still said "the
Westminster divines wrote a Directory for Family Worship" and its card said "Westminster produced"
one, though the list has said since 2026-10-04 that the General Assembly of the Church of Scotland
approved it. A rule that must always hold belongs in a check.

Each pattern below is one listed error, written narrowly enough that the correct statement passes
(the selftest proves both). Add a pattern when a listed error can be matched without false alarms.
Reads the manifest's public text files, minus generated master.json and this file.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT
from manifest import public_texts

_MK = r'[*_]{0,3}'   # Markdown emphasis around a title: italic, bold or both

ERRORS = {
    # CLAUDE.md: the Directory for Family Worship (24 Aug 1647) was approved by the General
    # Assembly of the Church of Scotland, not the Westminster divines.
    # "Westminster" directly before the verb (optionally "divines"/"Assembly"), so "the Assembly
    # that adopted the Westminster Confession, approved a Directory" stays legal; possessive and
    # Markdown-italic forms ("Westminster's *Directory for Family Worship*") are caught too.
    'Directory credited to Westminster': re.compile(
        # active: "the Westminster divines (also) wrote a/its (own) Directory"
        r"Westminster(?:\s+(?:divines|Assembly(?:\s+of\s+Divines)?))?\s+(?:also\s+)?(?:wrote|produced|issued|composed|"
        r"drafted|prepared|authored|framed|approved|adopted|gave\s+us)\s+(?:a|the|its)\s+(?:own\s+)?" + _MK +
        r"Directory\s+for\s+Family\s+Worship"
        # possessive or adjective: "Westminster's / the Westminster Assembly's / the divines' *Directory*"
        r"|Westminster(?:\s+(?:divines|Assembly(?:\s+of\s+Divines)?))?(?:['’]s?)?\s+" + _MK +
        r"Directory\s+for\s+Family\s+Worship"
        # passive: "a Directory for Family Worship written by the Westminster divines"
        r"|Directory\s+for\s+Family\s+Worship" + _MK + r"[^.\n]{0,40}?\b(?:written|produced|issued|composed|drafted|"
        r"prepared|authored|framed)\s+by\s+the\s+Westminster", re.I),
}
SKIP = {'master.json', 'verify/checks/45-known-errors.py'}

def scan(texts):
    hits = []
    for label, t in texts.items():
        for name, rx in ERRORS.items():
            for m in rx.finditer(t):
                hits.append(f'{label}:{t.count(chr(10), 0, m.start()) + 1} {name}: "{m.group(0)}"')
    print(f'COUNT known-error regressions {len(hits)} across {len(texts)} files ({len(ERRORS)} patterns)')
    for h in hits[:10]:
        print('SAMPLE ' + h)
    return not hits

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    planted = {'divines.md': 'Our own standards assume it: the Westminster divines wrote a Directory for Family Worship.',
               'produced.json': '"Westminster produced a Directory for Family Worship, so this is ours."',
               'named.md': 'See the Westminster Directory for Family Worship.',
               'possessive.md': "Westminster's *Directory for Family Worship* assumes it.",
               'italic.md': 'the Westminster *Directory for Family Worship* (1647)',
               'approved.md': 'the Westminster Assembly approved a Directory for Family Worship',
               'prepared.md': 'the Westminster divines prepared a Directory for Family Worship',
               'asmposs.md': "the Westminster Assembly's Directory for Family Worship",
               'divposs.md': 'the Westminster divines’ Directory for Family Worship',
               'also.md': 'the Westminster divines also wrote a Directory for Family Worship',
               'own.md': 'Westminster produced its own Directory for Family Worship',
               'ofdiv.md': 'the Westminster Assembly of Divines wrote a Directory for Family Worship',
               'passive.md': 'a Directory for Family Worship written by the Westminster divines',
               'bold.md': "Westminster's **Directory for Family Worship**"}
    caught = [k for k, v in planted.items() if not scan({k: v})]
    legal = {'g1.md': 'The General Assembly of the Church of Scotland approved a Directory for Family Worship on 24 August 1647.',
             'd4.md': 'the same Assembly that adopted the Westminster Confession, approved a Directory for Family Worship.',
             'texts.json': '"texts": "Baxter; BCO 8-3; Directory for Family Worship"',
             'd4card.json': '"The General Assembly of the Church of Scotland, which adopted the Westminster Confession, approved a Directory for Family Worship (1647)"',
             'nocomma.md': 'The General Assembly that adopted the Westminster Confession approved a Directory for Family Worship.',
             'list.md': 'The Directory for Family Worship (24 Aug 1647) was approved by the General Assembly of the Church of Scotland, not the Westminster divines.'}
    flagged = [k for k, v in legal.items() if not scan({k: v})]
    print(f'COUNT selftest planted {len(planted)}, caught {len(caught)}; legal {len(legal)}, flagged {len(flagged)}')
    sys.exit(1 if len(caught) == len(planted) and not flagged else 0)

texts = {k: v for k, v in public_texts(ROOT, exempt=True).items() if k not in SKIP and not k.startswith('kjv/')}
sys.exit(0 if scan(texts) else 1)
