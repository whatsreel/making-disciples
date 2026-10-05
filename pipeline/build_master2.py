#!/usr/bin/env python3
"""Merge argument-index.md (full prose) + args.json (structured fields) -> master.json

Design decision: the index does NOT use a uniform Case/Counter/Rejoinder schema.
Several entries use bespoke headings ("The tension.", "Church discipline.",
"Counter - three of them, and they matter."), and some have no rejoinder at all.
So the master stores BOTH:

  body_md   verbatim prose, lossless - nothing is dropped
  sections  [{label, text}] parsed from the bold labels actually used

Generators use whichever they need. args.json supplies the structured axes and
the compressed card text the map UI renders.
"""
import os
WORK = os.environ.get('WORK', '/home/claude')
OUT = os.environ.get('OUT', '/mnt/user-data/outputs')
import json, re

INDEX = OUT+'/argument-index.md'
ARGS  = WORK+'/args.json'
OUT   = WORK+'/master.json'

raw = open(INDEX).read()
aj  = json.load(open(ARGS))
struct = {a['id']: a for a in (aj['M'] + aj['D'])}
BANDS  = aj['BANDS']

# split on ### entries, but a following '## ' section header also ends an entry
chunks = re.split(r'\n(?=###? )', '\n' + raw)
entries, prefaces = {}, []
for p in chunks:
    if not p.startswith('\n### ') and not p.startswith('### '):
        continue
    p = p.lstrip('\n')[4:]
    head, _, body = p.partition('\n')
    head = head.strip()
    m = re.match(r'^([A-G]\d+[a-z]?)\.\s*(.*)$', head)
    if not m:
        prefaces.append({'head': head, 'body': body.strip()})
        continue
    entries[m.group(1)] = {'claim': m.group(2).strip().strip('"\u201c\u201d'),
                           'body': body.strip()}

# a bold label at the start of a line, e.g. **Case.** or **Counter - three of them.**
LABEL_RE = re.compile(r'^\*\*(.+?)\*\*', re.M)

def split_sections(body):
    """Return [{label,text}] for every bold-label block; text before the first
    label is kept under label None so nothing is lost."""
    out, hits = [], list(LABEL_RE.finditer(body))
    if not hits:
        return [{'label': None, 'text': body.strip()}]
    if hits[0].start() > 0:
        lead = body[:hits[0].start()].strip()
        if lead:
            out.append({'label': None, 'text': lead})
    for i, h in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(body)
        label = h.group(1).strip().rstrip('.:')
        text = body[h.end():end].strip()
        # 'Lands: Strong, and ...' packs verdict into the label itself
        out.append({'label': label, 'text': text})
    return out

def find_section(sections, *names):
    for s in sections:
        if not s['label']:
            continue
        lab = s['label'].lower()
        if any(lab == n or lab.startswith(n) for n in names):
            return s
    return None

master = []
for aid, e in entries.items():
    body = e['body']
    # strip the trailing italic column line out of the body before sectioning
    mc = re.search(r'^\*Column:\s*(.*?)\*\s*$', body, re.M)
    column_line = mc.group(1).strip() if mc else None
    body_wo = body.strip()
    # trailing '---' separators belong to the document, not the argument
    body_wo = re.sub(r'(\n\s*---\s*)+$', '', body_wo).strip()
    sections = split_sections(body_wo)
    rec = {'id': aid, 'claim': e['claim'],
           'body_md': body_wo,          # lossless
           'sections': sections,
           'column_line': column_line}

    cs = find_section(sections, 'case', 'the rules in play', 'the tension', 'church discipline')
    rj = find_section(sections, 'rejoinder', 'the resolution')
    ct = find_section(sections, 'counter')
    ld = find_section(sections, 'lands', "author's rating", 'author’s rating')  # label renamed 2026-10-04
    rec['case_label']      = cs['label'] if cs else None
    rec['case_full']       = cs['text']  if cs else None
    rec['counter_label']   = ct['label'] if ct else None
    rec['counter_full']    = ct['text']  if ct else None
    rec['rejoinder_label'] = rj['label'] if rj else None
    rec['rejoinder_full']  = rj['text']  if rj else None
    if ld:
        v = re.sub(r'^(?:Lands|Author[\'’]s rating)[:\s]*', '', ld['label']).strip()
        rec['lands_verdict'] = v or None
        rec['lands_note']    = ld['text'] or None
    else:
        rec['lands_verdict'] = rec['lands_note'] = None

    s = struct.get(aid)
    if s:
        b = s.get('band')
        rec.update({
            'band': b,
            'band_name': BANDS[b]['h'] if b is not None else None,
            'what': s.get('what'), 'who': s.get('who'), 'use': s.get('use'),
            'survives': s.get('surv'), 'risk': s.get('risk'),
            'supports': s.get('sup'), 'texts': s.get('texts'),
            'case_card': s.get('case'), 'counter_card': s.get('counter'),
            'claim_card': s.get('claim'), 'lands_card': s.get('lands'),
        })
    master.append(rec)

def sortkey(r):
    m = re.match(r'([A-G])(\d+)([a-z]?)', r['id'])
    return (m.group(1), int(m.group(2)), m.group(3))
master.sort(key=sortkey)

json.dump({'arguments': master, 'bands': BANDS, 'prefaces': prefaces},
          open(OUT, 'w', encoding='utf-8', newline=''), indent=1, ensure_ascii=False)

# ---- honest coverage report (None-aware, so band 0 is not a false alarm) ----
def missing(r, k):
    return r.get(k) is None or r.get(k) == ''

print(f'master.json: {len(master)} arguments, {len(prefaces)} prefaces')
print(f'orphans: {[i for i in struct if i not in entries] or "none"}')
chars = sum(len(r["body_md"]) for r in master)
print(f'verbatim prose preserved: {chars:,} chars\n')
for k in ['body_md','case_full','counter_full','rejoinder_full','lands_verdict',
          'band','what','who','texts','risk','supports','column_line']:
    miss = [r['id'] for r in master if missing(r, k)]
    tag = 'OK' if not miss else f'{len(miss)} missing'
    print(f'  {k:16s} {tag:14s} {"" if not miss else miss}')
