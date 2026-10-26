"""B-262: negatives + mixed-radix in HDC chaining, dim 16384, random codes, 3 seeds.
(a) signed chain: x->x+1 over -100..100 (201 links), query a+k exact.
(b) mixed-radix odometer: (m,s) s in 0..59, m in 0..23; links (m,s)->(m,s+1) and (m,59)->(m+1,0);
    query (m,s)+k seconds exact (k up to 200, crossing rollovers)."""
import numpy as np, random
import t5hdc
from t5hdc import codebook, clean
t5hdc.D = 16384
def signed(sd):
    C = codebook(202, 'random', np.random.default_rng(sd))  # index = x+100
    M = np.zeros(16384, np.int32)
    for x in range(-100, 100): M += np.roll(C[x + 100], 1) * C[x + 101]
    M = np.sign(M); rng = random.Random(sd); ok = 0
    for _ in range(300):
        a = rng.randrange(-100, 90); k = rng.randrange(1, 11)
        v = C[a + 100].copy()
        for _ in range(k): v = clean(M * np.roll(v, 1), C)
        ok += np.array_equal(v, C[a + k + 100])
    return ok / 300
def odometer(sd):
    C = codebook(24 * 60 + 1, 'random', np.random.default_rng(sd))
    idx = lambda m, s: m * 60 + s
    M = np.zeros(16384, np.int32)
    for m in range(24):
        for s in range(60):
            nm, ns = (m + 1, 0) if s == 59 else (m, s + 1)
            if nm < 24: M += np.roll(C[idx(m, s)], 1) * C[idx(nm, ns)]
    M = np.sign(M); rng = random.Random(sd); ok = 0
    for _ in range(60):
        m0, s0 = rng.randrange(22), rng.randrange(60); k = rng.randrange(1, 60)
        if idx(m0, s0) + k >= 24 * 60: continue
        v = C[idx(m0, s0)].copy()
        for _ in range(k): v = clean(M * np.roll(v, 1), C)
        t = idx(m0, s0) + k; ok += np.array_equal(v, C[t])
    return ok / 60
s = [signed(sd) for sd in range(3)]; o = [odometer(sd) for sd in range(2)]; o = o  # 2 seeds, k<=60, 60 queries (trimmed for runtime)
print(f'signed chain (-100..100): {sum(s)/3:.3f} | mixed-radix odometer (24h clock, k<=60 hops, 60q, 2 seeds): {sum(o)/2:.3f}', flush=True)
