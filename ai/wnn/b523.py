"""B-523: CURR boundary coverage. Re-probe previously-wrong cells with boundary() entries active,
plus no-regression spot-checks on already-clean cells. Recipe baselib,simp,adv full inits, cap 6M."""
import random, json
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
CELLS = (
    [('mul', n, s) for s in (0, 1) for n in (3, 5, 10, 25)] +
    [('div', n, s) for s in (0, 1) for n in (3, 5, 10)] +
    [('power', n, s) for s in (0, 1) for n in (3, 5, 10)] +
    [('isprime', 3, 0), ('isprime', 10, 0)] +
    [('mod', 25, 0), ('div', 25, 0), ('fact', 25, 0), ('sumto', 25, 0), ('gcd', 3, 1)]  # spot-checks
)
ABL = 'baselib,simp,adv'
def one(task, train, cap=6_000_000):
    cur7.VALID[:] = []; ADV[:] = boundary(task); EXCL.clear(); EXCL.add(task); CAPF[0] = 400
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
out = []
for task, n, seed in CELLS:
    rng = random.Random(seed); full = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    p, tried, dt = one(task, full[:n])
    g = general(p, task, seed) if p else None
    wrong = g is not None and any(v < 40 for v in g.values())
    row = {'task': task, 'seed': seed, 'n': n, 'found': p is not None,
           'tried': tried, 'dt': round(dt, 1), 'wrong': wrong, 'gen': g}
    out.append(row)
    print(json.dumps(row, default=str), flush=True)
json.dump(out, open('logs/b523.json', 'w'), indent=1, default=str)
print('DONE', len(out), flush=True)
