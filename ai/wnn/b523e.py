"""B-523-H1 clean re-verification: per-cell pin reset (search._baselib_done=False) so each cell's
EXCL is honored at pin time. Cells replace the polluted records: mul s0 n3 (b523d's polluted
in-process cell discarded), div s1 n3 (pair with b523d's clean s0 n3 = 4202713)."""
import random, json
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
CELLS = [('div', 3, 1), ('mul', 3, 0)]
ABL = 'baselib,simp,adv'
def one(task, train, cap=6_000_000):
    cur7.VALID[:] = []; ADV[:] = boundary(task); EXCL.clear(); EXCL.add(task); CAPF[0] = 400
    search._baselib_done = False  # B-523-H1: re-pin honoring THIS cell's EXCL
    return search(train, ABL, tried_cap=cap)
def general(p, task, seed):
    f = make_fn(p); te = random.Random(1000 + seed); res = {}; CAPF[0] = 20000
    for sc in (1, 2, 3, 4):
        ok = 0
        for _ in range(40):
            x, y, r = gen(task, te, sc)
            try: ok += int(f(x, y) == r)
            except (Fail, KeyError, RecursionError, OverflowError): pass
        res[sc] = ok
    CAPF[0] = 400; ev.cache_clear()
    return res
for task, n, seed in CELLS:
    rng = random.Random(seed); full = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    p, tried, dt = one(task, full[:n])
    g = general(p, task, seed) if p else None
    wrong = g is not None and any(v < 40 for v in g.values())
    row = {'task': task, 'seed': seed, 'n': n, 'found': p is not None,
           'tried': tried, 'dt': round(dt, 1), 'wrong': wrong, 'gen': g,
           'prog': __import__('cur7').show_prog(p) if p else None, 'note': 'b523e clean re-verification (B-523-H1)'}
    print(json.dumps(row, default=str), flush=True)
print('DONE', flush=True)
