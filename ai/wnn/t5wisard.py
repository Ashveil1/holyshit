"""B-236 + B-241 (fixed): WiSARD with 28-bit tuples (28 nodes) on binarized MNIST; Bloom-WiSARD at half RAM.
Few-shot sweep 1/5/20 per class vs one-vs-rest pure-numpy MLP (784-64-1, 800 epochs)."""
import numpy as np, time
def load(path):
    f = open(path); n, npix = map(int, f.readline().split())
    Y = np.zeros(n, int); X = np.zeros((n, npix), np.uint8)
    for i, line in enumerate(f):
        p = line.split(); Y[i] = int(p[0]); X[i] = np.frombuffer(bytes.fromhex(p[1]), np.uint8)
    return (X > 128).astype(np.uint8), Y
Xtr, Ytr = load('mnist_train_raw.txt'); Xte, Yte = load('mnist_test_raw.txt')
rng = np.random.default_rng(0); TUP = rng.permutation(784).reshape(28, 28)
def tuples(X):
    out = np.zeros((len(X), 28), np.int64)
    for j in range(28):
        bits = X[:, TUP[j]]
        out[:, j] = bits.dot(1 << np.arange(28, dtype=np.int64))
    return out
print('tuple extraction...', flush=True)
TTR, TTE = tuples(Xtr), tuples(Xte)
def train_wisard(TT, YY):
    return [[set(np.unique(TT[YY == c, j]).tolist()) for j in range(28)] for c in range(10)]
def acc(nodes, T, Y):
    S = np.zeros((len(T), 10))
    for c in range(10):
        for j in range(28):
            s = nodes[c][j]; S[:, c] += np.array([v in s for v in T[:, j]])
    return ((S / 28).argmax(1) == Y).mean()
t0 = time.time(); nodes = train_wisard(TTR, Ytr); entries = sum(len(s) for c in range(10) for s in nodes[c])
print(f'WiSARD full: acc {acc(nodes, TTE, Yte):.4f}, entries {entries} (~{entries*8//1024}KB sparse 8B/entry), train {time.time()-t0:.0f}s', flush=True)
BB = entries * 64 // 2 // 280  # bits/node at half sparse RAM (8B/entry = 64 bits)
def bhash(v, m): return [(v * 2654435761 + i * 974634) % m for i in range(3)]
nodesB = [[np.zeros(BB, bool) for _ in range(28)] for _ in range(10)]
for c in range(10):
    for j in range(28):
        for v in nodes[c][j]:
            for h in bhash(v, BB): nodesB[c][j][h] = True
S = np.zeros((len(TTE), 10))
for c in range(10):
    for j in range(28):
        bl = nodesB[c][j]
        S[:, c] += np.array([bl[h] for h in [bhash(int(v), BB) for v in TTE[:, j]]]).all(1)
print(f'Bloom-WiSARD half-RAM ({BB}b/node): acc {((S/28).argmax(1)==Yte).mean():.4f}', flush=True)
class OVR:
    def fit(s, X, Y):
        mu, sd = X.mean(0), X.std(0) + 1e-9; s.mu, s.sd = mu, sd; Xs = (X - mu) / sd
        s.W = []
        for c in range(10):
            t = ((Y == c).astype(float) * 2 - 1).reshape(-1, 1)
            rng = np.random.default_rng(c); W1 = rng.normal(0, .5, (784, 32)); b1 = np.zeros(32); W2 = rng.normal(0, .5, (32, 1)); b2 = np.zeros(1)
            for ep in range(800):
                a1 = np.tanh(Xs @ W1 + b1); z = a1 @ W2 + b2; d = 2 * (z - t) / len(Xs)
                dW2 = a1.T @ d; db2 = d.sum(0); d1 = (d @ W2.T) * (1 - a1 ** 2); dW1 = Xs.T @ d1; db1 = d1.sum(0)
                W1 -= .05 * dW1; b1 -= .05 * db1; W2 -= .05 * dW2; b2 -= .05 * db2
            s.W.append((W1, b1, W2, b2))
    def pred(s, X):
        Xs = (X - s.mu) / s.sd
        return np.argmax([np.tanh(Xs @ W1 + b1) @ W2 + b2 for W1, b1, W2, b2 in s.W], 0).ravel()
for k in (1, 5, 20):
    idx = np.concatenate([np.where(Ytr == c)[0][:k] for c in range(10)])
    nk = train_wisard(TTR[idx], Ytr[idx]); a_w = acc(nk, TTE, Yte)
    m = OVR(); m.fit(Xtr[idx].astype(float), Ytr[idx]); a_m = (m.pred(Xte.astype(float)) == Yte).mean()
    print(f'few-shot k={k}: WiSARD {a_w:.4f} | MLP-ovr {a_m:.4f}', flush=True)
