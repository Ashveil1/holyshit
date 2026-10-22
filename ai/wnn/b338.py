"""B-338P: mul under selection, curriculum-relevant config (pre-registered in LEDGER B-338P)."""
import random, json
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
def one(train, cap=6_000_000):
    cur7.VALID[:] = []; ADV[:] = []; EXCL.clear(); EXCL.add('mul'); CAPF[0] = 400
    search._baselib_done = False  # honor EXCL at pin (B-523-H1 fix)
    return search(train, 'baselib,simp', tried_cap=cap)
def general(p, seed):
    f = make_fn(p); te = random.Random(1000 + seed); bad = 0; CAPF[0] = 20000
    for sc in (1, 2, 3, 4):
        for _ in range(40):
            x, y, r = gen('mul', te, sc)
            try: bad += int(f(x, y) != r)
            except (Fail, KeyError, RecursionError, OverflowError, ZeroDivisionError): bad += 1
    CAPF[0] = 400; ev.cache_clear()
    return bad
for seed in (0, 1):
    rng = random.Random(seed); full = [gen('mul', rng, rng.choice([1, 2])) for _ in range(25)]
    for cond, train in (('R5', full[:5]), ('B5', boundary('mul')[:5]), ('R25', full)):
        p, tried, dt = one(train)
        bad = general(p, seed) if p else None
        row = {'task': 'mul', 'cond': cond, 'seed': seed, 'found': p is not None, 'tried': tried,
               'dt': round(dt, 1), 'wrong40': bad,
               'prog': cur7.show_prog(p) if p else None}
        print(json.dumps(row, default=str), flush=True)
print('DONE', flush=True)
