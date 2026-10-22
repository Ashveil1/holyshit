"""B-337P: covering-selection prediction test on div (pre-registered in LEDGER B-337P)."""
import random, json
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
def one(train, cap=3_000_000):
    cur7.VALID[:] = []; ADV[:] = []; EXCL.clear(); CAPF[0] = 400
    return search(train, 'baselib,simp', tried_cap=cap)
def general(p, seed):
    f = make_fn(p); te = random.Random(1000 + seed); bad = 0; CAPF[0] = 20000
    for sc in (1, 2, 3, 4):
        for _ in range(40):
            x, y, r = gen('div', te, sc)
            try: bad += int(f(x, y) != r)
            except (Fail, KeyError, RecursionError, OverflowError, ZeroDivisionError): bad += 1
    CAPF[0] = 400; ev.cache_clear()
    return bad
def covering(pool, n=5):
    picked, sc_seen, bk_seen = [], set(), set()
    while len(picked) < n:
        best, bs = None, -1
        for c in pool:
            if c in picked: continue
            x, y, r = c
            sc_gain = len({1 if max(x,y)<10 else 2 if max(x,y)<100 else 3 if max(x,y)<1000 else 4} - sc_seen)
            bk_gain = len({x//10, y//10} - bk_seen)
            s = 10*sc_gain + bk_gain
            if s > bs: best, bs = c, s
        if best is None: break
        picked.append(best)
        x, y, r = best
        sc_seen.add(1 if max(x,y)<10 else 2 if max(x,y)<100 else 3 if max(x,y)<1000 else 4)
        bk_seen |= {x//10, y//10}
    return picked
for seed in (0, 1, 2):
    rng = random.Random(seed); pool = [gen('div', rng, rng.choice([1, 2])) for _ in range(25)]
    train = covering(pool, 5)
    p, tried, dt = one(train)
    bad = general(p, seed) if p else None
    row = {'task': 'div', 'cond': 'C5', 'seed': seed, 'found': p is not None, 'tried': tried,
           'dt': round(dt, 1), 'wrong40': bad,
           'prog': cur7.show_prog(p) if p else None}
    print(json.dumps(row, default=str), flush=True)
print('DONE', flush=True)
