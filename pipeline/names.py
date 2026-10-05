#!/usr/bin/env python3
"""Protected names: one matcher, shared by gate check 25 and the export to the public page repo.

This file is public, so it holds no names and no hashes of them. The names live in
private/protected-names.txt in the notes repo, found in this repo or in the folder the
machine-local .notes-expected marker names (see paper.notes_dir).

How a name is matched: the text and the name are both reduced to bare letters and digits --
accents folded (é -> e), case folded, everything else dropped -- and the name is searched for as
a plain substring. So "Zz Chapel", "ZzChapel", "zz-chapel.org", "*Zz* Chapel" and "Zz’s" all
read as the same letters. Each text is scanned in every combination of three markup reductions
(views()): decoding (HTML entities, %20, a JSON "\\u00e9"), taking out tags, and taking out
marks (footnotes, citations, link targets) -- because each one also removes letters (decoding
eats the letter after a backslash in a Windows path; stripping eats an href), so a form without
it must be scanned too.

Earlier versions allowed a list of separators between a name's words; every code review found
another separator (2026-10-04, three rounds). The cost of this one is that two sentences ending
and beginning with a long name's words also match ("...by zz. Chapel..."): a false alarm the
author can reword, where a missed name ships.
"""
import html, os, re, sys, unicodedata
from urllib.parse import unquote

NAMES_FILE = os.path.join('private', 'protected-names.txt')
# A real tag only (a letter, "/" or "!" after "<"), so "a < 3 ... b > 2" or "=>" is never one.
_TAG = re.compile(r'<[A-Za-z/!][^<>]*>')
_COMMENT = re.compile(r'<!--.*?-->', re.S)
_ESC = re.compile(r'\\(?:u([0-9a-fA-F]{4})|x([0-9a-fA-F]{2})|[ntr/])')
# Marks that put letters or digits between a name's words: an HTML footnote (<sup>1</sup>), a
# superscript digit, a citation ([1], ^1, [^1]), a markdown link target or reference label.
_MARKS = re.compile(r'<sup\b[^<>]*>.*?</sup>|[\u00b9\u00b2\u00b3\u2070-\u2079]|\[\^?\d+\]|\^\d+|\[\^[^\]\n]*\]'
                    r'|\]\([^)\n]*\)|\]\[[^\]\n]*\]', re.I | re.S)

def _unescape(m):
    code = m.group(1) or m.group(2)
    return chr(int(code, 16)) if code else ('/' if m.group(0).endswith('/') else ' ')

def _decode(t):
    """Escapes, HTML entities and %-escapes decoded, repeated until nothing changes (so
    double-encoded "&amp;nbsp;" comes undone too); tags and links left in place."""
    for _ in range(4):
        before = t
        t = _ESC.sub(_unescape, t)
        t = html.unescape(t)
        t = unquote(t) if '%' in t else t
        if t == before:
            break
    return t

def _tags(t):
    return _TAG.sub(' ', _COMMENT.sub(' ', t))

def _marks(t):
    return _MARKS.sub(' ', t)

def views(t):
    """Every form a text is scanned in: each combination of three independent reductions --
    decode (entities, %, escapes), take out tags and comments, take out marks (footnotes,
    citations, link targets). Each reduction can reveal a name (it joins the name's words) or hide
    one (it eats letters: the letter after a backslash, an href, a footnote's "st" in
    "1<sup>st</sup>"). A name that some reduction hides is in a span that reduction removes, so
    the combinations without it still show it. Identical forms are scanned once."""
    out = []
    for dec in (False, True):
        a = _decode(t) if dec else t
        for tg in (False, True):
            b = _tags(a) if tg else a
            for mk in (False, True):
                c = _marks(b) if mk else b
                if c not in out:
                    out.append(c)
    return out

def _undo_markup(t):
    return _marks(_tags(_decode(t)))

def letters(t):
    """(the text's letters and digits, lowercased and unaccented, as one string; for each of them,
    its offset in t)."""
    out, at = [], []
    for i, c in enumerate(t):
        for d in unicodedata.normalize('NFKD', c).casefold():
            if 'a' <= d <= 'z' or '0' <= d <= '9':
                out.append(d)
                at.append(i)
    return ''.join(out), at

def key(name):
    return letters(_undo_markup(name))[0]

def load(root, notes_dir):
    """The names' keys, or None when no names file is found. Text after "#" is a comment; blank
    lines are skipped. Exits 1 on a line that has no letters or digits (it would match nothing)."""
    from manifest import decode
    for base in (root, notes_dir):
        if base and os.path.isfile(os.path.join(base, NAMES_FILE)):
            lines = decode(open(os.path.join(base, NAMES_FILE), 'rb').read()).splitlines()
            raw = [l.split('#', 1)[0].strip() for l in lines]
            # "=" before a name: match it only as whole words, like an abbreviation -- for a name
            # whose letters begin ordinary words ("zzfirst zzpres" in "zzfirst zzpresbytery")
            keys = [('=' if n.startswith('=') else '') + key(n.lstrip('=')) for n in raw]
            empty = [i + 1 for i, (n, k) in enumerate(zip(raw, keys)) if n and not k.lstrip('=')]
            if empty:
                print(f'COUNT names-file lines that name nothing {len(empty)}')
                print(f'SAMPLE {NAMES_FILE} line {empty[0]}: no letters or digits, so it could never match')
                sys.exit(1)
            return [k for k in keys if k]
    return None

# A short name (an abbreviation) found as bare letters would hit ordinary code: with the
# punctuation gone, "if (pc" reads as "ifpc". So a key under SHORT letters must begin and end on
# a word boundary: between two words (letters, or digits), at a camelCase step ("ZzNotes"), or
# where capitals give way to lower case ("ZZQnotes"). "Z.Z.Q." and "ZZQ_notes" match; "ifpc"
# does not. A run-together slug with no case step ("zzqcity", "ZZQCITY", "Zzqcity") has no
# boundary to find: list that form in the names file itself, as a longer name.
SHORT = 5
_WORD = re.compile(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+')

def _starts(t, keys, short):
    """Offsets in t where a key's letters begin."""
    s, at = letters(t)
    wid = {}
    for n, m in enumerate(_WORD.finditer(t)):
        for i in range(m.start(), m.end()):
            wid[i] = n
    def edge(j, end):   # a word boundary just before s[j]?
        if j <= 0 or j >= len(s):
            return True
        a, b = at[j - 1], at[j]
        # capitals giving way to lower case ends a short name ("ZZQnotes") but never starts one:
        # "Azzq" is one word
        return wid.get(a, -1 - a) != wid.get(b, -2 - b) or (end and t[a].isupper() and t[b].islower())
    found = set()
    for k in keys:
        i = s.find(k)
        while i != -1:
            if k not in short or (edge(i, False) and edge(i + len(k), True)):
                found.add(at[i])
            i = s.find(k, i + 1)
    return found

def hits(texts, keys):
    """['label:line', ...] for every line of every text where a name's letters begin, in any of
    the text's views. A key under SHORT letters, or marked "=" in the names file, must begin and
    end on a word boundary -- unless the same letters are also listed plainly, which matches
    anywhere (the flag belongs to the line, so a plain line is never narrowed by a "=" one)."""
    plain = {k for k in keys if not k.startswith('=') and len(k) >= SHORT}
    keys = sorted({k.lstrip('=') for k in keys})
    short = {k for k in keys if k not in plain}
    out = []
    for label, raw in texts.items():
        lines = set()
        for t in views(raw):
            lines |= {t.count('\n', 0, p) + 1 for p in _starts(t, keys, short)}
        out += [f'{label}:{ln}' for ln in sorted(lines)]
    return out
