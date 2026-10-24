"""B-486/489/492: snips few-shot wiSARD readout rows (k=1/5/20), added to b468's exact
protocol; nn/centroid/mlp re-measured as paired sanity rows. LEDGER pre-reg 2026-10-24."""
import numpy as np, json
from b468 import Xtr, Xte, Ytr, Yte, NC, nn_acc, cent_acc, OVR, B

POW32 = (1 << np.arange(32, dtype=np.int64))
def wis_fit(Xs, Ys, perm):
    T = np.stack([Xs[:, perm[j]].dot(POW32) for j in range(128)], 1)
    return {c: [set(np.unique(T[Ys == c, j]).tolist()) for j in range(128)] for c in range(NC)}
def wis_acc(nodes, X, Y, perm):
    T = np.stack([X[:, perm[j]].dot(POW32) for j in range(128)], 1)
    S = np.zeros((len(X), NC))
    for c in range(NC):
        for j in range(128):
            s = nodes[c][j]
            if s: S[:, c] += np.array([v in s for v in T[:, j]])
    return (S.argmax(1) == Y).mean()

if __name__ == '__main__':
    for k in (1, 5, 20):
        r_nn, r_ct, r_mlp, r_wis = [], [], [], []
        for seed in range(10):
            r = np.random.default_rng(100 + seed)
            idx = np.concatenate([r.choice(np.where(Ytr == c)[0], k, replace=False) for c in range(NC)])
            Xs, Ys = Xtr[idx], Ytr[idx]
            perm = np.random.default_rng(400 + seed).permutation(B).reshape(128, 32)
            r_nn.append(nn_acc(Xs, Ys)); r_ct.append(cent_acc(Xs, Ys))
            m = OVR(); m.fit(Xs, Ys); r_mlp.append(m.acc(Xte, Yte))
            r_wis.append(wis_acc(wis_fit(Xs, Ys, perm), Xte, Yte, perm))
        print(json.dumps({'k': k, 'nn': round(float(np.mean(r_nn)), 4), 'centroid': round(float(np.mean(r_ct)), 4),
                          'mlp': round(float(np.mean(r_mlp)), 4), 'wisard': round(float(np.mean(r_wis)), 4),
                          'wisard_seeds': [round(float(x), 3) for x in r_wis]}), flush=True)
    print('DONE', flush=True)
