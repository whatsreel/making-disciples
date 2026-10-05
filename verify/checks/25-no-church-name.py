#!/usr/bin/env python3
"""25 no church name: no public file and no view of the page names the church or its folders.

WHY: the page is "prepared for the session" and never names the church; the public repo is
named making-disciples for the same reason (plan of record, chunk C). Until 2026-10-04 two
pipeline files carried the private notes folder's name, which names the church, and no check
looked. This check is itself public, so it holds no names and no hashes of them (a code review
reversed a short hash in under a second). The names live in private/protected-names.txt in the
notes repo, found the same way the session paper is: in this repo, or in the folder the
machine-local .notes-expected marker names. Without the marker (CI, a public clone) the check
counts itself skipped; with the marker and no names file, it FAILS, so it cannot skip forever on
the machines that matter.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, PAGE, rendered, need_build
from manifest import public_files, read_texts, decode, is_binary
from paper import notes_dir, MARKER
from names import NAMES_FILE, key, load, hits as name_hits   # one matcher, shared with the export

def load_names(root):
    return load(root, notes_dir(root))

def scan(texts, keys):
    found = name_hits(texts, keys)
    print(f'COUNT church-name hits {len(found)} across {len(texts)} public files and views')
    for x in found[:10]:
        print(f'SAMPLE {x} (a protected name; open the line to see it)')
    return not found

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    # Stand-in names, written the ways a names file might hold them, against the ways a public
    # file might spell them. Each planted line must be caught on its own.
    names = [key(n) for n in ('zzplanted', 'zz chapel', 'zz-chapel of grace', "st. zzpaul's",
                              'zzchurch.org', 'joinedzzname', 'são zzé', 'ZZQ', 'tzz chapel', '1st zzname')]
    names.append('=' + key('zzfirst zzpres'))   # "=": whole words only, as in the names file
    cases = {'one.md': 'Prepared for zzplanted elders.', 'two.md': 'Notes from Zz Chapel, kept private.',
             'wrap.md': 'a hard-wrapped line ending Zz\nChapel on the next line',
             'joined.py': 'NOTES = "../zzplanted_notes"', 'domain.md': 'See https://www.zzplantedchurch.org/',
             'long.md': 'the Zz Chapel of\nGrace session', 'runon.md': 'See https://zzchapel.org/',
             'camel.py': 'ZzChapelNotes = 1', 'emph.md': 'prepared for *Zz* Chapel',
             'nbsp.html': 'Zz&nbsp;Chapel', 'numeric.html': 'Zz&#xa0;Chapel', 'dash.md': 'Zz\u2013Chapel',
             'tag.html': 'Zz <b>Chapel</b>', 'url.md': 'href="/Zz%20Chapel"', 'slash.md': 'zz/chapel',
             'json.json': '"zz\nchapel"', 'soft.md': 'Zz\u00adChapel', 'zwsp.md': 'Zz\u200bChapel',
             'own.md': "a note from St. Zzpaul's", 'curly.md': 'a note from St. Zzpaul\u2019s',
             'entity.html': 'St. Zzpaul&rsquo;s', 'nodot.md': 'St Zzpaul s', 'owndomain.md': 'see zzchurch.org',
             'spaced.md': 'Joined Zz Name', 'accent.md': 'Sao Zze', 'accented.md': 'São Zzé',
             # a short name (an abbreviation): whole words only, camelCase split
             'abbr.md': 'the ZZQ session', 'abbrslug.py': 'ROOT = "../ZZQ_notes"', 'abbrcamel.js': 'ZZQNotes()',
             'abbrdomain.md': 'zzq.org', 'dotted.md': 'the Z.Z.Q. session', 'capslower.py': 'ZZQnotes = 1',
             # inside markup, where undoing it would remove the letters: so the raw text is scanned too
             'href.html': '<a href="https://zzchurch.org/">our church</a>', 'autolink.md': 'see <https://zzchurch.org>',
             'alt.html': '<img alt="Zz Chapel">', 'code.py': 'if a < 3 and n == "Zz Chapel" or b > 2:',
             'winpath.txt': 'C:\\dev\\claude\\tzz chapel notes', 'jsonpath.json': '"C:\\\\dev\\\\tzzchapel"',
             'uesc.json': '"S\\u00e3o Zz\\u00e9"',
             'tagwrap.html': 'Zz<span\n  class="x">Chapel</span>', 'enctag.html': '&lt;em&gt;Zz&lt;/em&gt; Chapel',
             'mdlink.md': '[Zz](https://example.org/x) Chapel', 'mdref.md': '[Zz][ref] Chapel',
             'footnote.md': 'Zz[^1] Chapel', 'double.html': 'Zz&amp;nbsp;Chapel', 'pct.md': 'Zz%26nbsp%3BChapel',
             # decoded but still inside a tag or link target; a footnote in HTML or a superscript
             'hrefpct.html': '<a href="https://x.org/Zz%20Chapel/">site</a>', 'mdpct.md': '[notes](https://x.org/Zz%20Chapel/notes)',
             'altnbsp.html': '<img alt="Zz&nbsp;Chapel">', 'sup.html': 'Zz<sup>1</sup> Chapel', 'supchar.md': 'Zz¹ Chapel',
             # a comparison is not a tag: the name between "<" and ">" is still read
             'cmp.js': 'for(i=0;i<n;i++){u="Zz%20Chapel";}\nf=a=>b',
             # one stray ANSI byte must not turn a UTF-8 no-break space into a letter
             'ansi.md': decode('Zz Chapel, then '.encode('utf-8') + b'\x92s'),
             # each reduction can hide what another reveals: an HTML ordinal, a call's arguments,
             # a plain citation, an escaped closing tag, a comment
             'ordinal.html': '1<sup>st</sup> Zzname', 'callarg.js': 'h[k]("Zz <b>Chapel</b>")',
             'cite.md': 'Zz[1] Chapel', 'caret.md': 'Zz^2 Chapel', 'esctag.json': '"<em>Zz<\\/em> Chapel"',
             'comment.html': 'Zz<!-- a > b --> Chapel', 'wholeword.md': 'the Zzfirst Zzpres session',
             'wholecamel.py': 'ZzfirstZzpres = 1'}
    caught = [k for k, v in cases.items() if not scan({k: v}, names)]
    # Part of a long name is not the name.
    longname = [key('zz-chapel of grace')]
    legal = {'part1.md': 'the Zz Chapel session', 'part2.md': 'by grace through faith',
             'part3.md': 'Zz chapel and grace are two words here'}
    flagged = [k for k, v in legal.items() if not scan({k: v}, longname)]
    # A short name's letters inside code or another word are not the name.
    # The two shapes that gave real false alarms on 2026-10-04 ("if (pc", "if (!p) { console").
    # A key split across separate one-letter words ("z) { zq") reads as "Z.Z.Q." and does match:
    # the price of catching dotted abbreviations.
    abbr = {'code1.js': 'iz (zq.length) {', 'code2.js': "iz (!z) { qconsole.error('x'); }",
            'capword.md': 'Azzq is one word',
            'inword.md': 'the zzqx and xzzq tokens'}
    legal.update(abbr)
    flagged += [k for k, v in abbr.items() if not scan({k: v}, [key('ZZQ')])]
    # A whole-word name's letters at the start of ordinary words are not the name.
    whole = {'polity.md': 'the zzfirst zzpresbytery met', 'presented.md': 'it was zzfirst zzpresented'}
    legal.update(whole)
    flagged += [k for k, v in whole.items() if not scan({k: v}, ['=' + key('zzfirst zzpres')])]
    # ...but the same letters also listed plainly still match inside a slug
    both = ['=' + key('zzfirst zzpres'), key('zzfirst zzpres')]
    plain_ok = not scan({'slug.md': 'see zzfirstzzpreschurch.org'}, both)
    cases['slug.md'] = 'see zzfirstzzpreschurch.org'
    caught += ['slug.md'] if plain_ok else []
    print(f'COUNT selftest planted {len(cases)}, caught {len(caught)}; legal {len(legal)}, flagged {len(flagged)}')
    sys.exit(1 if len(caught) == len(cases) and not flagged else 0)

need_build()
names = load_names(ROOT)
if names == []:
    print('COUNT protected names 0 (the names file exists but lists none)')
    print('SAMPLE an empty list would pass every file: add the names or remove the file')
    sys.exit(1)
if names is None:
    expected = os.path.isfile(os.path.join(ROOT, MARKER))
    print(f'COUNT protected-names-file 0/1 ({"marker present: it must be found" if expected else "no marker (CI or a public clone): skipped"})')
    if expected:
        print(f'SAMPLE not found in {NAMES_FILE} here or in the folder .notes-expected names')
    sys.exit(1 if expected else 0)
files, exempt = public_files(ROOT)
texts = read_texts(files + exempt, ROOT)                # every public file, Scripture too
binaries = [k for k in texts if is_binary(open(os.path.join(ROOT, k), 'rb').read())]
texts.update({'path ' + k: k for k in list(texts)})     # file paths are public as well
for k, v in rendered().items():
    texts['page ' + k] = v
# The built page as published, hidden parts too (attributes, script data, comments): the release
# loop publishes this file whole.
texts['built ' + os.path.relpath(PAGE, ROOT).replace(os.sep, '/')] = decode(open(PAGE, 'rb').read())
print(f'COUNT protected names {len(names)} (from the notes repo); binary public files unreadable {len(binaries)}')
for b in binaries[:5]:
    print('SAMPLE binary, cannot be checked for names: ' + b)
ok = scan(texts, names)
sys.exit(0 if ok and not binaries else 1)
