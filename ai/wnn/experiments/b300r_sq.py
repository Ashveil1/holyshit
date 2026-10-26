"""B-300R-SQ: square B5 CORRECTED - train-safe boundary cases (cap-cost rule B-523rev: canonical
square = repeated-addition mul, cost O(product) at x=30 -> 900 steps > search CAP 400 -> NOT FOUND
artifact). Train = [(0,0),(1,1),(2,4),(3,9),(5,25)] - same info, cap-respecting."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, json
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
CAPF[0] = 400
train = [(0, 7, 0), (1, 7, 1), (2, 7, 4), (3, 7, 9), (5, 7, 25)]
ADV[:] = []; EXCL.clear()
p, tried, dt = search(train, 'baselib,simp', tried_cap=3_000_000)
g = None
if p:
    f = make_fn(p); rng = random.Random(9000); bad = 0
    for _ in range(40):
        try:
            x, y, r = gen('square', rng, rng.choice([1, 2]))
            CAPF[0] = 500000
            if f(x, y) != r: bad += 1
        except (Fail, KeyError, ZeroDivisionError, RecursionError, OverflowError): bad += 1
        finally: CAPF[0] = 400
    g = bad
row = {'task': 'square', 'cond': 'B5t', 'found': p is not None, 'tried': tried, 'dt': round(dt, 1), 'wrong40': g}
print(json.dumps(row), file=open('logs/b300r_run.log', 'a'), flush=True)
print(row, flush=True)
