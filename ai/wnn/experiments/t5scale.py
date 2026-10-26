"""B-237: HDC at 10x scale. facts: 350 pairs (700 queries, XOR binding). 2-hop: 500 chains (1500 links).
dims 8192/16384, random-proj, 3 seeds. Baseline: P5 T2 100% at 35 facts / 50 chains."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np
import t5hdc
from t5hdc import codebook, clean
def facts_n(C, n):
    M = np.zeros(C.shape[1], np.int32)
    for i in range(n): M += C[i] * C[n + i]
    M = np.sign(M)
    fwd = sum(np.array_equal(clean(M * C[i], C[n:]), C[n + i]) for i in range(n))
    rev = sum(np.array_equal(clean(M * C[n + i], C[:n]), C[i]) for i in range(n))
    return (fwd + rev) / (2 * n)
def twohop_n(C, chains):
    M = np.zeros(C.shape[1], np.int32)
    for c in range(chains):
        for j in range(3): M += np.roll(C[4 * c + j], 1) * C[4 * c + j + 1]
    M = np.sign(M); ok = 0
    for c in range(chains):
        v1 = clean(M * np.roll(C[4 * c], 1), C); v2 = clean(M * np.roll(v1, 1), C)
        ok += np.array_equal(v2, C[4 * c + 2])
    return ok / chains
for D in (8192, 16384):
    t5hdc.D = D
    f = [facts_n(codebook(700, 'random', np.random.default_rng(sd)), 350) for sd in range(3)]
    h = [twohop_n(codebook(2000, 'random', np.random.default_rng(sd)), 500) for sd in range(3)]
    print(f'dim {D}: facts-700q {sum(f)/3:.3f} | 2hop-500chains {sum(h)/3:.3f}', flush=True)
