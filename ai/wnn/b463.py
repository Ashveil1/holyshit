"""B-463: 233-cell core connectome as a fixed reservoir + ridge readout vs raw-pixel ridge,
mnist-1shot. Pure numpy; all design choices pre-registered in LEDGER (2026-10-24)."""
import numpy as np, json, time

RSTEP, ALPHA, BETA, LAM, SEEDS = 15, 0.9, 0.5, 1e-3, range(5)
NC = 10

def load(path):
    X, Y = [], []
    for line in open(path):
        p = line.split()
        Y.append(int(p[0])); X.append(np.frombuffer(bytes.fromhex(p[1]), np.uint8))
    return (np.array(X) > 128).astype(np.float64), np.array(Y, int)

def load_conn(path='data/connectome_core.txt'):
    f = open(path); n, m = map(int, f.readline().split()); names = f.readline().split()
    idx = {w: i for i, w in enumerate(names)}
    W = np.zeros((n, n))
    for line in f:
        a, b, w, kind = line.split()
        i, j, w = int(a), int(b), float(w)  # edges stored as integer indices (fixed post-launch, pre-result)
        W[j, i] += w                      # chemical: pre i -> post j
        if kind.strip() == 'g': W[i, j] += w   # gap: undirected
    return W

def norm_spectral(W, iters=200):
    v = np.random.default_rng(0).normal(size=W.shape[0]); v /= np.linalg.norm(v)
    for _ in range(iters): v = W @ v; v /= np.linalg.norm(v)
    return W / float(np.linalg.norm(W @ v) / np.linalg.norm(v) + 1e-12)

def reservoir_states(X, Wn):
    n = Wn.shape[0]; npix = X.shape[1]    # capped files are 392 px (14x28), not raw 784 (LEDGER amendment)
    S = np.zeros((len(X), n))
    J = np.zeros((npix, n))
    for p in range(npix): J[p, p % n] = 1.0
    Jin_all = X @ J / (npix / n)          # n_img x 233
    for k in range(len(X)):
        x = np.zeros(n); inj = BETA * Jin_all[k]
        for _ in range(RSTEP): x = np.tanh(ALPHA * (Wn @ x) + inj)
        S[k] = x
    return S

def ridge_fit(Xs, Y):
    T = np.zeros((len(Y), NC)); T[np.arange(len(Y)), Y] = 1.0
    A = Xs.T @ Xs + LAM * np.eye(Xs.shape[1])
    return np.linalg.solve(A, Xs.T @ T)

def ridge_acc(Wr, Xe, Ye):
    return float((np.argmax(Xe @ Wr, 1) == Ye).mean())

if __name__ == '__main__':
    t0 = time.time()
    Xtr, Ytr = load('mnist_train.txt'); Xte, Yte = load('mnist_test.txt')
    print(f'train {len(Ytr)} test {len(Yte)}', flush=True)
    W = load_conn(); Wn = norm_spectral(W)
    print('computing reservoir states...', flush=True)
    Str = reservoir_states(Xtr, Wn); Ste = reservoir_states(Xte, Wn)
    print(f'states done wall_s={round(time.time()-t0)}', flush=True)
    Wr_raw_full_test = ridge_acc  # alias
    for sd in SEEDS:
        rng = np.random.default_rng(sd)
        pick = np.array([rng.choice(np.where(Ytr == c)[0]) for c in range(NC)])
        a_raw = ridge_acc(ridge_fit(Xtr[pick], Ytr[pick]), Xte, Yte)
        a_res = ridge_acc(ridge_fit(Str[pick], Ytr[pick]), Ste, Yte)
        print(json.dumps({'seed': sd, 'raw': round(a_raw, 3), 'reservoir': round(a_res, 3)}), flush=True)
    print(f'DONE wall_s={round(time.time()-t0)}', flush=True)
