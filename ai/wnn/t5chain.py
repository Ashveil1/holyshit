"""B-243..248: HDC chain depth 2 at link counts 70/300/1000, dim 16384, random-proj, 3 seeds.
logic = transitive chains (A->B->C, 2-hop query); arith = x->x+1 chaining with N links (475 sampled queries).
Baseline: P5 100% at 100 links / 50 chains. Success: exact at larger scale or honest limit."""
import numpy as np, random
import t5hdc
from t5hdc import codebook, clean
t5hdc.D = 16384
def logic_nlinks(nl, sd):
    C = codebook(nl + 3, 'random', np.random.default_rng(sd))
    M = np.zeros(16384, np.int32)
    for x in range(nl): M += np.roll(C[x], 1) * C[x + 1]
    M = np.sign(M); ok = tot = 0
    for a in range(0, nl - 1, max(1, nl // 300)):  # sample ~300 chain starts
        v1 = clean(M * np.roll(C[a], 1), C); v2 = clean(M * np.roll(v1, 1), C)
        ok += np.array_equal(v2, C[a + 2]); tot += 1
    return ok / tot
def arith_nlinks(nl, sd):
    C = codebook(nl + 1, 'random', np.random.default_rng(sd))
    M = np.zeros(16384, np.int32)
    for x in range(nl): M += np.roll(C[x], 1) * C[x + 1]
    M = np.sign(M); rng = random.Random(sd); ok = 0
    for _ in range(475):
        a = rng.randrange(nl); k = rng.randrange(1, min(50, nl - a) + 1)
        v = C[a].copy()
        for _ in range(k): v = clean(M * np.roll(v, 1), C)
        ok += np.array_equal(v, C[a + k])
    return ok / 475
for nl in (70, 300, 1000):
    l = [logic_nlinks(nl, sd) for sd in range(3)]; a = [arith_nlinks(nl, sd) for sd in range(3)]
    print(f'links {nl:4d}: logic-2hop {sum(l)/3:.3f} | arith-chain {sum(a)/3:.3f}', flush=True)
