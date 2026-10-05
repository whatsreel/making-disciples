#!/usr/bin/env python3
"""Builds the payload for the unified hub. Every view reads this one object."""
import os
WORK = os.environ.get('WORK', '/home/claude')
OUT = os.environ.get('OUT', '/mnt/user-data/outputs')
import json, re, collections

M = json.load(open(WORK+'/master.json'))
A = M['arguments']
BANDS = M['bands']
ids = {a['id'] for a in A}

from ratings import verdict_short   # one rating rule, shared with the gate (check 40)
from falls import (KIND_FIELDS, kind_record, members,   # the fields a kind reads, shared with gate check 80
                   all_combinations, rests_view, all_subsets, is_traced, sweep_order)

# cross references with context
pat = re.compile(r'\b([A-G]\d+[a-z]?)\b')
links = []
for a in A:
    body, seen = a['body_md'], set()
    for m in pat.finditer(body):
        t = m.group(1)
        if t not in ids or t == a['id'] or t in seen: continue
        seen.add(t)
        s, e = max(0, m.start()-150), min(len(body), m.end()+150)
        ctx = re.sub(r'\*\*|\*', '', body[s:e].replace('\n', ' ').strip())
        links.append({'from': a['id'], 'to': t,
                      'ctx': ('\u2026' if s else '') + ctx + ('\u2026' if e < len(body) else '')})
inbound = collections.Counter(l['to'] for l in links)

BAND_ORDER = [b['h'] for b in BANDS]

# The index's italic summary line ends "· Use: Lead" (Support / Reference / Do not use). The field stays in
# the data for the Key arguments filter, but on the page it read as presenter tactics (tone list item 2,
# Jon chose "apply all" 2026-10-05), so the page drops that one segment of the line.
USE_SEG = re.compile(r' · Use: [^*\n]+(?=\*)')
def no_use(text):
    return USE_SEG.sub('', text) if text else text

args = []
for a in A:
    args.append({
        **kind_record(a),   # id, band, what, who, use, survives: one source, so a kind picks the same members as check 80
        'claim': a.get('claim') or '',
        'bandIdx': a.get('band') if a.get('band') is not None else -1,
        'verdict': verdict_short(a.get('lands_verdict')),
        'verdictFull': a.get('lands_verdict') or '',
        'texts': a.get('texts') or '',
        'risk': a.get('risk') or '',
        'sup': a.get('supports') or [],
        'inbound': inbound.get(a['id'], 0),
        'sections': [{'l': s.get('label'), 't': no_use(s.get('text'))} for s in a.get('sections', [])],
        'caseCard': a.get('case_card') or '',
        'counterCard': a.get('counter_card') or '',
    })

def order(vals, tail='\u2014'):
    seen = [v for v in dict.fromkeys(vals) if v]
    seen.sort(key=lambda v: (v == tail, v == 'Both', v))
    return seen

# ---- front door: editorial source, validated against master --------------
fd = json.load(open(WORK+'/front_door.json'))
byid = {a['id']: a for a in args}
bad = []
for c in fd['changes']:
    for k in ['lead'] :
        if c[k] not in byid: bad.append((c['key'], k, c[k]))
    for k in ['also', 'avoid']:
        for i in c.get(k, []):
            if i not in byid: bad.append((c['key'], k, i))
for i in fd['read_three']:
    if i not in byid: bad.append(('read_three', '', i))
for i in fd.get('alternative', {}).get('ids', []):
    if i not in byid: bad.append(('alternative', '', i))
for cq in fd.get('common_questions', []):
    for i in cq.get('ids', []):
        if i not in byid: bad.append(('common_questions', cq['q'][:30], i))
    if cq.get('computed') not in (None, 'not_firm', 'survives'):
        bad.append(('common_questions', cq['q'][:30], 'computed=' + str(cq.get('computed'))))
    if not cq.get('ids') and not cq.get('computed'):
        bad.append(('common_questions', cq['q'][:30], 'names no arguments'))
assert not bad, f'front_door.json references unknown ids: {bad}'
# every listed source must actually be cited in the published arguments
_corpus = open(OUT+'/argument-index.md', encoding='utf-8').read() + open(WORK+'/args.json', encoding='utf-8').read()
_uncited = [s['cite'] for s in fd.get('sources', []) if s['match'] not in _corpus]
assert not _uncited, f'front_door.json lists sources the arguments never cite: {_uncited}'

# ---- method: the reading rules (A1) and the three categories (A3), taken from the prose ----
def _numbered(arg_id, label):
    a = next(x for x in A if x['id'] == arg_id)
    sec = next((s for s in a['sections'] if (s['label'] or '').lower().startswith(label)), None)
    assert sec, f'{arg_id} has no "{label}" section'
    items = re.findall(r'^\d+\.\s+(.+)$', sec['text'], re.M)
    assert items, f'{arg_id} "{label}" section has no numbered list'
    return items
METHOD = {'rules': _numbered('A1', 'the rules in play'), 'rulesFrom': 'A1',
          'bins': _numbered('A3', 'the framework'), 'binsFrom': 'A3'}
# attach claim + verdict so the page never has to look them up
for c in fd['changes']:
    c['leadClaim'] = byid[c['lead']]['claim']
    c['leadVerdict'] = byid[c['lead']]['verdict']
    c['leadBand'] = byid[c['lead']]['band']
fd['read_three_items'] = [{'id': i, 'claim': byid[i]['claim'], 'band': byid[i]['band'],
                           'verdict': byid[i]['verdict']} for i in fd['read_three']]

# ---- dependencies: authored edges + spine, validated -----------------------
dep = json.load(open(WORK+'/dependencies.json'))
PREM = {p['id']: p for p in dep['premises']}
dbad = []
for e in dep['edges']:
    if e['from'] not in byid: dbad.append(('from', e['from']))
    if e['to'] not in byid and not (e['rel'] == 'rests on rule' and e['to'] in PREM): dbad.append(('to', e['to']))
    # shown as "rests on a reading rule or method": a kind is something an argument is one of, not a rule
    if e['rel'] == 'rests on rule' and PREM.get(e['to'], {}).get('group') not in ('rule', 'fixed'): dbad.append(('rule', e['to']))
    if e['rel'] not in dep['relations']: dbad.append(('rel', e['rel']))
    # a premise held fixed never falls, so nothing it rests on or is licensed by may carry a fall into it
    _carry = e['rel'] in ('rests on', 'rests on rule', 'licenses')
    _into = e['to'] if e['rel'] == 'licenses' else e['from']
    if _carry and PREM.get(_into, {}).get('group') == 'fixed': dbad.append(('fixed premise could fall', e['from'], e['rel'], e['to']))
    # one heading per kind of link on How it fits: resting on A2, A4 or A5 is resting on a method
    if e['rel'] == 'rests on' and e['to'] in PREM: dbad.append(('rests on rule', e['from'] + '->' + e['to']))
for L in dep['spine']['layers']:
    for i in L['ids']:
        if i not in byid: dbad.append(('spine', i))
for p in dep['premises']:
    if p.get('from') and p['from'] not in byid: dbad.append(('premise from', p['from']))
    # a premise that shares an argument's id IS that argument (it falls when set aside): say so in 'from'
    if p['id'] in byid and p.get('from') != p['id']: dbad.append(('premise id is an argument but from differs', p['id'], p.get('from')))
    # a kind is something arguments are OF: it is never an argument, and no argument states it
    if p.get('group') == 'kind' and (p['id'] in byid or p.get('from')): dbad.append(('kind with an argument id or a from', p['id']))
    # the page shows only these three groups; any other would silently drop the premise's box
    if p.get('group') not in ('rule', 'kind', 'fixed'): dbad.append(('premise group', p['id'], p.get('group')))
    m = p.get('members')
    if p.get('group') == 'kind':
        # members is a non-empty id list, or a field and value that match at least one argument
        # the shape falls.members() needs ('ids' wins, else field and value); it is not defensive, so the build refuses any other shape here
        if not isinstance(m, dict) or ('ids' in m and not m['ids']) or not ('ids' in m or (m.get('field') and m.get('value'))):
            dbad.append(('kind without members', p['id']))
        elif 'ids' in m:     # a typo would silently drop an argument from the kind
            dbad += [('kind member', p['id'], i) for i in m['ids'] if i not in byid]
        elif m['field'] not in KIND_FIELDS:   # gate check 80 builds its records with these fields only
            dbad.append(('kind field not allowed', p['id'], m['field'], sorted(KIND_FIELDS)))
        elif not members(p, args):   # the page's own selection rule, so the two cannot differ
            dbad.append(('kind matches nothing', p['id'], m.get('field'), m.get('value')))
        # a kind must never take a premise held fixed: ticking it would fell what is never set aside
        if isinstance(m, dict) and ('ids' in m or m.get('field') in KIND_FIELDS):
            dbad += [('kind takes a fixed premise', p['id'], i) for i in members(p, args)
                     if PREM.get(i, {}).get('group') == 'fixed']
    elif m:
        dbad.append(('members on a premise that is not a kind', p['id']))
    # 'partly': the arguments a kind leaves standing only in part, listed on What if when it is ticked
    q = p.get('partly')
    if q is not None and (p.get('group') != 'kind' or not isinstance(q, dict) or q.get('field') not in KIND_FIELDS
                          or not q.get('value') or not q.get('say')):
        dbad.append(('partly needs a kind, a field in KIND_FIELDS, a value and a say', p['id']))
    elif q is not None:
        # it must name someone, and not the kind's own members (those fall; they are not "standing")
        if not any(a.get(q['field']) == q['value'] for a in args): dbad.append(('partly matches nothing', p['id'], q['field'], q['value']))
        if isinstance(m, dict) and m.get('field') == q['field'] and m.get('value') == q['value']:
            dbad.append(('partly is the same as the members rule', p['id']))
# premise ids are one per box: a duplicate would give two boxes the same data-c and shift fallsAll's bits
_dup = [i for i, c in collections.Counter(p['id'] for p in dep['premises']).items() if c > 1]
if _dup: dbad.append(('duplicate premise ids', _dup))
# rule-N names and describes A1's Nth rule in plain words, typed by hand. The rules must be numbered
# 1..N with no gap, each name must say 'Rule N:', and each anchor must BE the head of A1's Nth rule,
# so a reorder or a reworded rule in A1 fails here instead of mislabelling every What if box. (The
# plain-words part of the name after 'Rule N:' is authored and cannot be checked mechanically.)
_rp = sorted(int(p['id'].split('-')[1]) for p in dep['premises'] if re.fullmatch(r'rule-\d+', p['id']))
if _rp != list(range(1, len(METHOD['rules']) + 1)): dbad.append(('rule premises vs A1 rules', _rp, len(METHOD['rules'])))
for p in dep['premises']:
    if not re.fullmatch(r'rule-\d+', p['id']): continue
    n = int(p['id'].split('-')[1])
    if p.get('group') != 'rule' or p.get('from') != 'A1':   # else it drops its box or claims another argument states it
        dbad.append(('rule premise must be group rule, from A1', p['id'], p.get('group'), p.get('from')))
    head = re.match(r'\*([^*]+)\*', METHOD['rules'][n - 1]) if 1 <= n <= len(METHOD['rules']) else None
    # the anchor is the whole italic head of A1's rule, so any rewording of the head (not just a
    # new first word) fails here
    a = (p.get('anchor') or '').lower()
    if not head or a != head.group(1).strip().lower():
        dbad.append(('rule anchor is not the head of A1 rule', p['id'], p.get('anchor'), head and head.group(1)))
    if not p.get('name', '').startswith(f'Rule {n}:'):
        dbad.append(('rule name does not say its number', p['id'], p.get('name')))
for q in dep.get('open_questions', []):
    if q['id'] not in byid and q['id'] not in PREM: dbad.append(('open question', q['id']))
assert not dbad, f'dependencies.json references unknown ids/relations: {dbad}'
# per-argument upstream/downstream for the detail sheet
up, down = {}, {}
for e in dep['edges']:
    up.setdefault(e['from'], []).append({'id': e['to'], 'rel': e['rel'], 'why': e['why']})
    down.setdefault(e['to'], []).append({'id': e['from'], 'rel': e['rel'], 'why': e['why']})
for a in args:
    a['up'] = up.get(a['id'], []); a['down'] = down.get(a['id'], [])

# ---- what falls if a premise is set aside: computed once, here (pipeline/falls.py) ----------
# Every combination of the toggles, so the page only reads (a license falls only when ALL its
# licensors are set aside, which a union of single results would get wrong). Key: a bitmask over
# PREM_ORDER; value: a hex bitmask over the arguments in page order. One sweep (toggles, then A5)
# serves this table, each premise alone, and the "rests on" view.
PREM_ORDER = [p['id'] for p in dep['premises'] if p['group'] != 'fixed']
SWEEP = all_subsets(sweep_order(PREM_ORDER, dep), args, dep)
SUBSETS = SWEEP[:1 << len(PREM_ORDER)]
FALLS_ALL = all_combinations(PREM_ORDER, args, dep, SUBSETS)
FALLS = {p: sorted(SUBSETS[1 << k][1]) for k, p in enumerate(PREM_ORDER)}   # each premise alone
# "Rests on", jointly, and "states" for each sheet, in What if's own terms (falls.rests_view;
# gate check 80 recomputes and compares them).
_RV = rests_view(args, dep, PREM_ORDER, SWEEP)
for a in args:
    a.update(_RV[a['id']])
_open = {q['id'] for q in dep.get('open_questions', [])}
# "traced" means what the page shows: something on the sheet's Rests-on line (falls.is_traced)
_untraced = [a['id'] for a in args if not is_traced(_RV[a['id']]) and a['id'] not in _open]
_answered = [a['id'] for a in args if is_traced(_RV[a['id']]) and a['id'] in _open]
# a premise's question (rule 5: "no entry names it") is answered once anything rests on it
_lean = {p for v in _RV.values() for p in v['restsOn'] + [x for s in v['restsJointly'] for x in s]}
_answered += sorted(p for p in _open if p in PREM and p in _lean)
assert not _answered, f'open_questions lists arguments already traced, or premises something rests on -- answer and remove: {_answered}'
assert not _untraced, f'arguments neither traced to a premise nor listed in open_questions: {_untraced}'

# ---- scripture table: KJV text for every reference the arguments cite ------
BOOKS = {'Matt':'Matthew','Mark':'Mark','Luke':'Luke','John':'John','Acts':'Acts','Rom':'Romans',
 '1 Cor':'1Corinthians','2 Cor':'2Corinthians','Gal':'Galatians','Eph':'Ephesians','Phil':'Philippians',
 'Col':'Colossians','1 Thess':'1Thessalonians','2 Thess':'2Thessalonians','1 Tim':'1Timothy',
 '2 Tim':'2Timothy','Titus':'Titus','Heb':'Hebrews','Jas':'James','1 Pet':'1Peter','2 Pet':'2Peter',
 '1 John':'1John','Deut':'Deuteronomy','Ezek':'Ezekiel','Judg':'Judges','Exod':'Exodus'}
_bib = {}
def _verse(book, ch, vs):
    if book not in _bib: _bib[book] = json.load(open(f'{WORK}/bib/{book}.json'))
    t = _bib[book]['chapters'][ch-1]['verses'][vs-1]
    return t.get('text') if isinstance(t, dict) else t
REF = re.compile(r'\b((?:[123] )?[A-Z][a-z]+) (\d+):(\d+)(?:[\u2013-](\d+))?')
V, unresolved = {}, set()
blob = json.dumps(args, ensure_ascii=False) + json.dumps(M.get('prefaces', []), ensure_ascii=False)
for mm in REF.finditer(blob):
    bk, ch, v1, v2 = mm.group(1), int(mm.group(2)), int(mm.group(3)), mm.group(4)
    key = f'{bk} {ch}:{v1}' + (f'\u2013{v2}' if v2 else '')
    if key in V or bk not in BOOKS: continue
    try:
        vs = range(v1, int(v2)+1) if v2 else [v1]
        V[key] = ' '.join(f'{n} {_verse(BOOKS[bk], ch, n)}' for n in vs)
    except Exception:
        unresolved.add(key)

unrated = [a['id'] for a in args if a['verdict'] == 'Unrated']
assert not unrated, f'arguments with no recognizable rating: {unrated}'

payload = {
    'scripture': V,
    'deps': dep,
    'falls': FALLS,
    'premOrder': PREM_ORDER,
    'fallsAll': FALLS_ALL,
    'front': fd,
    'args': args,
    'links': links,
    'bands': BANDS,
    'bandOrder': BAND_ORDER,
    'whats': order(a['what'] for a in args),
    'whos': order(a['who'] for a in args),
    'prefaces': M.get('prefaces', []),
    'method': METHOD,
    'stats': {
        'n': len(args),
        'verdicts': dict(collections.Counter(a['verdict'] for a in args)),
        'bands': dict(collections.Counter(a['band'] for a in args)),
        'prose': sum(len(x['body_md']) for x in A),
    },
}
open(WORK+'/_hub_data.json', 'w', encoding='utf-8', newline='').write(json.dumps(payload, ensure_ascii=False))
print('args', len(args), '| links', len(links), '| scripture', len(V), '| unresolved', sorted(unresolved)[:6])
print('whats', payload['whats'])
print('whos ', payload['whos'])
print('bytes', len(json.dumps(payload, ensure_ascii=False)))
