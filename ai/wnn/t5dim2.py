import numpy as np, random
import t5hdc
from t5hdc import codebook, clean
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
for D in (8192, 16384):
    t5hdc.D = D
    accs = []
    for sd in range(2):
        accs.append(arith_sampled(codebook(101, 'random', np.random.default_rng(sd)), random.Random(sd)))
    print(f'dim {D}: arith(475 pairs) {sum(accs)/len(accs):.3f}', flush=True)
