"""B-249..254: HDC chain depth 5 at link counts 70/300/1000, dim 16384, random-proj, 3 seeds.
logic: follow 5 hops from chain start, check 5th node (sample 200 starts). arith: exactly 5 +1-recalls (150 queries).
Depth-2 reference (t5chain): 70: 1.0/1.0, 300: .996/.945, 1000: .284/.038."""
import numpy as np, random
import t5hdc
from t5hdc import codebook, clean
t5hdc.D = 16384
def logic5(nl, sd):
    C = codebook(nl + 6, 'random', np.random.default_rng(sd))
    M = np.zeros(16384, np.int32)
    for x in range(nl): M += np.roll(C[x], 1) * C[x + 1]
    M = np.sign(M); rng = random.Random(sd); ok = 0; N = 200
    for _ in range(N):
        a = rng.randrange(nl - 5); v = C[a].copy()
        for _ in range(5): v = clean(M * np.roll(v, 1), C)
        ok += np.array_equal(v, C[a + 5])
    return ok / N
def arith5(nl, sd):
    C = codebook(nl + 6, 'random', np.random.default_rng(sd))
    M = np.zeros(16384, np.int32)
    for x in range(nl): M += np.roll(C[x], 1) * C[x + 1]
    M = np.sign(M); rng = random.Random(sd); ok = 0; N = 150
    for _ in range(N):
        a = rng.randrange(nl - 5); v = C[a].copy()
        for _ in range(5): v = clean(M * np.roll(v, 1), C)
        ok += np.array_equal(v, C[a + 5])
    return ok / N
for nl in (70, 300, 1000):
    l = [logic5(nl, sd) for sd in range(3)]; a = [arith5(nl, sd) for sd in range(3)]
    print(f'links {nl:4d} depth5: logic {sum(l)/3:.3f} | arith {sum(a)/3:.3f}', flush=True)
