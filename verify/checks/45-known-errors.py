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
import os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT
from manifest import public_texts

_MK = r'[*_]{0,3}'   # Markdown emphasis around a title: italic, bold or both
# Corrections stay legal: each negation, with and without "grammatical" (a match may start at either word).
_NEG = ''.join(f'(?<!{re.escape(n)})(?<!{re.escape(n)}grammatical )' for n in
               ("not the ", "not an ", "not a ", "never the ", "rather than the ", "isn't the ", "isn’t the "))

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
    # CLAUDE.md: tērein is not the object of didaskontes (Matt 28:20); what Christ commanded is the object
    # of tērein. Object-language about the teaching came back in C10 (three times), C1c, three args.json lines
    # and a dependencies.json quote (corrected in sources/ 2026-10-05), so any "object of didaskontes / the participle /
    # (the Commission's) teaching" fails. Deliberately broad: ordinary English such as "Christ is the
    # object of the teaching" fails too, and is reworded rather than allowed, because this error has
    # returned in exactly that loose form. Corrections ("not the object of ...") stay legal.
    # Known misses, accepted (sweep): the claim with didaskontes as subject ("didaskontes takes keeping as its
    # object"), and a correction wrapped across a line break (exemptions need single spaces).
    'terein called the object of the teaching': re.compile(   # ASCII label: a Windows console cannot print the macron
        _NEG + r"(?<![\w*_])(?:grammatical\s+)?" + _MK + r"object" + _MK + r"\s+of\s+"
        r"(?:(?:the|his|their|Christ['’]s|Jesus['’]s?)\s+)?(?:(?:Great\s+)?Commission['’]s\s+)?(?:(?:verb|participle)\s+)?[“\"]?" + _MK +
        r"(?:didask\w*|δ[ιί]δ[αά]σκ\w*|participle|teaching|instruction)"
        # (?<![\w*_]) makes a match start before any emphasis, so the "not " guard always sees the word before it
        r"|(?<!not )(?<![\w*_])" + _MK + r"didaskontes" + _MK + r"['’]s?\s+object", re.I),
}
SKIP = {'master.json', 'verify/checks/45-known-errors.py'}

def scan(texts):
    hits = []
    for label, t in texts.items():
        t = unicodedata.normalize('NFC', t).replace(' ', ' ')   # one spelling of each accented Greek letter (U+1F71 -> U+03AC); NBSP as a space
        for name, rx in ERRORS.items():
            for m in rx.finditer(t):
                hits.append(f'{label}:{t.count(chr(10), 0, m.start()) + 1} {name}: "{m.group(0)}"')
    print(f'COUNT known-error regressions {len(hits)} across {len(texts)} files ({len(ERRORS)} patterns)')
    for h in hits[:10]:
        print(('SAMPLE ' + h).encode('ascii', 'backslashreplace').decode())   # a Greek or macron hit must not crash a Windows console
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
               'bold.md': "Westminster's **Directory for Family Worship**",
               'c10.md': 'And the infinitive is *tērein* — keep, guard, obey. It is the object of *didaskontes*: the thing being taught is *keeping*.',
               'c1c.md': '"teaching them to observe," where keeping is the grammatical object of the teaching.',
               'sup.json': '"To keep is the grammatical object of teaching, so obedience is the content"',
               'sup74.json': '"Matt 28:20 — teaching them to observe. Keeping is the object of the teaching."',
               'dep209.json': '"why": "The object of the Commission\'s teaching is not the body of instruction Jesus delivered"',
               'participle.md': 'tērein is the object of the participle didaskontes',
               'greek.md': 'tērein is the object of διδάσκοντες',
               'thedid.md': 'the object of the *didaskontes*',
               'possobj.md': 'tērein is *didaskontes*’ object',
               'emteach.md': 'keeping is the object of *teaching*',
               'empart.md': 'tērein is the object of the *participle*',
               'his.md': 'keeping is the object of his teaching',
               'christs.md': "keeping is the object of Christ's teaching",
               'great.md': "The object of the Great Commission's teaching is not the body of instruction",
               'quoted.md': 'keeping is the object of “teaching”',
               'oxia.md': 'tērein is the object of διδάσκοντες',   # Greek-extended alpha with oxia, as pasted from some sites
               'verb.md': 'keeping is the object of the verb didaskontes',
               'inf.md': 'tērein is the object of didaskein',
               'morethan.md': 'Keeping is more than the object of the teaching',
               'posss.md': "keeping is didaskontes's object",
               'jesus.md': "keeping is the object of Jesus' teaching",
               'their.md': 'keeping is the object of their teaching',
               'plaingreek.md': 'tērein is the object of διδασκοντες',
               'emobj.md': 'keeping is the *object* of the teaching',
               'instr.md': 'keeping is the object of the instruction'}
    caught = [k for k, v in planted.items() if not scan({k: v})]
    legal = {'g1.md': 'The General Assembly of the Church of Scotland approved a Directory for Family Worship on 24 August 1647.',
             'd4.md': 'the same Assembly that adopted the Westminster Confession, approved a Directory for Family Worship.',
             'texts.json': '"texts": "Baxter; BCO 8-3; Directory for Family Worship"',
             'd4card.json': '"The General Assembly of the Church of Scotland, which adopted the Westminster Confession, approved a Directory for Family Worship (1647)"',
             'nocomma.md': 'The General Assembly that adopted the Westminster Confession approved a Directory for Family Worship.',
             'list.md': 'The Directory for Family Worship (24 Aug 1647) was approved by the General Assembly of the Church of Scotland, not the Westminster divines.',
             'teren.md': 'It is a complementary infinitive, not the object of *didaskontes*.',
             'c10new.md': 'It states what *didaskontes* teaches: the thing being taught is *keeping*.',
             'dep.json': '"why": "What they are taught to keep is not the body of instruction Jesus delivered"',
             'notgram.md': 'tērein is not the grammatical object of didaskontes',
             'never.md': 'Keeping is never the object of the teaching; it is its content.',
             'learn.md': '"learn of me" makes Christ himself, not only his doctrine, the object of learning.',
             'isnt.md': "Keeping isn't the object of the teaching; it is its content.",
             'isntcurly.md': 'Keeping isn’t the object of the teaching; it is its content.',
             'rather.md': 'Keeping is its content rather than the object of the teaching.',
             'notan.md': 'tērein is not an object of the participle.',
             'notposs.md': 'tērein is not *didaskontes*’ object',
             'c10now.md': "The subject matter of the Commission's teaching is not the body of instruction Jesus delivered; it is the set of commands he issued.",
             'rathergram.md': 'Keeping is its content rather than the grammatical object of the teaching.',
             'nevergram.md': 'Keeping is never the grammatical object of the teaching.',
             'isntgram.md': "Keeping isn't the grammatical object of the teaching.",
             'boldital.md': 'tērein is not ***didaskontes***’ object',
             'dunder.md': 'tērein is not __didaskontes__’ object',
             'nbsp.md': 'tērein is not the object of didaskontes',
             'notemobj.md': 'keeping is not the *object* of the teaching'}
    flagged = [k for k, v in legal.items() if not scan({k: v})]
    print(f'COUNT selftest planted {len(planted)}, caught {len(caught)}; legal {len(legal)}, flagged {len(flagged)}')
    sys.exit(1 if len(caught) == len(planted) and not flagged else 0)

texts = {k: v for k, v in public_texts(ROOT, exempt=True).items() if k not in SKIP and not k.startswith('kjv/')}
sys.exit(0 if scan(texts) else 1)
