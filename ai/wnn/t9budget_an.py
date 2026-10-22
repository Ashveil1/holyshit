"""B-299 analysis: tried(n) flatness per skill; even re-eval at CAPF 500000 (B-265 artifact)."""
import json, random, sys
import cur7
from cur7 import gen, search, make_fn, boundary, ADV, EXCL, CAPF, Fail, ev
rows = json.load(open('logs/t9budget2.json'))
by = {}
for r in rows:
    by.setdefault(r['task'], []).append(r)
for t, rr in by.items():
    trieds = sorted(set(r['tried'] for r in rr))
    wrongs = sum(r['wrong'] for r in rr)
    print(f"{t}: tried set {trieds} | wrong flags {wrongs}/{len(rr)} | found {sum(r['found'] for r in rr)}/{len(rr)}")
# even re-eval at high CAPF: re-find per seed (fast, ~10s), eval scale 4 at CAPF 500000
ABL = 'init10,baselib,simp,adv'
for seed in range(2):
    rng = random.Random(seed); train = [gen('even', rng, rng.choice([1, 2])) for _ in range(25)]
    cur7.VALID[:] = []; ADV[:] = boundary('even'); EXCL.clear(); EXCL.add('even'); CAPF[0] = 400
    p, tried, dt = search(train, ABL, tried_cap=6_000_000)
    f = make_fn(p); te = random.Random(1000 + seed); CAPF[0] = 500000
    ok4 = 0
    for _ in range(40):
        x, y, r = gen('even', te, 4)
        try: ok4 += int(f(x, y) == r)
        except (Fail, KeyError, RecursionError, OverflowError): pass
    CAPF[0] = 400; ev.cache_clear()
    print(f"even seed{seed}: tried {tried} scale4 at CAPF500000 = {ok4}/40")
