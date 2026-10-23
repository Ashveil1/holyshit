"""B-500/501: iterative deepening of base expression depth (1->2), cost-ordered, via cur7 LIST_OVERRIDE. LEDGER B-500P."""
import json, random, sys, time
import cur7

def tup(e):
    return tuple(tup(t) for t in e) if isinstance(e, list) else e

def nodes(e):
    return 1 if isinstance(e, str) else 1 + sum(nodes(t) for t in e[1:])

def run_task(task, seed, cap=6_000_000):
    # pin library exactly like main() baselib path
    for k in [k for k in cur7.LIB if k not in ('add', 'sub')]: del cur7.LIB[k]
    cur7.EXCL.clear(); cur7.EXCL.add(task); cur7.search._baselib_done = False
    cur7.VALID[:] = []; cur7.ADV[:] = []
    cur7.ev.cache_clear()
    rng = random.Random(seed)
    train = [cur7.gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    vr = random.Random(5000 + seed)
    cur7.VALID[:] = [cur7.gen(task, vr, sc) for sc in (1, 2) for _ in range(16)]
    # baseline arm: default bases (leaves only)
    t0 = time.time(); pb, tried_b, _ = cur7.search(train, 'baselib val', tried_cap=cap); dt_b = time.time() - t0
    # deepened arm: capture ops after pinning, build cost-ordered depth<=2 bases
    ops = [o for o in cur7.LIB]
    L = list(cur7.LEAVES)
    E1 = [(o, p, q) for o in ops for p in L for q in L if p != q or o == 'add']
    deep = []
    for o in ops:
        for e1 in E1:
            for q in L: deep.append((o, e1, q))
            for q in L: deep.append((o, q, e1))
    for o in ops:
        for e1 in E1:
            for e2 in E1: deep.append((o, e1, e2))
    bases_ext = L + E1 + deep  # already cost-ordered by construction (1 < 3 < 5 < 7 nodes)
    for k in [k for k in cur7.LIB if k not in ('add', 'sub')]: del cur7.LIB[k]
    cur7.EXCL.clear(); cur7.EXCL.add(task); cur7.search._baselib_done = False
    cur7.ev.cache_clear()
    cur7.LIST_OVERRIDE = {'bases': bases_ext, 'steps_pair': [('a', 'b')], 'steps_single': [('a', 'b')]}  # B-500: dummy step - zero-loop hypothesis, pre-stated
    t0 = time.time(); pd, tried_d, _ = cur7.search(train, 'baselib val', tried_cap=cap); dt_d = time.time() - t0
    cur7.LIST_OVERRIDE = None
    def gen_test(p):
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
    return {'task': task, 'seed': seed,
            'baseline': {'found': pb is not None, 'tried': tried_b, 'dt': round(dt_b, 1),
                         'prog': cur7.show_prog(pb) if pb else None, 'gen': gen_test(pb)},
            'deep': {'found': pd is not None, 'tried': tried_d, 'dt': round(dt_d, 1),
                     'prog': cur7.show_prog(pd) if pd else None, 'gen': gen_test(pd),
                     'n_bases': len(bases_ext)}}

for task in ('absdiff', 'lcm'):
    print(json.dumps(run_task(task, 0)), flush=True)
print('DONE', flush=True)
