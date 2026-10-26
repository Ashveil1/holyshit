"""T5 dim-4096 encoding grid (B-218..226): level/thermo/random x arith/facts/2-hop at dim 4096.
arith: 475 sampled pairs (P5 count), 3 seeds. facts: 70 queries. 2-hop: 50 chains. P5 baseline: 100% at 4-16KB."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np, random
import t5hdc
from t5hdc import codebook, clean, facts, twohop
t5hdc.D = 4096
def arith_sampled(C, rng):
    D = C.shape[1]; M = np.zeros(D, np.int32)
    for x in range(100): M += np.roll(C[x], 1) * C[x + 1]
    M = np.sign(M); ok = 0
    pairs = [(a, k) for a in range(100) for k in range(1, 100 - a)]; rng.shuffle(pairs)
    for a, k in pairs[:475]:
        v = C[a].copy()
        for _ in range(k): v = clean(M * np.roll(v, 1), C)
        ok += np.array_equal(v, C[a + k])
    return ok / 475
for enc in ('level', 'thermo', 'random'):
    a, f, h = [], [], []
    for sd in range(3):
        rng = np.random.default_rng(sd)
        a.append(arith_sampled(codebook(101, enc, rng), random.Random(sd)))
        f.append(sum(x / y for x, y in [facts(codebook(70, enc, np.random.default_rng(sd)))]))
        h.append(sum(x / y for x, y in [twohop(codebook(200, enc, np.random.default_rng(sd)))]))
    print(f'dim4096 {enc:7s}: arith {sum(a)/3:.3f} | facts {sum(f)/3:.3f} | 2-hop {sum(h)/3:.3f}', flush=True)
