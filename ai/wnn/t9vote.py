"""T9 (B-263..265): vote k=3 over random 50% train subsets vs single run.
Per seed+task: 3 votes (random 50% subsets of the 25 train rows, recipe init10,baselib,simp,adv,
cap1m), majority program wins (else best train fit); single = one search on all 25, same recipe/cap.
Metrics: found rate, tried, wrong-program rate (found but fails some unseen scale 1-4, 40/scale)."""
import random, json, sys
import cur7
from cur7 import gen, search, make_fn, boundary, LIB, ADV, EXCL, CAPF, Fail, ev
TASKS = sys.argv[1].split(',') if len(sys.argv) > 1 else ['square', 'even', 'sumto']
ABL = 'init10,baselib,simp,adv'
CAPS = {'square': 3_000_000, 'choose2': 3_000_000, 'sumsq': 3_000_000}
def _cap(task): return CAPS.get(task, 1_000_000)
CAPS = {t: _cap(t) for t in ('square','even','sumto','choose2','sumsq')}
def one(task, train, cap):
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
out = {}
for task in TASKS:
    rows = []
    for seed in range(2):
        rng = random.Random(seed); train = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
        # votes
        progs = []
        for v in range(3):
            sr = random.Random(100 + seed * 10 + v); sub = [r for r in train if sr.random() < 0.5]
            if len(sub) < 3: sub = train[:6]
            p, tried, dt = one(task, sub, CAPS[task])
            progs.append((p, tried))
        found = [p for p, _ in progs if p]
        maj = None
        for p in found:
            if sum(q == p for q in found) >= 2: maj = p; break
        if maj is None and found:
            maj = max(found, key=lambda p: sum(make_fn(p)(x, y) == r for x, y, r in train if True) if p else 0)
        vg = general(maj, task, seed) if maj else None
        # single
        p1, t1, _ = one(task, train, CAPS[task])
        sg = general(p1, task, seed) if p1 else None
        def wrong(g): return g is not None and any(v < 40 for v in g.values())
        rows.append({'seed': seed, 'vote_found': maj is not None, 'vote_wrong': wrong(vg), 'vote_tried': sum(t for _, t in progs),
                     'single_found': p1 is not None, 'single_wrong': wrong(sg), 'single_tried': t1, 'vote_gen': vg, 'single_gen': sg})
        print(task, seed, json.dumps(rows[-1]), flush=True)
    out[task] = rows
json.dump(out, open('logs/t9vote.json', 'w'), indent=1, default=str)
print('SUMMARY', json.dumps({t: {'vote_found': sum(r['vote_found'] for r in rr), 'vote_wrong': sum(r['vote_wrong'] for r in rr),
      'single_found': sum(r['single_found'] for r in rr), 'single_wrong': sum(r['single_wrong'] for r in rr)} for t, rr in out.items()}), flush=True)
