"""B-299: adaptive search budget as function of example count.
For CURR skills mod..sumto: measure tried-to-first-accepted and wrong-program rate
at train sizes n in {3,5,10,25}, seeds 0-1, recipe init10,baselib,simp,adv, cap 6M
(cap never binds for measurement; exhaustion recorded as NOT FOUND).
Adaptive rule cap(n) is then fit from the tried(n) curve; CPU saving vs fixed cap."""
import random, json, sys
import cur7
from cur7 import gen, search, make_fn, boundary, LIB, ADV, EXCL, CAPF, Fail, ev
TASKS = ['gcd', 'isprime', 'fact', 'sumto']
NS = [3, 5, 10, 25]
ABL = 'baselib,simp,adv'  # full inits: init10 drops init=y (B-522)
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
for task in TASKS:
    for seed in range(2):
        if task == 'gcd' and seed == 0: continue  # seed0 n=3 exhausted 6M; nested prefixes => NOT FOUND all n (LEDGER)
        rng = random.Random(seed); full = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
        for n in (NS if task != 'gcd' else [3]):
            train = full[:n]
            p, tried, dt = one(task, train)
            g = general(p, task, seed) if p else None
            wrong = g is not None and any(v < 40 for v in g.values())
            row = {'task': task, 'seed': seed, 'n': n, 'found': p is not None,
                   'tried': tried, 'dt': round(dt, 1), 'wrong': wrong, 'gen': g}
            out.append(row)
            print(json.dumps(row, default=str), flush=True)
json.dump(out, open('logs/t9budget_curr2.json', 'w'), indent=1, default=str)
print('DONE', len(out), flush=True)
