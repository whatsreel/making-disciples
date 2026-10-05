#!/usr/bin/env python3
"""50 no typed counts: no number typed next to "arguments", "views", "tabs" or "positions", and no typed tally.

WHY: counts were typed by hand three times and were wrong each time ("nine views" in the
footer, "Forty arguments" atop a 45-argument index, "seven views" in the smoke test). Visible
counts are computed from the data. This reads the hand-edited files only; the built page's
numbers are computed, so they are not scanned. The files are the manifest's public text files.

If a sentence genuinely needs a small fixed number ("the two arguments usually quoted"),
reword it to name them, or compute it in the template.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT
from manifest import public_texts, decode

# One list of number words, from which the patterns and the range test's values are all built,
# so a word added here is both matched and valued (a word matched but valued 0 would hide a tally).
_UNITS = ('one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen '
          'sixteen seventeen eighteen nineteen').split()
_TENS = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60}
_WORDS = {w: i + 1 for i, w in enumerate(_UNITS)} | _TENS
NUM = r'\d+|' + '|'.join(_WORDS)
# Between words: spaces, or a line wrap -- at most one newline, so a heading that ends in a
# number and the next paragraph never read as one phrase.
WS = r'(?:[ \t]*\n[ \t]*|[ \t]+)'
TYPED = re.compile(r'\b(' + NUM + r')(?:-[a-z]+)?' + WS + r'(arguments|views|tabs|positions)\b', re.I)
# A tally of the corpus typed out: "the split is six to six", "Ten of the thirty-three",
# "holds 26–2", "a 12–7 split". All were stale on 2026-10-04 (the corpus had grown to 45) and
# the pattern above missed them. A tally needs a verdict word before it ("split is", "stands at",
# "holds", "held"), the word "split" after it, or a corpus-sized number (twenty and up) after
# "of the". Plain "is" is NOT a verdict word: "is two to five sentences" and "is one-on-one" are
# ranges and phrases, and the selftest proves they stay legal. So does a verse range ("14:25–33").
W = r'(?:' + '|'.join(_WORDS) + r')(?:-(?:' + '|'.join(_UNITS[:9]) + r'))?'
N = r'(?:\d+|' + W + r')'
# After a verdict verb, word numbers join only by "to" ("holds six to six"), so "held one-to-one
# meetings" and "holds twenty-one people" stay legal; digits join by "to" or any dash.
DV = r'\d+(?:' + WS + r'to' + WS + r'|[ \t]*[\u2013\u2014-][ \t]*)\d+'
WV = W + WS + r'to' + WS + W
# Before "split", "margin" or "majority" any separator reads as a tally ("a six-to-six split").
S = r'(?:' + WS + r'to' + WS + r'|[ \t]*[\u2013\u2014-][ \t]*|-to-)'
# A time or length range ("holds 2 to 3 weeks") is not a tally.
UNIT = r'(?!' + WS + r'(?:weeks?|days?|months?|years?|hours?|minutes?|times|pages?|verses?|chapters?|sentences?|people)\b)'
E = r'[*_]{0,2}'                                       # markdown emphasis around a tally
VERB = (r'(?:split' + WS + r'(?:is|was)|stands(?:' + WS + r'at)?|stood(?:' + WS + r'at)?|holds(?:' + WS
        + r'at)?|held(?:' + WS + r'at)?|went|split' + WS + r'of|(?:won|lost)' + WS + r'by)')
TALLY = re.compile(r'\b' + VERB + WS + E + r'(?:' + WV + r'|' + DV + r')' + E + r'(?!\w)' + UNIT
                   + r'|\b' + N + S + N + E + WS + r'(?:split|margin|majority)\b'
                   + r'|\bis' + WS + E + DV + E + r'(?!\w)' + UNIT              # "is 26-2", not "is 2-3 pages"
                   # a share of the corpus: "Ten of the thirty-three", "26 of 45" -- but not
                   # "one of the 70", "one of the 120" or "one of the twenty-four elders", which
                   # name a person, not a tally
                   + r'|\b(?!one\b)' + W + WS + r'of' + WS + r'the' + WS + r'(?:twenty|thirty|forty|fifty|sixty)\b'
                   + r'|\b\d{2}' + WS + r'of' + r'(?:' + WS + r'the)?' + WS + r'[2-9]\d\b', re.I)
# A vote count runs high to low ("26-2", "six to six"); a verse, page or year range runs low to
# high ("3-8", "18-20", "1643-1649", "two to five"). So a to/dash pair whose first number is the
# smaller one, or that has a four-digit number, is a range, never a tally.
def _val(tok):
    parts = tok.lower().split('-')
    return sum(_WORDS.get(x, 0) for x in parts) if not tok.isdigit() else int(tok)
SHARE = re.compile(r'(?:\d+|' + W + r')' + WS + r'of\b', re.I)
def is_range(g):
    if SHARE.match(g):
        return False   # the share branch ("26 of 45"): first < second by nature, never a range
    nums = re.findall(r'\b(?:\d+|' + W + r')\b', g, re.I)   # whole words: "fourteen", never "four"
    if any(len(n) >= 4 for n in nums if n.isdigit()):
        return True
    return len(nums) == 2 and _val(nums[0]) < _val(nums[1])
# Which files: every public text file the manifest names (one list, shared with checks 20 and 25),
# tone-exempt ones included (exempt from tone, not from counts), minus generated master.json,
# the Scripture text and this check, whose selftest plants tallies on purpose.
SKIP = {'master.json', 'verify/checks/50-no-typed-counts.py'}
def wanted(rel):
    return rel not in SKIP and not rel.startswith('kjv/')

def scan(texts):
    hits = []
    for label, t in texts.items():
        for rx in (TYPED, TALLY):
            for m in rx.finditer(t):
                if rx is TALLY and is_range(m.group(0)):
                    continue
                hits.append(f'{label}:{t.count(chr(10), 0, m.start()) + 1} "{m.group(0)}"')
    print(f'COUNT typed-counts {len(hits)} in {len(texts)} hand-edited files')
    for h in hits[:10]:
        print('SAMPLE ' + h)
    return not hits

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    # Each planted line must be caught on its own; a selftest that passes on any one is useless.
    planted = {'footer.html': "footer: 45 arguments · nine views",
               'split.md': "On the who question the split is six to six.",
               'share.md': "Ten of the thirty-three bear on what.",
               'digits.md': "The what question holds 26–2 with nothing set aside.",
               'digsplit.md': "It is a 12–7 split.",
               'past.md': "On who, the split was six to six.",
               'digto.md': "The what question holds 26 to 2.",
               'emph.md': "It holds **26–2** even so.",
               'margin.md': "It carries a 26–2 margin.",
               'stands.md': "Who stands 12–7.",
               'wrapped.md': "the split is\nsix to six",
               'wraptyped.md': "all 45\narguments",
               'wordsplit.md': "a twelve to seven split",
               'hyphen.md': "a six-to-six split",
               'heldat.md': "it held at 12-7",
               'emdash.md': "held 26—2",
               'went.md': "the vote went 26-2",
               'is.md': "The what question is 26\u20132.", 'splitof.md': "a split of 12\u20137",
               'wonby.md': "it won by 26 to 2", 'of45.md': "26 of 45 hold",
               # teen words begin with a smaller number's word ("four" in "fourteen")
               'teen1.md': "the split is fourteen to six", 'teen2.md': "It holds seventeen to nine",
               'teen3.md': "a sixteen-to-eight split", 'teen4.md': "the split was nineteen to ten",
               'teen5.md': "held eighteen to nine",
               # a Windows (CRLF) file, read through the same decoder the real files use
               'crlf.md': decode(b'the split is\r\nsix to six'), 'crlftyped.md': decode(b'all 45\r\narguments')}
    caught = [k for k, v in planted.items() if not scan({k: v})]
    legal = {'range.md': "Keep answers short: each summary is two to five sentences.",
             'phrase.md': "Discipleship is one-on-one.", 'pages.md': "It is 2–3 pages.",
             'verse.md': "Luke 14:25–33 thinned them.",
             'apostle.md': "Judas was one of the 12.",
             'weeks.md': "The course holds 2 to 3 weeks of material.",
             'onetoone.md': "He held one-to-one meetings.",
             'seventy.md': "He was one of the 70 he sent.", 'onetwenty.md': "one of the 120 in Acts 1:15",
             'verse1.md': "Matt 28:18 is 18-20.", 'verse2.md': "Rom 12 holds 3-8.",
             'years.md': "The Assembly held 1643\u20131649.", 'meet.md': "the session held 4 to 5 meetings",
             'maj.md': "a 2-3 majority of elders", 'splitrange.md': "a split of 3–8", 'went.md': "Discipleship went one-to-one.",
             'twentyone.md': "It holds twenty-one people.",
             'elders.md': "He was one of the twenty-four elders.",
             'heading.md': "## Part 2\n\nArguments for the other view"}
    flagged = [k for k, v in legal.items() if not scan({k: v})]
    print(f'COUNT selftest planted {len(planted)}, caught {len(caught)}; legal {len(legal)}, flagged {len(flagged)}')
    # fails (as a selftest must) only when every tally is caught AND no legal line is flagged
    sys.exit(1 if len(caught) == len(planted) and not flagged else 0)

texts = {k: v for k, v in public_texts(ROOT, exempt=True).items() if wanted(k)}
sys.exit(0 if scan(texts) else 1)
