#!/usr/bin/env python3
"""Positions word (check 32): the page calls its entries "positions", never "arguments".

WHY: Jon, 2026-10-05, on the footer's count of arguments: "I don't like this word. too combative."
He chose "positions" (option 1 of positions / points / lines of reasoning). The word keeps an
honest use inside the entries' own prose, where it means a line of reasoning ("a lexical
argument", "Bruce argues"). So this check reads the places the page's own wording comes from,
not the rendered text: the template (every label, heading, placeholder, aria-label and count
line), and the visible fields of front_door.json and dependencies.json. The word may not appear
in any of them, except the one chat instruction that names it to forbid it.
Not scanned: keys starting with "_" (editor notes, never shown) and dependencies' "why" fields,
which are verbatim quotes of the index (gate check 80 holds them to it).
(Two earlier versions read the rendered page and either covered only the plural, or allowed any
phrase also found in the prose; code review showed chrome regressions passing both.)
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT

WORD = re.compile(r'\barguments?\b', re.I)   # any case: '=== THE ARGUMENTS ===' was in the chat prompt
TEMPLATE_ALLOWED = ['Call the entries positions, never arguments.']   # the chat instruction forbids the word by naming it

def scan_template(src):
    for a in TEMPLATE_ALLOWED:
        src = src.replace(a, '')
    return [f'template: "...{src[max(0, m.start()-40):m.end()+20].strip()}..."' for m in WORD.finditer(src)]

def scan_json(name, obj, skip=('why',)):
    hits = []
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.startswith('_') or k in skip:
                    continue
                walk(v, f'{path}.{k}')
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f'{path}[{i}]')
        elif isinstance(o, str):
            for m in WORD.finditer(o):
                hits.append(f'{name}{path}: "...{o[max(0, m.start()-40):m.end()+20]}..."')
    walk(obj, '')
    return hits

def report(hits, scanned):
    print(f'COUNT entries-called-arguments {len(hits)} in {scanned} (template, front_door.json, dependencies.json)')
    for h in hits[:12]:
        print('SAMPLE ' + h)
    return not hits

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    planted = [("t", "'<h2>The arguments</h2>'"), ("t", "placeholder=\"Ask about any argument\""),
               ("t", "aria-label=\"Search the arguments\""), ("t", "'A dash means the argument is silent'"),
               ("t", "'<h4>This argument</h4>'"), ("j", {"how": {"steps": [{"text": "{n} arguments, each"}]}}),
               ("j", {"premises": [{"name": "Arguments from wisdom"}]}), ("j", {"q": "Which arguments hold?"}),
               ("t", "'=== THE ARGUMENTS ==='")]
    caught = sum(1 for kind, x in planted
                 if (scan_template(x) if kind == 't' else scan_json('planted', x)))
    legal_hits = (scan_template("'(0) Call the entries positions, never arguments.'")
                  + scan_json('legal', {"_note": "argument-index.md", "edges": [{"why": "The argument rests on what the word means"}]}))
    print(f'COUNT selftest planted {len(planted)}, caught {caught}; legal uses flagged {len(legal_hits)}')
    sys.exit(1 if caught == len(planted) and not legal_hits else 0)

src = open(os.path.join(ROOT, 'pipeline', 'hub_template.html'), encoding='utf-8').read()
hits = scan_template(src)
for name in ('front_door.json', 'dependencies.json'):
    hits += scan_json(name, json.load(open(os.path.join(ROOT, 'sources', name), encoding='utf-8')))
sys.exit(0 if report(hits, '3 files') else 1)
