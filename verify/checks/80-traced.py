#!/usr/bin/env python3
"""80 traced: every argument traces to a reading rule or method premise, or is an open question,
and every link between arguments can be pointed to in the index.

WHY: the What-if view says what falls if a reading rule is set aside, so the links it follows
must hold up (Jon, 2026-10-04: "the logic of it has to be airtight"). Links were once text-mined
and overclaimed; then authored with paraphrased reasons, four of which the index contradicts
(chunk E). So: each link's reason is a verbatim quote from the entry of one of its two ends; an
argument nobody could trace confidently is listed in open_questions with its question, never
given a guessed link; a reason is at least MIN_WHY characters and comes from the entry itself, never
from a section heading or the closing section; carrying links never loop; an open question is never
one already answered; and what falls, for one premise and for every combination, and what each
argument is shown to rest on, are the same as the page was built with. Uses pipeline/falls.py, the build's own rule.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, need_build
from falls import fallen, has_cycle, all_combinations, all_subsets, minimal_sets, rests_view, is_traced, sweep_order, kind_record

def entries(index):
    """{argument id: its entry's text}, each entry ending at the next heading of any level, so a
    section heading or the closing section is never counted as part of the entry before it.
    'C1a–C1f' (the six things' preface) counts for C1a."""
    heads = [(m.start(), m.group(1)) for m in re.finditer(r'^#{1,4} (?:([A-G]\d+[a-z]?(?:–C1f)?)\.)?', index, re.M)]
    out = {}
    for n, (p, i) in enumerate(heads):
        if not i:
            continue
        end = heads[n + 1][0] if n + 1 < len(heads) else len(index)
        k = 'C1a' if i == 'C1a–C1f' else i
        out[k] = out.get(k, '') + index[p:end]
    return out

MIN_WHY = 20   # a reason shorter than this could match almost any entry

def check(args, deps, index, built_falls=None, built_all=None):
    ent = entries(index)
    prem = [p['id'] for p in deps['premises'] if p['group'] != 'fixed']
    sweep = all_subsets(sweep_order(prem, deps), args, deps)  # one sweep (toggles, then fixed), shared below
    subs = sweep[:1 << len(prem)]                             # the toggle-only subsets
    view = rests_view(args, deps, prem, sweep)
    traced = {i for i, v in view.items() if is_traced(v)}     # what the sheet shows, as the build asserts
    opened = {q['id'] for q in deps.get('open_questions', [])}
    untraced = sorted(i for i in view if i not in traced and i not in opened)
    # a question already answered: an argument now traced, or a premise something now rests on
    leaning = {p for v in view.values() for p in v['restsOn'] + [x for s in v['restsJointly'] for x in s]}
    open_traced = sorted(i for i in opened if i in traced or i in leaning)
    unpointed = [e for e in deps['edges'] if len(e['why'].strip()) < MIN_WHY
                 or not any(e['why'] in ent.get(x, '') for x in (e['from'], e['to']))]
    cycle = has_cycle(deps)
    once = {p: sorted(subs[1 << k][1]) for k, p in enumerate(prem)}
    stale = [p for p in prem if built_falls is not None and built_falls.get(p) != once[p]]
    # every combination the page reads (licenses need ALL licensors, so singles are not enough)
    combos = None if built_all is None else (built_all.get('premOrder') == prem and
                                             built_all.get('fallsAll') == all_combinations(prem, args, deps, subs))
    if combos is False:
        stale.append('every combination')
    # what each sheet, "What fell" and How it fits say an argument rests on
    if built_all is not None:
        built = {a['id']: a for a in built_all.get('args', [])}
        for i, v in view.items():
            if any(built.get(i, {}).get(k) != v[k] for k in v):
                stale.append(f'rests on, {i}')
    n, ids = len(args), {a['id'] for a in args}
    print(f'COUNT traced {len(traced)}/{n}, open questions {len(opened & ids)} arguments '
          f'+ {len(opened - ids)} premises, neither {len(untraced)}; links {len(deps["edges"])}, '
          f'not pointable {len(unpointed)}; cycles {0 if not cycle else 1}; premises {len(prem)}, '
          f'differ from build {len(stale)}')
    for i in untraced[:5]:
        print(f'SAMPLE {i}: its sheet would show no premise, and it is not in open_questions')
    for i in open_traced[:5]:
        print(f'SAMPLE {i}: in open_questions but already traced -- answer and remove the question')
    for e in unpointed[:5]:
        print(f'SAMPLE {e["from"]} {e["rel"]} {e["to"]}: why under {MIN_WHY} characters or not found verbatim in either entry')
    if cycle:
        print('SAMPLE cycle: ' + ' -> '.join(cycle))
    for p in stale[:5]:
        print(f'SAMPLE {p}: falls differ from what the page was built with')
    return not (untraced or open_traced or unpointed or cycle or stale)

if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
    idx = ('### G1. "x"\nthe first reason, which rests\n### G2. "y"\nthe second one, which is licensed\n'
           '### G3. "z"\nthe third reason, also stated\n### G4. "w"\nthe fourth rests on the third\n'
           '### G5. "m"\na method that is a premise\n### G6. "n"\nthe sixth rests on the method\n'
           '### G7. "o"\nthe seventh, licensed by two\n'
           '### G8. "p"\nan ordinary member of a kind\n### G9. "q"\nthe ninth, licensed by a method and a member\n'
           '## Closing\na sentence from the closing section\n')
    args = [{'id': i} for i in ('G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9')]
    def deps(edges, opened=()):
        # two rules, a kind listed by id (G4 is one of it), a premise held fixed (G1 rests on it), and
        # a method that is itself an argument (G5) taken by a kind (k2): G6 and G7 rest on G5, not on k2;
        # and a kind (k3) that takes G5 and an ordinary member G8: G9 needs both, so k3 IS its reason
        return {'premises': [{'id': 'r1', 'group': 'rule'}, {'id': 'r2', 'group': 'rule'},
                             {'id': 'k1', 'group': 'kind', 'members': {'ids': ['G4']}},
                             {'id': 'f1', 'group': 'fixed'}, {'id': 'G5', 'group': 'rule', 'from': 'G5'},
                             {'id': 'k2', 'group': 'kind', 'members': {'ids': ['G5']}},
                             {'id': 'k3', 'group': 'kind', 'members': {'ids': ['G5', 'G8']}}],
                'edges': [{'from': f, 'rel': r, 'to': t, 'why': w} for f, r, t, w in edges],
                'open_questions': [{'id': i} for i in opened]}
    good = [('G1', 'rests on rule', 'r1', 'the first reason, which rests'),
            ('G1', 'rests on rule', 'f1', 'the first reason, which rests'),
            ('G3', 'rests on rule', 'r2', 'the third reason, also stated'),
            ('G1', 'licenses', 'G2', 'the second one, which is licensed'),
            ('G3', 'licenses', 'G2', 'the second one, which is licensed'),
            ('G4', 'rests on', 'G3', 'the fourth rests on the third'),
            ('G6', 'rests on rule', 'G5', 'the sixth rests on the method'),
            ('G6', 'licenses', 'G7', 'the seventh, licensed by two'),
            ('G3', 'licenses', 'G7', 'the seventh, licensed by two'),
            ('G5', 'licenses', 'G9', 'the ninth, licensed by a method and a member'),
            ('G8', 'licenses', 'G9', 'the ninth, licensed by a method and a member')]
    # the propagation rules themselves: ANY for rests on, ALL for licenses; and the minimal sets
    rules_ok = (sorted(fallen(['r2'], args, deps(good))) == ['G3', 'G4']        # G2 keeps G1's license
                and sorted(fallen(['r1', 'r2'], args, deps(good))) == ['G1', 'G2', 'G3', 'G4']
                and minimal_sets(['r1', 'r2'], args, deps(good)).get('G2') == [['r1', 'r2']])
    good_g = deps(good)
    order = ['r1', 'r2', 'k1', 'G5', 'k2', 'k3']
    view = rests_view(args, good_g, order)
    # joint sets; the fixed premise tested by falling, not by reach; a kind's member is OF it, not resting on it
    # G2 needs both licensors down: G1 falls with r1 or with the fixed f1, G3 with r2; f1 is never set
    # aside, so [r2, f1] is not shown
    rules_ok = (rules_ok and view['G2']['restsJointly'] == [['r1', 'r2']] and view['G1']['restsOn'] == ['f1', 'r1']
                and view['G2']['restsOn'] == [] and view['G4']['restsOn'] == ['r2'] and view['G4']['kinds'] == ['k1']
                # a kind that takes a method with it is not a reason in its own right, alone or jointly
                and view['G6']['restsOn'] == ['G5'] and view['G6']['restsJointly'] == []
                and sorted(map(sorted, view['G7']['restsJointly'])) == [['G5', 'r2']] and view['G5']['states'] == ['G5']
                # ...but a kind needed for an ordinary member too is a reason (code review round 9)
                and view['G9']['restsOn'] == ['k3'])
    right_all = {'premOrder': order, 'fallsAll': all_combinations(order, args, good_g),
                 'args': [dict(id=i, **v) for i, v in view.items()]}
    wrong_all = dict(right_all, fallsAll=right_all['fallsAll'][:-1] + ['0'])
    singles = {p: sorted(fallen([p], args, good_g)) for p in order}
    # the page says G2 rests on r1 alone, though it falls only with r2 as well (the first review's defect)
    wrong_rests = dict(right_all, args=[dict(a, restsOn=['r1'], restsJointly=[]) if a['id'] == 'G2' else a
                                        for a in right_all['args']])
    no_g4 = [e for e in good if e[:3] != ('G4', 'rests on', 'G3')]   # the edge each why-fault replaces
    faults = {   # name: (deps, built_falls, built_all)
        'untraced': (deps(good[:1]), None, None),                    # G2, G3 trace to nothing (G4 is of k1)
        'paraphrase': (deps(no_g4 + [('G4', 'rests on', 'G3', 'a reason nobody ever wrote')]), None, None),
        'short why': (deps(no_g4 + [('G4', 'rests on', 'G3', 'rests on')]), None, None),
        'why from the closing section': (deps(no_g4 + [('G4', 'rests on', 'G3', 'a sentence from the closing section')]), None, None),
        'cycle': (deps(good + [('G3', 'rests on', 'G4', 'the third reason, also stated')]), None, None),
        'open question already traced': (deps(good, opened=['G1']), None, None),
        'premise question already answered': (deps(good, opened=['r1']), None, None),   # G1 rests on r1
        'stale rests on': (good_g, None, wrong_rests),
        'stale singles': (good_g, dict(singles, r2=['G3']), None),               # the build left out G4
        'stale combinations': (good_g, None, wrong_all),
    }
    caught = [k for k, (d, bf, ba) in faults.items() if not check(args, d, idx, bf, ba)]
    clean = check(args, good_g, idx, singles, right_all)
    print(f'COUNT selftest propagation rules {"ok" if rules_ok else "WRONG"}; planted {len(faults)}, '
          f'caught {len(caught)}; clean graph passes {clean}')
    for k in faults:
        if k not in caught:
            print(f'SAMPLE missed: {k}')
    sys.exit(1 if rules_ok and len(caught) == len(faults) and clean else 0)

need_build()
deps = json.load(open(os.path.join(ROOT, 'sources', 'dependencies.json'), encoding='utf-8'))
index = open(os.path.join(ROOT, 'sources', 'argument-index.md'), encoding='utf-8').read()
M = json.load(open(os.path.join(ROOT, 'master.json'), encoding='utf-8'))
# the fields a kind may read, built by the same helper the build asserts against (falls.kind_record),
# so a kind picks the same members here as on the page
args = [kind_record(a) for a in M['arguments']]
data = os.path.join(ROOT, 'work', '_hub_data.json')
if not os.path.isfile(data):
    print('COUNT built-data 0/1')
    print('SAMPLE work/_hub_data.json missing: check 10 (the build) must run first')
    sys.exit(1)
D = json.load(open(data, encoding='utf-8'))
print(f'COUNT combinations the page reads {len(D.get("fallsAll") or [])}')
sys.exit(0 if check(args, deps, index, D.get('falls') or {}, D) else 1)
