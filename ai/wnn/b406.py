"""B-406: anti-unify pairs of learned programs into partial schemas; test as search ordering on held-out tasks.
Arms: baseline cur7.search('baselib') vs schema-phase-then-full. See LEDGER B-406P."""
import json, random, sys, time
from itertools import islice
import cur7

HOLE = '?'
CAP = 1_000_000
PHASE1_BUDGET = 500_000
HELDOUT = ['absdiff', 'lcm', 'isprime', 'cube', 'even']
SEED = 0

def tup(e):
    return tuple(tup(t) for t in e) if isinstance(e, list) else e

def lgg_expr(a, b):
    if a == b: return a
    if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b) and a and b and a[0] == b[0]:
        return tuple([a[0]] + [lgg_expr(x, y) for x, y in zip(a[1:], b[1:])])
    return HOLE

def lgg_prog(p, q):
    i1, (c1, b1, s01, s11, cb1), o1 = p
    i2, (c2, b2, s02, s12, cb2), o2 = q
    comb = None if cb1 is None and cb2 is None else (HOLE if (cb1 is None) != (cb2 is None) else tuple(lgg_expr(x, y) for x, y in zip(cb1, cb2)))
    return {'init': i1 if i1 == i2 else HOLE, 'cond': lgg_expr(c1, c2), 'base': b1 if b1 == b2 else HOLE,
            's0': lgg_expr(s01, s02), 's1': lgg_expr(s11, s12), 'comb': comb, 'post': o1 if o1 == o2 else HOLE}

def has_hole(e):
    if e == HOLE: return True
    return isinstance(e, tuple) and any(has_hole(x) for x in e)

def fixed_fields(sch):
    n = 0
    for f in ('init', 'base', 'post'):
        if sch[f] != HOLE: n += 1
    for f in ('cond', 's0', 's1'):
        if not has_hole(sch[f]): n += 1
    if sch['comb'] is None or not has_hole(sch['comb']): n += 1
    return n

def match_expr(sch, val):
    if sch == HOLE: return True
    if isinstance(sch, tuple):
        return isinstance(val, tuple) and len(val) == len(sch) and all(match_expr(s, v) for s, v in zip(sch, val))
    return sch == val

def comb_match(schc, c):
    if schc == HOLE: return True
    if schc is None: return c is None
    return c is not None and all(match_expr(s, v) for s, v in zip(schc, c))

def prog_matches(sch, p):
    init, (cond, base, s0, s1, comb), post = p
    return ((sch['init'] == HOLE or sch['init'] == init) and match_expr(sch['cond'], cond)
            and (sch['base'] == HOLE or sch['base'] == base) and match_expr(sch['s0'], s0)
            and match_expr(sch['s1'], s1) and comb_match(sch['comb'], comb)
            and (sch['post'] == HOLE or sch['post'] == post))

def filtered_lists(sch, cap_lists):
    fl = {}
    fl['inits'] = [i for i in cap_lists['inits'] if sch['init'] == HOLE or i == sch['init']]
    fl['conds'] = [c for c in cap_lists['conds'] if match_expr(sch['cond'], c)]
    fl['bases'] = [b for b in cap_lists['bases'] if sch['base'] == HOLE or b == sch['base']]
    fl['steps_pair'] = [st for st in cap_lists['steps_pair'] if match_expr(sch['s0'], st[0]) and match_expr(sch['s1'], st[1])]
    fl['steps_single'] = [st for st in cap_lists['steps_single'] if match_expr(sch['s0'], st[0]) and match_expr(sch['s1'], st[1])]
    fl['combs'] = [c for c in cap_lists['combs'] if comb_match(sch['comb'], c)]
    fl['posts'] = {k: v for k, v in cap_lists['posts'].items() if sch['post'] == HOLE or k == sch['post']}
    return fl

def key_stream(fl):
    for comb in fl['combs']:
        st = fl['steps_pair'] if comb is None else fl['steps_single']
        for init in fl['inits']:
            for cond in fl['conds']:
                for base in fl['bases']:
                    for (s0, s1) in st:
                        yield (init, cond, base, s0, s1, comb)

def reset_lib():
    for k in [k for k in cur7.LIB if k not in ('add', 'sub')]: del cur7.LIB[k]
    cur7.EXCL.clear(); cur7.search._baselib_done = False
    cur7.VALID[:] = []; cur7.ADV[:] = []

def clear_caches():
    cur7.ev.cache_clear(); cur7.cev.cache_clear()

def main():
    base = {t: tup(p) for t, p in json.load(open('/tmp/c7_prog_0_base.json')).items()}
    tasks = sorted(base)
    schemas = {}
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            s = lgg_prog(base[tasks[i]], base[tasks[j]])
            key = json.dumps(s, sort_keys=True, default=str)
            schemas.setdefault(key, {'schema': s, 'pairs': [], 'fixed': fixed_fields(s)})['pairs'].append((tasks[i], tasks[j]))
    nontrivial = [v for v in schemas.values() if v['fixed'] >= 3]
    nontrivial.sort(key=lambda v: -v['fixed'])
    print(json.dumps({'n_schemas_all': len(schemas), 'n_nontrivial': len(nontrivial),
                      'schemas': [{'fixed': v['fixed'], 'pairs': v['pairs'], 'schema': str(v['schema'])} for v in nontrivial]}), flush=True)
    results = []
    for task in HELDOUT:
        rng = random.Random(SEED)
        train = [cur7.gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
        # baseline arm (cold caches), capture lists
        reset_lib(); cur7.EXCL.add(task); clear_caches()
        cap_lists = {}; cur7.LIST_CAPTURE = cap_lists; cur7.LIST_OVERRIDE = None; cur7.SKIP_SET = None
        t0 = time.time(); pb, tried_b, _ = cur7.search(train, 'baselib', tried_cap=CAP); dt_b = time.time() - t0
        cur7.LIST_CAPTURE = None
        rec = {'task': task, 'baseline': {'found': pb is not None, 'tried': tried_b, 'dt': round(dt_b, 1),
                                          'prog': cur7.show_prog(pb) if pb else None}}
        # schema arm (cold caches)
        reset_lib(); cur7.EXCL.add(task); clear_caches()
        cur7.LIST_CAPTURE = None
        skip = set(); p1_tried = 0; found_sch = None; ps = None
        t0 = time.time()
        for si, v in enumerate(nontrivial):
            if p1_tried >= PHASE1_BUDGET: break
            fl = filtered_lists(v['schema'], cap_lists)
            if not all([fl['inits'], fl['conds'], fl['bases'], fl['combs'], fl['posts']]): continue
            keys = list(islice(key_stream(fl), PHASE1_BUDGET - p1_tried + len(skip)))
            keys = [k for k in keys if k not in skip]
            if not keys: continue
            cur7.SKIP_SET = skip; cur7.LIST_OVERRIDE = fl
            ps, tr, _ = cur7.search(train, 'baselib', tried_cap=len(keys))
            p1_tried += tr; skip.update(keys)
            if ps is not None: found_sch = si; break
        dt_p1 = time.time() - t0
        cur7.LIST_OVERRIDE = None; cur7.SKIP_SET = None
        if ps is not None:
            rec['schema_arm'] = {'found': True, 'phase': 1, 'tried': p1_tried, 'dt': round(dt_p1, 1),
                                 'schema_idx': found_sch, 'prog': cur7.show_prog(ps)}
        else:
            extra = tried_b if pb is not None else CAP
            rec['schema_arm'] = {'found': pb is not None, 'phase': 2, 'tried': p1_tried + extra,
                                 'dt': round(dt_p1 + dt_b, 1), 'schema_idx': None,
                                 'prog': cur7.show_prog(pb) if pb else None,
                                 'note': 'phase1 missed; tried = phase1 + baseline (double-counted)'}
        sol = ps if ps is not None else pb
        if sol is not None:
            rec['solution_matches_schemas'] = [si for si, v in enumerate(nontrivial) if prog_matches(v['schema'], sol)]
        results.append(rec)
        print(json.dumps(rec), flush=True)
    print('DONE', flush=True)

if __name__ == '__main__':
    main()
