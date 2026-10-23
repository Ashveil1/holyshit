import numpy as np, json
def load(path):
    f = open(path); n, npix = map(int, f.readline().split())
    Y = np.zeros(n, int); X = np.zeros((n, npix), np.uint8)
    for i, line in enumerate(f):
        p = line.split(); Y[i] = int(p[0]); X[i] = np.frombuffer(bytes.fromhex(p[1]), np.uint8)
    return (X > 128).astype(np.uint8), Y
Xtr, Ytr = load('mnist_train_raw.txt'); Xte, Yte = load('mnist_test_raw.txt')
NT = 5
def run_seed(sd):
    rng = np.random.default_rng(sd); TUP = rng.permutation(784).reshape(28, 28)
    PERMS = [np.arange(784)] + [np.random.default_rng(1000 + sd * 10 + k).permutation(784) for k in range(1, NT)]
    def tuples(X):
        out = np.zeros((len(X), 28), np.int64)
        for j in range(28):
            out[:, j] = X[:, TUP[j]].dot(1 << np.arange(28, dtype=np.int64))
        return out
    TTRk = [tuples(Xtr[:, p]) for p in PERMS]; TTEk = [tuples(Xte[:, p]) for p in PERMS]
    def acc_w(nodes, T, Y):
        S = np.zeros((len(T), 10))
        for c in range(10):
            for j in range(28):
                s = nodes[c][j]
                if s: S[:, c] += np.array([v in s for v in T[:, j]])
        return (S.argmax(1) == Y).mean()
    shared = {c: [set() for _ in range(28)] for c in range(10)}
    pertask = [{c: [set() for _ in range(28)] for c in range(10)} for _ in range(NT)]
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
    def pred(X): return np.argmax(np.tanh(((X - MU) / SD) @ W1 + b1) @ W2 + b2, 1)
    curve = {'shared': [], 'pertask': [], 'mlp': []}
    for k in range(NT):
        for c in range(10):
            sel = Ytr == c
            for j in range(28):
                v = np.unique(TTRk[k][sel, j])
                shared[c][j] |= set(v.tolist()); pertask[k][c][j] |= set(v.tolist())
        fit(Xtr[:, PERMS[k]], Ytr, 300)
        curve['shared'].append(round(float(acc_w(shared, TTEk[0], Yte)), 4))
        curve['pertask'].append(round(float(acc_w(pertask[0], TTEk[0], Yte)), 4))
        curve['mlp'].append(round(float((pred(Xte[:, PERMS[0]]) == Yte).mean()), 4))
    allmean = round(float(np.mean([acc_w(shared, TTEk[k], Yte) for k in range(NT)])), 4)
    return {'seed': sd, 'task1_curve_after_k': curve, 'shared_all_task_mean': allmean}
for sd in range(3):
    print(json.dumps(run_seed(sd)), flush=True)
print('DONE', flush=True)
