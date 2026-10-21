"""B-255..260: HDC chain depth 10 at link counts 70/300/1000, dim 16384, random-proj, 3 seeds.
Same protocol as t5chain5 but k=10 hops. Depth-5 reference: 70: 1/1, 300: .990/.989, 1000: .038/.031."""
import numpy as np, random
import t5hdc
from t5hdc import codebook, clean
t5hdc.D = 16384
def chain(nl, sd, K, N):
    C = codebook(nl + K + 1, 'random', np.random.default_rng(sd))
    M = np.zeros(16384, np.int32)
    for x in range(nl): M += np.roll(C[x], 1) * C[x + 1]
    M = np.sign(M); rng = random.Random(sd); ok = 0
    for _ in range(N):
        a = rng.randrange(nl - K); v = C[a].copy()
        for _ in range(K): v = clean(M * np.roll(v, 1), C)
        ok += np.array_equal(v, C[a + K])
    return ok / N
for nl in (70, 300, 1000):
    l = [chain(nl, sd, 10, 150) for sd in range(3)]
    print(f'links {nl:4d} depth10: logic=arith {sum(l)/3:.3f} (same computation)', flush=True)
