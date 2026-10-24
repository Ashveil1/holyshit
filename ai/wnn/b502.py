"""B-502: depth-2 fragments mined from PAIRS OF USED depth-1 exprs. Arm A mined-only (expressivity-proof arm), Arm B mined-first+deep (position cost). LEDGER B-502 design + verdict."""
import json, random, time
import cur7

def tup(e):
    return tuple(tup(t) for t in e) if isinstance(e, list) else e

def used_exprs():
    d = json.load(open('/tmp/c7_prog_0_base.json'))
    used = set()
    def walk(e):
        if isinstance(e, list):
            if len(e) == 3 and isinstance(e[0], str) and e[0] not in ('lt', 'nlt'):
                used.add(tuple(tup(t) for t in e))
            for t in e: walk(t)
    for t, (init, prog, pn) in d.items():
        cond, base, s0, s1, comb = prog
        walk(base); walk(s0); walk(s1)
        if comb: walk(comb[1])
    return sorted(used)

def fresh(task, seed):
    for k in [k for k in cur7.LIB if k not in ('add', 'sub')]: del cur7.LIB[k]
    cur7.EXCL.clear(); cur7.EXCL.add(task); cur7.search._baselib_done = False
    cur7.VALID[:] = []; cur7.ADV[:] = []
    cur7.ev.cache_clear()
    rng = random.Random(seed)
    train = [cur7.gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    vr = random.Random(5000 + seed)
    cur7.VALID[:] = [cur7.gen(task, vr, sc) for sc in (1, 2) for _ in range(16)]
    cur7.search(train[:1], 'baselib val', tried_cap=1)  # force pin
    return train

def gen_test(p, task, seed):
    if p is None: return None
    f = cur7.make_fn(p); te = random.Random(1000 + seed); res = {}; cur7.CAPF[0] = 20000
    for sc in (1, 2, 3, 4):
        ok = 0
        for _ in range(40):
            x, y, r = cur7.gen(task, te, sc)
            try: ok += int(f(x, y) == r)
            except Exception: pass
        res[sc] = ok
    cur7.CAPF[0] = 400; cur7.ev.cache_clear()
    return res

task = 'absdiff'; seed = 0
train = fresh(task, seed)
ops = [o for o in cur7.LIB]
L = list(cur7.LEAVES)
E1 = [(o, p, q) for o in ops for p in L for q in L if p != q or o == 'add']
U = used_exprs()
mined = [(o, e1, e2) for o in ops for e1 in U for e2 in U]
deep = []
for o in ops:
    for e1 in E1:
        for q in L: deep.append((o, e1, q))
        for q in L: deep.append((o, q, e1))
for o in ops:
    for e1 in E1:
        for e2 in E1: deep.append((o, e1, e2))
print(json.dumps({'setup': {'ops': ops, 'n_E1': len(E1), 'U': [list(u) for u in U], 'n_mined': len(mined), 'n_deep': len(deep),
                            'absdiff_fragment_in_mined': ('sub', ('max', 'a', 'b'), ('min', 'a', 'b')) in mined}}), flush=True)

for arm, bases in (('A_mined_only', L + E1 + mined), ('B_mined_first_deep', L + E1 + mined + deep)):
    fresh(task, seed)
    cur7.LIST_OVERRIDE = {'bases': bases, 'steps_pair': [('a', 'b')], 'steps_single': [('a', 'b')]}
    t0 = time.time(); p, tried, _ = cur7.search(train, 'baselib val', tried_cap=6_000_000); dt = time.time() - t0
    cur7.LIST_OVERRIDE = None
    print(json.dumps({'task': task, 'seed': seed, 'arm': arm, 'found': p is not None, 'tried': tried, 'dt': round(dt, 1),
                      'prog': cur7.show_prog(p) if p else None, 'gen': gen_test(p, task, seed), 'n_bases': len(bases)}), flush=True)
print('DONE', flush=True)
