"""T4 baselines (B-188..B-208): MLP/kNN/majority/linreg on the exact cur7 protocol.
Train: 25 examples, scales {1,2} (rng.choice per example). Eval: 40 examples/scale, scales 1-4,
te=Random(1000+seed). y input is a RANDOM DISTRACTOR on unary tasks (the program search must ignore it).
Classification tasks (even, isprime): threshold .5. Regression: round to int, exact match. 3 seeds."""
import random, json, math
import numpy as np
from cur7 import gen
TASKS = ['mod', 'mul', 'div', 'power', 'gcd', 'isprime', 'fact', 'sumto', 'max', 'min', 'square', 'cube', 'choose2', 'sumsq', 'dblfact', 'absdiff', 'lcm', 'even']
CLS = {'even', 'isprime'}
def data(task, seed):
    rng = random.Random(seed); tr = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    te = random.Random(1000 + seed); ev = {sc: [gen(task, te, sc) for _ in range(40)] for sc in (1, 2, 3, 4)}
    return tr, ev
def xy(rows): X = np.array([[r[0], r[1]] for r in rows], float); Y = np.array([r[2] for r in rows], float); return X, Y
class MLP:
    def __init__(s, cls): s.cls = cls
    def fit(s, X, Y):
        mu, sd = X.mean(0), X.std(0) + 1e-9; Xs = (X - mu) / sd; s.mu, s.sd = mu, sd
        rng = np.random.default_rng(0)
        W1 = rng.normal(0, .5, (2, 32)); b1 = np.zeros(32); W2 = rng.normal(0, .5, (32, 32)); b2 = np.zeros(32)
        if s.cls: W3 = rng.normal(0, .5, (32, 1)); b3 = np.zeros(1); t = Y.reshape(-1, 1)
        else: s.ym, s.ys = Y.mean(), Y.std() + 1e-9; t = ((Y - s.ym) / s.ys).reshape(-1, 1); W3 = rng.normal(0, .5, (32, 1)); b3 = np.zeros(1)
        lr = 0.05; n = len(Xs)
        for ep in range(3000):
            z1 = Xs @ W1 + b1; a1 = np.tanh(z1); z2 = a1 @ W2 + b2; a2 = np.tanh(z2); z3 = a2 @ W3 + b3
            if s.cls: p = 1 / (1 + np.exp(-z3)); d = (p - t) / n
            else: d = 2 * (z3 - t) / n
            dW3 = a2.T @ d; db3 = d.sum(0); d2 = (d @ W3.T) * (1 - a2 ** 2)
            dW2 = a1.T @ d2; db2 = d2.sum(0); d1 = (d2 @ W2.T) * (1 - a1 ** 2)
            dW1 = Xs.T @ d1; db1 = d1.sum(0)
            for W, dW in ((W1, dW1), (W2, dW2), (W3, dW3)): W -= lr * dW
            for b, db in ((b1, db1), (b2, db2), (b3, db3)): b -= lr * db
        s.W = (W1, b1, W2, b2, W3, b3)
    def pred(s, X):
        Xs = (X - s.mu) / s.sd; W1, b1, W2, b2, W3, b3 = s.W
        z = np.tanh(np.tanh(Xs @ W1 + b1) @ W2 + b2) @ W3 + b3
        z = z.ravel()
        if s.cls: return (z > 0).astype(int)
        return np.round(z * s.ys + s.ym)
def knn(Xtr, Ytr, Xte, k=3, cls=False):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9; A = (Xtr - mu) / sd; B = (Xte - mu) / sd
    out = []
    for b in B:
        d = ((A - b) ** 2).sum(1); idx = np.argsort(d)[:k]; v = Ytr[idx]
        out.append(int(np.round(np.mean(v))) if not cls else int(np.mean(v) > .5))
    return np.array(out)
def run(task, seed):
    tr, ev = data(task, seed); Xtr, Ytr = xy(tr); cls = task in CLS
    m = MLP(cls); m.fit(Xtr, Ytr)
    maj = int(np.round(np.mean(Ytr))) if not cls else int(np.mean(Ytr) > .5)
    X = np.linalg.lstsq(np.c_[np.ones(len(Xtr)), Xtr], Ytr, rcond=None)[0]
    res = {}
    for sc, rows in ev.items():
        Xte, Yte = xy(rows); r = {}
        r['mlp'] = int((m.pred(Xte) == Yte).sum())
        r['knn'] = int((knn(Xtr, Ytr, Xte, cls=cls) == Yte).sum())
        r['maj'] = int((np.full(len(Yte), maj) == Yte).sum())
        pr = np.round(np.c_[np.ones(len(Xte)), Xte] @ X)
        if cls: pr = (pr > .5).astype(int)
        r['lin'] = int((pr == Yte).sum())
        res[sc] = r
    return res
if __name__ == '__main__':
    all_res = {}
    for task in TASKS:
        agg = {b: {sc: [] for sc in (1, 2, 3, 4)} for b in ('mlp', 'knn', 'maj', 'lin')}
        for seed in range(3):
            res = run(task, seed)
            for b in agg:
                for sc in agg[b]: agg[b][sc].append(res[sc][b])
        all_res[task] = {b: {sc: round(sum(v) / len(v), 1) for sc, v in scs.items()} for b, scs in agg.items()}
        print(task, json.dumps(all_res[task]), flush=True)
    json.dump(all_res, open('logs/t4base.json', 'w'), indent=1)
    # B-208: frozen eval pack v1 (seed 0 protocol)
    pack = {t: {'train': data(t, 0)[0], 'eval': {str(sc): rows for sc, rows in data(t, 0)[1].items()}} for t in TASKS}
    json.dump(pack, open('evalpack_v1.json', 'w'))
    print('evalpack_v1.json written', flush=True)
