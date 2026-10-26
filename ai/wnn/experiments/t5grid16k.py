"""T5 dim-16384 encoding grid (B-227..235): level/thermo/random x arith/facts/2-hop at dim 16384 (= P5's 16KB).
arith: 475 sampled pairs, 2 seeds. random arith already 1.000 (t5dim2) - replicated here for the record."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np, random
import t5hdc
from t5hdc import codebook, clean, facts, twohop
t5hdc.D = 16384
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
    for sd in range(2):
        a.append(arith_sampled(codebook(101, enc, np.random.default_rng(sd)), random.Random(sd)))
        f.append(sum(x / y for x, y in [facts(codebook(70, enc, np.random.default_rng(sd)))]))
        h.append(sum(x / y for x, y in [twohop(codebook(200, enc, np.random.default_rng(sd)))]))
    print(f'dim16384 {enc:7s}: arith {sum(a)/2:.3f} | facts {sum(f)/2:.3f} | 2-hop {sum(h)/2:.3f}', flush=True)
