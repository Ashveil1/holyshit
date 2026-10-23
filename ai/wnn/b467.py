"""B-467/470/473/476/479/482/485/488/491: few-shot continual pmnist (5 tasks, k shots/class/task) - 1nn/centroid/WiSARD shared+pertask arms vs naive MLP. LEDGER B-467P."""
import numpy as np, json
def load(path):
    f = open(path); n, npix = map(int, f.readline().split())
    Y = np.zeros(n, int); X = np.zeros((n, npix), np.uint8)
    for i, line in enumerate(f):
        p = line.split(); Y[i] = int(p[0]); X[i] = np.frombuffer(bytes.fromhex(p[1]), np.uint8)
    return (X > 128).astype(np.uint8), Y
Xtr, Ytr = load('mnist_train_raw.txt'); Xte, Yte = load('mnist_test_raw.txt')
NT = 5
def l2arg(Xq, Xs):
    d = (Xq ** 2).sum(1)[:, None] + (Xs ** 2).sum(1)[None, :] - 2 * Xq @ Xs.T
    return d.argmin(1)
def run_k(k, sd):
    rng = np.random.default_rng(sd); TUP = rng.permutation(784).reshape(28, 28)
    PERMS = [np.arange(784)] + [np.random.default_rng(1000 + sd * 10 + t).permutation(784) for t in range(1, NT)]
    POW = (1 << np.arange(28, dtype=np.int64))
    def tuples(X):
        return np.stack([X[:, TUP[j]].dot(POW) for j in range(28)], 1)
    TTEk = [tuples(Xte[:, p]) for p in PERMS]
    XTEk = [Xte[:, p].astype(np.float64) for p in PERMS]
    # per-task k-shot samples
    rs = np.random.default_rng(500 + sd)
    SAMP = []
    for t in range(NT):
        idx = np.concatenate([rs.choice(np.where(Ytr == c)[0], k, replace=False) for c in range(10)])
        SAMP.append(idx)
    # arms
    sup_X, sup_Y = [], []                       # 1nn shared (raw permuted vectors)
    sup_pt = [([], []) for _ in range(NT)]      # 1nn per-task
    sum_c = np.zeros((10, 784)); cnt_c = np.zeros(10)   # centroid shared (running)
    cent_pt = [None] * NT                       # centroid per-task
    wis_sh = {c: [set() for _ in range(28)] for c in range(10)}
    wis_pt = [{c: [set() for _ in range(28)] for c in range(10)} for _ in range(NT)]
    r2 = np.random.default_rng(100 + sd)
    W1 = r2.normal(0, .1, (784, 64)); b1 = np.zeros(64); W2 = r2.normal(0, .1, (64, 10)); b2 = np.zeros(10)
    MU, SD = Xtr.mean(0), Xtr.std(0) + 1e-9
    def fit(X, Y, eps):
        nonlocal W1, b1, W2, b2
        Xs = (X - MU) / SD; T = np.eye(10)[Y]
        for ep in range(eps):
            a1 = np.tanh(Xs @ W1 + b1); z = a1 @ W2 + b2
            p = np.exp(z - z.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
            d = (p - T) / len(Xs)
            dW2 = a1.T @ d; db2 = d.sum(0); d1 = (d @ W2.T) * (1 - a1 ** 2)
            W1 -= .5 * (Xs.T @ d1); b1 -= .5 * d1.sum(0); W2 -= .5 * dW2; b2 -= .5 * db2
    def pred_mlp(X): return np.argmax(np.tanh(((X - MU) / SD) @ W1 + b1) @ W2 + b2, 1)
    def acc_w(nodes, T, Y):
        S = np.zeros((len(T), 10))
        for c in range(10):
            for j in range(28):
                s = nodes[c][j]
                if s: S[:, c] += np.array([v in s for v in T[:, j]])
        return (S.argmax(1) == Y).mean()
    for t in range(NT):
        idx = SAMP[t]; Xs_t = Xtr[idx][:, PERMS[t]].astype(np.float64); Ys_t = Ytr[idx]
        Tt = tuples(Xtr[idx][:, PERMS[t]])
        sup_X.append(Xs_t); sup_Y.append(Ys_t)
        sup_pt[t] = (Xs_t, Ys_t)
        for c in range(10):
            sel = Ys_t == c
            sum_c[c] += Xs_t[sel].sum(0); cnt_c[c] += sel.sum()
            v = np.unique(Tt[sel], axis=0)
            for j in range(28):
                u = np.unique(Tt[sel, j]).tolist()
                wis_sh[c][j] |= set(u); wis_pt[t][c][j] |= set(u)
        cent_pt[t] = np.stack([Xs_t[Ys_t == c].mean(0) for c in range(10)])
        fit(Xs_t, Ys_t, 300)
    # final eval on all tasks
    out = {'k': k, 'seed': sd}
    SX = np.concatenate(sup_X); SY = np.concatenate(sup_Y)
    Csh = sum_c / np.maximum(cnt_c, 1)[:, None]
    means = {}
    for name in ('1nn_sh', '1nn_pt', 'cent_sh', 'cent_pt', 'wis_sh', 'wis_pt', 'mlp'):
        accs = []
        for t in range(NT):
            if name == '1nn_sh': a = (SY[l2arg(XTEk[t], SX)] == Yte).mean()
            elif name == '1nn_pt': a = (sup_pt[t][1][l2arg(XTEk[t], sup_pt[t][0])] == Yte).mean()
            elif name == 'cent_sh': a = (l2arg(XTEk[t], Csh) == Yte).mean()
            elif name == 'cent_pt': a = (l2arg(XTEk[t], cent_pt[t]) == Yte).mean()
            elif name == 'wis_sh': a = acc_w(wis_sh, TTEk[t], Yte)
            elif name == 'wis_pt': a = acc_w(wis_pt[t], TTEk[t], Yte)
            else: a = (pred_mlp(XTEk[t]) == Yte).mean()
            accs.append(round(float(a), 4))
        out[name] = accs; means[name] = round(float(np.mean(accs)), 4)
    out['means'] = means
    return out
for k in (1, 5, 20):
    for sd in range(2):
        print(json.dumps(run_k(k, sd)), flush=True)
print('DONE', flush=True)
