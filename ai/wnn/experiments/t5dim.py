"""T5 follow-up: random-proj at dim 2048/4096 - where does chaining capacity recover?
arith: 475 sampled (a,k) pairs (P5's test count) per seed, 3 seeds. 2-hop: 50 chains."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np, random
from t5hdc import codebook, clean, facts, twohop
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
for D in (2048, 4096):
    import t5hdc; t5hdc.D = D
    a_acc, h_acc = [], []
    for sd in range(3):
        rng = random.Random(sd)
        a_acc.append(arith_sampled(codebook(101, 'random', np.random.default_rng(sd)), rng))
        h_acc.append(sum(x / y for x, y in [twohop(codebook(200, 'random', np.random.default_rng(sd)))]) )
    print(f'dim {D}: arith(475 pairs) {sum(a_acc)/3:.3f} | 2-hop {sum(h_acc)/3:.3f}', flush=True)
