"""B-523 spot-checks (no-regression) - b523b continuation. isprime cells SKIPPED (recorded):
B-299-CURR already established isprime exhausts >6M (seed-dependent); expected b523b isprime result
was not-found-exhaustion (wrong=0 via not-found) - re-confirming on a 5x-slower sandbox is 4-8h of
compute for a known result. Spot-checks: mod/div/fact/sumto n=25, gcd n=3 - all were clean pre-patch,
must stay clean with boundary() entries active."""
import random, json
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
CELLS = [('mod', 25, 0), ('div', 25, 0), ('fact', 25, 0), ('sumto', 25, 0), ('gcd', 3, 1)]
ABL = 'baselib,simp,adv'
def one(task, train, cap=6_000_000):
    cur7.VALID[:] = []; ADV[:] = boundary(task); EXCL.clear(); EXCL.add(task); CAPF[0] = 400
    return search(train, ABL, tried_cap=cap)
def general(p, task, seed):
    if p is None: return None
    f = make_fn(p)
    rng = random.Random(9000 + seed); bad = 0
    for _ in range(40):
        try:
            x, y, r = gen(task, rng, rng.choice([1, 2]))
            CAPF[0] = 500000
            if f(x, y) != r: bad += 1
        except (Fail, KeyError, ZeroDivisionError, RecursionError, OverflowError): bad += 1
        finally: CAPF[0] = 400
    return bad
out = open('logs/b523c_run.log', 'a')
for task, n, seed in CELLS:
    rng = random.Random(seed); full = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    p, tried, dt = one(task, full[:n])
    g = general(p, task, seed) if p else None
    row = {'task': task, 'seed': seed, 'n': n, 'found': p is not None, 'tried': tried,
           'dt': round(dt, 1), 'wrong': bool(g), 'bad40': g}
    print(json.dumps(row), file=out, flush=True)
    print(row, flush=True)
print('DONE', len(CELLS), flush=True)
