"""B-466/469/472/475/478/481: MNIST few-shot readout grid slice: 1nn + centroid vs B-241 OVR MLP, k=1/5/20, 5 seeds. LEDGER B-466P."""
import numpy as np, json
def load(path):
    f = open(path); n, npix = map(int, f.readline().split())
    Y = np.zeros(n, int); X = np.zeros((n, npix), np.uint8)
    for i, line in enumerate(f):
        p = line.split(); Y[i] = int(p[0]); X[i] = np.frombuffer(bytes.fromhex(p[1]), np.uint8)
    return (X > 128).astype(np.float64), Y
Xtr, Ytr = load('mnist_train_raw.txt'); Xte, Yte = load('mnist_test_raw.txt')
NC = 10

def nn_acc(Xs, Ys):
    d = (Xte ** 2).sum(1)[:, None] + (Xs ** 2).sum(1)[None, :] - 2 * Xte @ Xs.T
    return (Ys[d.argmin(1)] == Yte).mean()

def cent_acc(Xs, Ys):
    C = np.stack([Xs[Ys == c].mean(0) for c in range(NC)])
    d = (Xte ** 2).sum(1)[:, None] + (C ** 2).sum(1)[None, :] - 2 * Xte @ C.T
    return (d.argmin(1) == Yte).mean()

class OVR:
    def fit(s, X, Y):
        mu, sd = X.mean(0), X.std(0) + 1e-9; s.mu, s.sd = mu, sd; Xs = (X - mu) / sd
        s.W = []
        for c in range(NC):
            t = ((Y == c).astype(float) * 2 - 1).reshape(-1, 1)
            rng = np.random.default_rng(c); W1 = rng.normal(0, .5, (784, 32)); b1 = np.zeros(32); W2 = rng.normal(0, .5, (32, 1)); b2 = np.zeros(1)
            for ep in range(800):
                a1 = np.tanh(Xs @ W1 + b1); z = a1 @ W2 + b2; d = 2 * (z - t) / len(Xs)
                dW2 = a1.T @ d; db2 = d.sum(0); d1 = (d @ W2.T) * (1 - a1 ** 2); dW1 = Xs.T @ d1; db1 = d1.sum(0)
                W1 -= .05 * dW1; b1 -= .05 * db1; W2 -= .05 * dW2; b2 -= .05 * db2
            s.W.append((W1, b1, W2, b2))
    def acc(s, X, Y):
        Xs = (X - s.mu) / s.sd
        return (np.argmax([np.tanh(Xs @ W1 + b1) @ W2 + b2 for W1, b1, W2, b2 in s.W], 0).ravel() == Y).mean()

for k in (1, 5, 20):
    r_nn, r_ct, r_mlp = [], [], []
    for seed in range(5):
        r = np.random.default_rng(200 + seed)
        idx = np.concatenate([r.choice(np.where(Ytr == c)[0], k, replace=False) for c in range(NC)])
        Xs, Ys = Xtr[idx], Ytr[idx]
        r_nn.append(nn_acc(Xs, Ys)); r_ct.append(cent_acc(Xs, Ys))
        m = OVR(); m.fit(Xs, Ys); r_mlp.append(m.acc(Xte, Yte))
    print(json.dumps({'k': k, 'nn': round(float(np.mean(r_nn)), 4), 'centroid': round(float(np.mean(r_ct)), 4),
                      'mlp': round(float(np.mean(r_mlp)), 4),
                      'nn_seeds': [round(x, 3) for x in r_nn], 'ct_seeds': [round(x, 3) for x in r_ct],
                      'mlp_seeds': [round(x, 3) for x in r_mlp]}), flush=True)
print('DONE', flush=True)
