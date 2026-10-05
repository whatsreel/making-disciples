#!/usr/bin/env python3
"""What falls if a premise is set aside: one rule, shared by the build (gen_hub_data.py, which
precomputes it for the page) and gate check 80 (which proves it).

The premises are in sources/dependencies.json: the five reading rules of A1, the method arguments
A2 and A4 (A5 is held fixed), and three kinds of argument whose members are listed or read from a
field. Setting a premise aside removes the arguments that rest on it, then carries the fall along
the authored edges until nothing more changes:
  'rests on', 'rests on rule'   an argument falls if ANY of its targets has fallen;
  'licenses'                    an argument falls only if ALL of its licensors have fallen;
  'repairs', 'bounds', 'answers', 'supports'   never carry a fall.
An argument that is itself a premise (A2, A4) falls when it is set aside.
"""

CARRY_ANY = ('rests on', 'rests on rule')
CARRY_ALL = ('licenses',)
# The fields a kind may read its members from. The build validates against this list and gate
# check 80 builds its argument records with exactly these, so the two always pick the same members.
KIND_FIELDS = ('band', 'what', 'who', 'use', 'survives')

def kind_record(a):
    """An argument from master.json reduced to its id and the fields a kind may read, with the
    page's defaults. Check 80 builds its records with this; the build asserts its own agree."""
    return {'id': a['id'], 'band': a.get('band_name') or 'Method',
            **{k: a.get(k) or '—' for k in KIND_FIELDS if k != 'band'}}

def carry_graph(deps):
    """(anys, alls): anys[x] = what x rests on (falls if ANY falls); alls[x] = what licenses x
    (falls only if ALL fall). The one place the edge kinds are read, for every function below."""
    anys, alls = {}, {}
    for e in deps['edges']:
        if e['rel'] in CARRY_ANY:
            anys.setdefault(e['from'], set()).add(e['to'])
        elif e['rel'] in CARRY_ALL:
            alls.setdefault(e['to'], set()).add(e['from'])
    return anys, alls

def members(premise, args):
    """Argument ids that belong to a kind premise: listed by id, or read from a field; else none."""
    m = premise.get('members')
    if not m:
        return set()
    if 'ids' in m:
        return {a['id'] for a in args if a['id'] in m['ids']}
    return {a['id'] for a in args if a.get(m['field']) == m['value']}

def fallen(set_aside, args, deps, graph=None):
    """The argument ids that fall when the premises in `set_aside` (ids) are set aside."""
    prem = {p['id']: p for p in deps['premises']}
    ids = {a['id'] for a in args}
    gone = set(i for i in set_aside if i in ids)          # A2, A4: the argument is the premise
    for pid in set_aside:
        gone |= members(prem[pid], args)
    down = set(set_aside)                                 # premises and arguments that have fallen
    anys, alls = graph or carry_graph(deps)
    changed = True
    while changed:
        changed = False
        for i in sorted(ids - gone):
            hit = anys.get(i, set()) & (gone | down)
            lic = alls.get(i)
            if hit or (lic and lic <= (gone | down)):
                gone.add(i)
                changed = True
    return gone

def all_subsets(order, args, deps):
    """[(mask, fallen set)] for every subset of `order`, mask = bitmask over `order`."""
    g = carry_graph(deps)
    return [(mask, fallen([p for k, p in enumerate(order) if mask >> k & 1], args, deps, g))
            for mask in range(1 << len(order))]

def sweep_order(order, deps):
    """The toggles, then the premises held fixed. Because the fixed ones come last, the first
    2**len(order) entries of a sweep over this order are exactly the toggle-only subsets, so one
    sweep serves both the page's table and the "rests on" view."""
    return list(order) + [p['id'] for p in deps['premises'] if p['group'] == 'fixed' and p['id'] not in order]

def all_combinations(order, args, deps, subsets=None):
    """For every subset of the premises in `order` (index = bitmask over `order`), the arguments
    that fall, as a hex bitmask over `args` in their order (bit i = args[i])."""
    return [format(sum(1 << i for i, a in enumerate(args) if a['id'] in gone), 'x')
            for _, gone in (subsets or all_subsets(order, args, deps))]

def minimal_sets(order, args, deps, subsets=None):
    """{argument id: the smallest sets of premises (from `order`) whose setting aside makes it fall}.
    A set is kept only if no smaller kept set is inside it, so {A2, A4} for B2 means: neither alone
    is enough, both together are. This is what the page names as an argument's reason for falling."""
    out = {}
    for mask, gone in sorted(subsets or all_subsets(order, args, deps), key=lambda mg: (bin(mg[0]).count('1'), mg[0])):
        for i in gone:
            if mask and not any(s & mask == s for s in out.get(i, ())):
                out.setdefault(i, []).append(mask)
    return {i: [[p for k, p in enumerate(order) if m >> k & 1] for m in ms] for i, ms in out.items()}

def rests_view(args, deps, order, subsets=None):
    """{argument id: {'states', 'kinds', 'restsOn', 'restsJointly'}}: what each argument's sheet,
    the "What fell" reasons and How it fits show. In What if's own terms:
      states        the premises it states or is (A1 the five rules; A2, A4, A5 themselves);
      kinds         the kinds it is one of (E1 IS an argument from wisdom; it does not rest on one);
      restsOn       each premise that makes it fall when set aside ALONE, other than the above;
      restsJointly  the smallest sets of two or more that make it fall only together.
    A premise held fixed (A5) is tested the same way, though the page never sets it aside: what
    rests on A5 alone is still worth showing, but no joint set names it. `subsets`, if given, is the sweep over
    sweep_order(order, deps) -- the toggles, then the fixed premises."""
    prem = {p['id']: p for p in deps['premises']}
    mins = minimal_sets(sweep_order(order, deps), args, deps, subsets)
    out = {}
    for a in args:
        i = a['id']
        states = sorted(p for p, pr in prem.items() if pr.get('from') == i)
        kinds = sorted(p for p, pr in prem.items() if i in members(pr, args))
        own = set(states) | set(kinds)
        sets = [s for s in mins.get(i, []) if not set(s) & own]
        sets = [s for s in sets if not _derived(i, s, prem, args, deps)]
        # a premise held fixed is never set aside, so "falls only if both are set aside" can never
        # name one; resting on it alone is still shown
        sets = [s for s in sets if len(s) == 1 or not any(prem[p]['group'] == 'fixed' for p in s)]
        out[i] = {'states': states, 'kinds': kinds,
                  'restsOn': sorted(s[0] for s in sets if len(s) == 1),
                  'restsJointly': [s for s in sets if len(s) > 1]}
    return out

def _derived(i, s, prem, args, deps):
    """True if set `s` makes argument `i` fall only because a kind in it takes a premise-argument
    with it: B2's [A2, the Twelve kind] holds only because that kind takes A4, and [A2, A4] already
    says so. Showing it would tell the reader B2 rests on the kind, which it does not. Tested by
    replacing each such kind with just the premise-arguments it takes: if `i` still falls, a set of
    premises already explains it and `s` is derived. If the kind is needed for an ordinary member
    too, `i` stands without it and the kind stays a reason. Any set size, a single kind included."""
    kinds = {k for k in s if prem[k]['group'] == 'kind'
             and any(m in prem and m not in s for m in members(prem[k], args))}
    if not kinds:
        return False
    taken = {m for k in kinds for m in members(prem[k], args) if m in prem}
    return i in fallen((set(s) - kinds) | taken, args, deps)

def is_traced(view):
    """An argument is traced when its sheet has something on the Rests-on line: a premise it rests
    on (alone or jointly), a kind it is one of, or a premise it states. The build's untraced list
    and gate check 80 both use this, so 'traced' means what the reader sees."""
    return any(view[k] for k in ('restsOn', 'restsJointly', 'kinds', 'states'))

def has_cycle(deps):
    """A carrying edge path that returns to where it started (the loop only), or None."""
    anys, alls = carry_graph(deps)
    g = {x: sorted(t) for x, t in anys.items()}
    for x, lic in alls.items():
        g.setdefault(x, [])
        g[x] = sorted(set(g[x]) | lic)
    state = {}
    def visit(n, path):
        state[n] = 1
        for m in g.get(n, ()):
            if state.get(m) == 1:
                loop = path + [n]
                return loop[loop.index(m):] + [m]
            if not state.get(m):
                r = visit(m, path + [n])
                if r:
                    return r
        state[n] = 2
        return None
    for n in sorted(g):
        if not state.get(n):
            r = visit(n, [])
            if r:
                return r
    return None
