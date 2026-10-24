"""B-412..B-434: WiSARD tuple-size x bleaching grid, full-data, mnist/pmnist/snips vs same-harness MLP.
LEDGER pre-reg 2026-10-24."""
import numpy as np, json, time

def load_mnist(path):
    f = open(path); n, npix = map(int, f.readline().split())
    Y = np.zeros(n, int); X = np.zeros((n, npix), np.uint8)
    for i, line in enumerate(f):
        p = line.split(); Y[i] = int(p[0]); X[i] = np.frombuffer(bytes.fromhex(p[1]), np.uint8)
    return (X > 128).astype(np.uint8), Y
Xmtr, Ymtr = load_mnist('mnist_train_raw.txt'); Xmte, Ymte = load_mnist('mnist_test_raw.txt')
PERM = np.random.default_rng(12345).permutation(784)
import b468  # snips features (guarded; does not run its protocol)
TASKS = {
 'mnist': (Xmtr, Ymtr, Xmte, Ymte, 10),
 'pmnist': (Xmtr[:, PERM], Ymtr, Xmte[:, PERM], Ymte, 10),
 'snips': (b468.Xtr, b468.Ytr, b468.Xte, b468.Yte, b468.NC),
}

def tuples_of(X, TUP, POW):
    return np.stack([X[:, TUP[j]].dot(POW) for j in range(len(TUP))], 1)

def fit_counts(T, Y, NC, NT):
    return [[{v: c for v, c in zip(*np.unique(T[Y == c, j], return_counts=True))} for j in range(NT)] for c in range(NC)]

def score(T, nodes, NC, NT, bleach, ntest):
    K = np.zeros((ntest, NC, NT), np.int32)
    for c in range(NC):
        for j in range(NT):
            d = nodes[c][j]
            K[:, c, j] = [d.get(int(v), 0) for v in T[:, j]]
    if not bleach:
        S = (K >= 1).sum(2)
        return S.argmax(1)
    pred = np.full(ntest, -1); b = 0
    while (pred < 0).any() and b < 64:
        b += 1; S = (K >= b).sum(2)
        am = S.argmax(1); uniq = (S == S.max(1, keepdims=True)).sum(1) == 1
        take = (pred < 0) & uniq; pred[take] = am[take]
    pred[pred < 0] = S.argmax(1)[pred < 0]
    return pred

def mlp_acc(Xtr, Ytr, Xte, Yte, NC, epochs, seed):
    rng = np.random.default_rng(seed); B = Xtr.shape[1]
    MU, SD = Xtr.mean(0), Xtr.std(0) + 1e-9
    W1 = rng.normal(0, .1, (B, 64)); b1 = np.zeros(64); W2 = rng.normal(0, .1, (64, NC)); b2 = np.zeros(NC)
    n = len(Xtr)
    for ep in range(epochs):
        for i in range(0, n, 256):
            Xs = (Xtr[i:i+256] - MU) / SD; T = np.eye(NC)[Ytr[i:i+256]]
            a1 = np.tanh(Xs @ W1 + b1); z = a1 @ W2 + b2
            p = np.exp(z - z.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
            d = (p - T) / len(Xs)
            dW2 = a1.T @ d; db2 = d.sum(0); d1 = (d @ W2.T) * (1 - a1 ** 2)
            W1 -= .1 * (Xs.T @ d1); b1 -= .1 * d1.sum(0); W2 -= .1 * dW2; b2 -= .1 * db2
    Xs = (Xte - MU) / SD
    return float((np.argmax(np.tanh(Xs @ W1 + b1) @ W2 + b2, 1) == Yte).mean())

if __name__ == '__main__':
    for task, (Xtr, Ytr, Xte, Yte, NC) in TASKS.items():
        B = Xtr.shape[1]; Xtr = Xtr.astype(np.float64); Xte = Xte.astype(np.float64)
        epochs = 50 if task == 'snips' else 10
        mlp = round(float(np.mean([mlp_acc(Xtr, Ytr, Xte, Yte, NC, epochs, s) for s in (0, 1)])), 4)
        print(json.dumps({'task': task, 'mlp': mlp}), flush=True)
        for s in (8, 16, 32, 64):
            NT = B // s
            TUP = np.random.default_rng(0).permutation(B)[:NT * s].reshape(NT, s)
            POW = (1 << np.arange(s, dtype=np.int64))
            t0 = time.time()
            TTR, TTE = tuples_of(Xtr, TUP, POW), tuples_of(Xte, TUP, POW)
            nodes = fit_counts(TTR, Ytr, NC, NT)
            a_off = float((score(TTE, nodes, NC, NT, False, len(Xte)) == Yte).mean())
            a_on = float((score(TTE, nodes, NC, NT, True, len(Xte)) == Yte).mean())
            print(json.dumps({'task': task, 'tuple': s, 'bleach_off': round(a_off, 4), 'bleach_on': round(a_on, 4),
                              'sec': round(time.time() - t0, 1)}), flush=True)
    print('DONE', flush=True)
