"""T5 (B-209..): HDC dim=1024 bipolar vs P5 4KB config. Encodings: level, thermometer, random-proj.
Tasks (P5 E5 protocol): arith chaining (x->x+1 stored 0..99, compute a+k by k recalls, ALL pairs a+k<=99),
facts (35 key->value facts, XOR binding, recall both directions = 70 queries), 2-hop (50 chains A->B->C->D,
directional binding, query start follow 2 hops). RAM: memory vector 1024 int8 = 1KB (128B packed) vs P5 4KB/16KB."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import numpy as np
D = 1024
def codebook(n, enc, rng):
    if enc == 'random': return rng.choice([-1, 1], (n, D)).astype(np.int8)
    if enc == 'thermo':
        C = -np.ones((n, D), np.int8)
        for k in range(n): C[k, :round((k + 1) / n * D)] = 1
        return C
    # level: two random endpoints; v_k interpolates by flipping a growing share of mismatch dims
    A = rng.choice([-1, 1], D).astype(np.int8); B = rng.choice([-1, 1], D).astype(np.int8)
    mism = np.where(A != B)[0]; rng.shuffle(mism); C = np.tile(A, (n, 1))
    for k in range(n): C[k, mism[:round(k / max(1, n - 1) * len(mism))]] = B[mism[:round(k / max(1, n - 1) * len(mism))]]
    return C
def clean(M, C): return C[np.argmax(C @ M)]
def arith(C):
    M = np.zeros(D, np.int32)
    for x in range(100): M += np.roll(C[x], 1) * C[x + 1]  # directional bind: perm(key)*value
    ok = tot = 0
    for a in range(100):
        for k in range(1, 100 - a):
            v = C[a].copy()
            for _ in range(k): v = clean(M.astype(np.int64) * np.roll(v, 1), C)
            ok += np.array_equal(v, C[a + k]); tot += 1
    return ok, tot
def facts(C, n=35):
    M = np.zeros(D, np.int32)
    for i in range(n): M += C[i] * C[n + i]
    M = np.sign(M)
    fwd = sum(np.array_equal(clean(M * C[i], C[n:]), C[n + i]) for i in range(n))
    rev = sum(np.array_equal(clean(M * C[n + i], C[:n]), C[i]) for i in range(n))
    return fwd + rev, 2 * n
def twohop(C, chains=50):
    # 50 disjoint chains of 4 symbols: indices 4c..4c+3; links A->B, B->C, C->D directional
    M = np.zeros(D, np.int32)
    for c in range(chains):
        for j in range(3): M += np.roll(C[4 * c + j], 1) * C[4 * c + j + 1]
    M = np.sign(M)
    ok = 0
    for c in range(chains):
        v1 = clean(M * np.roll(C[4 * c], 1), C); v2 = clean(M * np.roll(v1, 1), C)
        ok += np.array_equal(v2, C[4 * c + 2])
    return ok, chains
if __name__ == '__main__':
    for enc in ('level', 'thermo', 'random'):
        for task, fn, n in (('arith', arith, 101), ('facts', facts, 70), ('2-hop', twohop, 200)):
            accs = []
            for sd in range(5):
                C = codebook(n, enc, np.random.default_rng(sd))
                ok, tot = fn(C); accs.append(ok / tot)
            print(f'{enc:7s} {task:6s}: {sum(accs)/5:.3f} [{min(accs):.3f}-{max(accs):.3f}] (dim 1024, mem 1KB int8 / 128B packed)', flush=True)
