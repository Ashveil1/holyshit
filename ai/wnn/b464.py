"""B-464: static degree/spectral wiring features as image embeddings, ridge readout vs raw.
Pre-registered LEDGER 2026-10-24. Reuses b463 data conventions (392px capped files)."""
import numpy as np, json, time
from b463 import load, load_conn, ridge_fit, ridge_acc, NC

def structural(W):
    n = W.shape[0]
    chem = (W > 0).astype(float); gap = ((W > 0) & (W.T > 0)).astype(float)
    feats = [chem.sum(0), chem.sum(1), gap.sum(0), W.sum(0), W.sum(1)]
    F = np.stack(feats, 1); F = (F - F.mean(0)) / (F.std(0) + 1e-9)
    sym = W + W.T; sym = sym / (np.linalg.norm(sym, 2) + 1e-12)
    U, Sv, Vt = np.linalg.svd(sym)
    return np.concatenate([F, Vt[:8].T], 1)          # 233 x 13

if __name__ == '__main__':
    t0 = time.time()
    Xtr, Ytr = load('mnist_train.txt'); Xte, Yte = load('mnist_test.txt')
    W = load_conn(); n = W.shape[0]; npix = Xtr.shape[1]
    S = structural(W)
    J = np.zeros((npix, n))
    for p in range(npix): J[p, p % n] = 1.0
    Etr = (Xtr @ J / (npix / n)) @ S; Ete = (Xte @ J / (npix / n)) @ S
    # (b) full-pool row
    b_raw = ridge_acc(ridge_fit(Xtr, Ytr), Xte, Yte)
    b_emb = ridge_acc(ridge_fit(Etr, Ytr), Ete, Yte)
    print(json.dumps({'fullpool': {'raw': round(b_raw, 3), 'emb': round(b_emb, 3)}}), flush=True)
    # (a) 1-shot 5 seeds
    for sd in range(5):
        rng = np.random.default_rng(sd)
        pick = np.array([rng.choice(np.where(Ytr == c)[0]) for c in range(NC)])
        a_raw = ridge_acc(ridge_fit(Xtr[pick], Ytr[pick]), Xte, Yte)
        a_emb = ridge_acc(ridge_fit(Etr[pick], Ytr[pick]), Ete, Yte)
        print(json.dumps({'seed': sd, 'raw': round(a_raw, 3), 'emb': round(a_emb, 3)}), flush=True)
    print(f'DONE wall_s={round(time.time()-t0)}', flush=True)
