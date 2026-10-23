import numpy as np, time, json
def load(path):
    f = open(path); n, npix = map(int, f.readline().split())
    Y = np.zeros(n, int); X = np.zeros((n, npix), np.uint8)
    for i, line in enumerate(f):
        p = line.split(); Y[i] = int(p[0]); X[i] = np.frombuffer(bytes.fromhex(p[1]), np.uint8)
    return (X > 128).astype(np.uint8), Y
Xtr, Ytr = load('mnist_train_raw.txt'); Xte, Yte = load('mnist_test_raw.txt')

def run_seed(sd):
    rng = np.random.default_rng(sd); TUP = rng.permutation(784).reshape(28, 28)
    def tuples(X):
        out = np.zeros((len(X), 28), np.int64)
        for j in range(28):
            out[:, j] = X[:, TUP[j]].dot(1 << np.arange(28, dtype=np.int64))
        return out
    TTR, TTE = tuples(Xtr), tuples(Xte)
    A_tr = Ytr < 5; B_tr = Ytr >= 5; A_te = Yte < 5; B_te = Yte >= 5
    # WiSARD arm
    def train_w(TT, YY, classes, nodes=None):
        if nodes is None: nodes = {c: [set() for _ in range(28)] for c in range(10)}
        for c in classes:
            for j in range(28): nodes[c][j] |= set(np.unique(TT[YY == c, j]).tolist())
        return nodes
    def acc_w(nodes, T, Y):
        S = np.zeros((len(T), 10))
        for c in range(10):
            if not nodes[c][0]: continue
            for j in range(28):
                s = nodes[c][j]; S[:, c] += np.array([v in s for v in T[:, j]])
        return (S.argmax(1) == Y).mean()
    nd = train_w(TTR[A_tr], Ytr[A_tr], range(5))
    w_A1 = acc_w(nd, TTE[A_te], Yte[A_te])
    nd = train_w(TTR[B_tr], Ytr[B_tr], range(5, 10), nd)
    w_A2 = acc_w(nd, TTE[A_te], Yte[A_te]); w_B = acc_w(nd, TTE[B_te], Yte[B_te]); w_all = acc_w(nd, TTE, Yte)
    # MLP arm: shared hidden 784-64-10 softmax, sequential phases
    r2 = np.random.default_rng(100 + sd)
    W1 = r2.normal(0, .1, (784, 64)); b1 = np.zeros(64); W2 = r2.normal(0, .1, (64, 10)); b2 = np.zeros(10)
    def fit(X, Y, eps):
        mu, sd_ = X.mean(0), X.std(0) + 1e-9
        Xs = (X - mu) / sd_; T = np.eye(10)[Y]
        for ep in range(eps):
            a1 = np.tanh(Xs @ W1 + b1); z = a1 @ W2 + b2
            p = np.exp(z - z.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
            d = (p - T) / len(Xs)
            dW2 = a1.T @ d; db2 = d.sum(0); d1 = (d @ W2.T) * (1 - a1 ** 2)
            W1 -= .5 * (Xs.T @ d1); b1 -= .5 * d1.sum(0); W2 -= .5 * dW2; b2 -= .5 * db2
    def pred(X):
        mu, sd_ = X.mean(0), X.std(0) + 1e-9
        return np.argmax(np.tanh(((X - mu) / sd_) @ W1 + b1) @ W2 + b2, 1)
    fit(Xtr[A_tr], Ytr[A_tr], 300)
    m_A1 = (pred(Xte[A_te]) == Yte[A_te]).mean()
    fit(Xtr[B_tr], Ytr[B_tr], 300)
    m_A2 = (pred(Xte[A_te]) == Yte[A_te]).mean(); m_B = (pred(Xte[B_te]) == Yte[B_te]).mean()
    m_all = (pred(Xte) == Yte).mean()
    return {'seed': sd,
            'wisard': {'A_after_A': round(float(w_A1), 4), 'A_after_B': round(float(w_A2), 4), 'B': round(float(w_B), 4), 'all': round(float(w_all), 4)},
            'mlp': {'A_after_A': round(float(m_A1), 4), 'A_after_B': round(float(m_A2), 4), 'B': round(float(m_B), 4), 'all': round(float(m_all), 4)}}
for sd in range(3):
    print(json.dumps(run_seed(sd)), flush=True)
print('DONE', flush=True)
