"""B-495: few-shot SNIPS intents - WiSARD (hashed uni+bigram presence bits, 28-bit tuples) vs multinomial NB. LEDGER B-495P."""
import numpy as np, json, hashlib

def load(path):
    f = open(path); n, nc = map(int, f.readline().split())
    Y = np.zeros(n, int); T = []
    for i, line in enumerate(f):
        lab, txt = line.rstrip('\n').split('|', 1); Y[i] = int(lab); T.append(txt)
    return T, Y, nc

Xtr_t, Ytr, NC = load('data/snips_train.txt')
Xte_t, Yte, _ = load('data/snips_test.txt')

def feats(texts):
    out = []
    for t in texts:
        w = t.split()
        out.append(w + [w[i] + '_' + w[i + 1] for i in range(len(w) - 1)])
    return out
Ftr, Fte = feats(Xtr_t), feats(Xte_t)
B = 4096
def bits(fs):
    X = np.zeros((len(fs), B), np.uint8)
    for i, f in enumerate(fs):
        for tok in set(f):
            X[i, int.from_bytes(hashlib.md5(tok.encode()).digest()[:4], 'little') % B] = 1
    return X
rng = np.random.default_rng(0); NT = B // 28
TUP = rng.permutation(B)[:NT * 28].reshape(NT, 28)
POW = (1 << np.arange(28, dtype=np.int64))
def tuples(X):
    return np.stack([X[:, TUP[j]].dot(POW) for j in range(NT)], 1)
Xtr_b, Xte_b = bits(Ftr), bits(Fte)
TTR, TTE = tuples(Xtr_b), tuples(Xte_b)

def wisard_fit(TT, YY):
    return [[set(np.unique(TT[YY == c, j]).tolist()) for j in range(NT)] for c in range(NC)]
def wisard_acc(nodes, T, Y):
    S = np.zeros((len(T), NC))
    for c in range(NC):
        for j in range(NT):
            s = nodes[c][j]
            S[:, c] += np.array([v in s for v in T[:, j]])
    return ((S / NT).argmax(1) == Y).mean()

# NB on uni+bigram counts
vocab = {}
for f in Ftr:
    for tok in set(f): vocab.setdefault(tok, len(vocab))
V = len(vocab)
def counts(fs):
    X = np.zeros((len(fs), V))
    for i, f in enumerate(fs):
        for tok in f:
            j = vocab.get(tok)
            if j is not None: X[i, j] += 1
    return X
Ctr, Cte = counts(Ftr), counts(Fte)
def nb_fit(X, Y):
    pc = np.zeros(NC); lc = []
    for c in range(NC):
        Xc = X[Y == c]; pc[c] = len(Xc) / len(X)
        lc.append(np.log((Xc.sum(0) + 1) / (Xc.sum() + V)))
    return np.log(pc), lc
def nb_acc(model, X, Y):
    pc, lc = model
    S = np.stack([np.log(pc[c]) + X @ lc[c] for c in range(NC)], 1)
    return (S.argmax(1) == Y).mean()

res = {}
for k in (1, 5, 20):
    wa, na = [], []
    for seed in range(10):
        r = np.random.default_rng(100 + seed)
        idx = np.concatenate([r.choice(np.where(Ytr == c)[0], k, replace=False) for c in range(NC)])
        wa.append(wisard_acc(wisard_fit(TTR[idx], Ytr[idx]), TTE, Yte))
        na.append(nb_acc(nb_fit(Ctr[idx], Ytr[idx]), Cte, Yte))
    res[k] = {'wisard': [round(a, 4) for a in wa], 'nb': [round(a, 4) for a in na],
              'wisard_mean': round(float(np.mean(wa)), 4), 'nb_mean': round(float(np.mean(na)), 4)}
    print(json.dumps({'k': k, **res[k]}), flush=True)
print(json.dumps({'vocab': V, 'note': 'vocab from full train (transductive, pre-stated)'}), flush=True)
print('DONE', flush=True)
