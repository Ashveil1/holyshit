"""B-300R (re-scoped T10): does INFORMED selection replace test-time adversarial acceptance?
Cliff model: wrong rate >0 exactly where shortcuts survive. Selection matters iff it kills shortcuts.
Conditions: R5 (random 5), B5 (boundary entries as train - oracle informed selection), R25 (random 25).
NO adv (acceptance off) - selection must do the work. Recipe baselib,simp, cap 3M. Eval: general vs gen."""
import random, json, sys
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
CAPF[0] = 400
def general(p, task, seed):
    if p is None: return None
    f = make_fn(p)
    rng = random.Random(9000 + seed); bad = 0
    for _ in range(40):
        sc = rng.choice([1, 2])
        try:
            x, y, r = gen(task, rng, rng.choice([1, 2]))
            CAPF[0] = 20000
            if f(x, y) != r: bad += 1
        except (Fail, KeyError, ZeroDivisionError, RecursionError, OverflowError): bad += 1
        finally: CAPF[0] = 400
    return bad
def one(task, train, cap=3_000_000):
    ADV[:] = []; EXCL.clear()   # NO adv, NO exclusion: selection does the work
    p, tried, dt = search(train, 'baselib,simp', tried_cap=cap)
    return p, tried, dt
CELLS = []
for task in ('mod', 'even', 'div', 'square'):
    for s in (0, 1, 2):
        CELLS.append((task, 'R5', s)); CELLS.append((task, 'R25', s))
    CELLS.append((task, 'B5', 0))
out = open('logs/b300r_run.log', 'a')
for task, cond, seed in CELLS:
    rng = random.Random(seed)
    full = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    if cond == 'R5': train = full[:5]
    elif cond == 'R25': train = full
    else: train = boundary(task)[:5]
    p, tried, dt = one(task, train)
    g = general(p, task, seed) if p else None
    row = {'task': task, 'cond': cond, 'seed': seed, 'found': p is not None, 'tried': tried,
           'dt': round(dt, 1), 'wrong40': g}
    print(json.dumps(row), file=out, flush=True)
    print(row, flush=True)
print('DONE', len(CELLS), flush=True)
