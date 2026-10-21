"""B-238: recall PROGRAM (op) by task description - HD classifier over P15 sentences.
Encode sentence = bundle of random codes of its tok features (unigrams+bigrams); class vector =
bundle of all training sentences for that op; query = nearest class vector (cosine).
12 ops, train n=150 sentences (P15 protocol seed split), eval unseen frames (which=1).
Baseline: random recall 1/12 = 8.3%. Success: >90% top-1. dims 1024/4096/16384, 3 seeds."""
import numpy as np, random
from text2prog import gen_set, feats, T
OPS = list(T); N = len(OPS)
def codes_for(featset, table, rng):
    out = []
    for f in featset:
        if f not in table: table[f] = rng.choice([-1, 1], D).astype(np.int8)
        out.append(table[f])
    return out
def run(D, n, sd):
    table = {}; rng = np.random.default_rng(sd * 7 + 1)
    rr = random.Random(sd)
    train = gen_set(rr, 0, n); cls = np.zeros((N, D), np.int64); cnt = np.zeros(N)
    for op, text, ans in train:
        cs = codes_for(feats(text, 'tok'), table, rng)
        if cs: cls[OPS.index(op)] += np.sign(np.sum(cs, 0)); cnt[OPS.index(op)] += 1
    te = random.Random(100 + sd); ok = 0; tot = 0
    for op, text, ans in gen_set(te, 1, 300, big=True):
        cs = codes_for(feats(text, 'tok'), table, rng)
        if not cs: continue
        v = np.sign(np.sum(cs, 0)); ok += OPS[int(np.argmax(cls @ v))] == op; tot += 1
    return ok / tot
if __name__ == '__main__':
    for D in (1024, 4096, 16384):
        for n in (60, 150):
            a = [run(D, n, sd) for sd in range(3)]
            print(f'dim {D:5d} n={n:3d}: op recall top-1 {sum(a)/3:.3f} [{min(a):.3f}-{max(a):.3f}] (chance {1/N:.3f})', flush=True)
