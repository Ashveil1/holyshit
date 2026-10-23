"""B-497: symbolic unit conversion vs closed-set MLP text classifier. Boundary measurement, outcome expected. LEDGER B-497P."""
import numpy as np, json, hashlib
from fractions import Fraction

UNITS = {'mm': ('L', Fraction(1, 1000)), 'cm': ('L', Fraction(1, 100)), 'm': ('L', Fraction(1)),
         'km': ('L', Fraction(1000)), 'mg': ('M', Fraction(1, 1000)), 'g': ('M', Fraction(1)),
         'kg': ('M', Fraction(1000)), 's': ('T', Fraction(1)), 'min': ('T', Fraction(60)), 'h': ('T', Fraction(3600))}
TEMPLATES = ["convert {x} {u} to {v}", "how many {v} in {x} {u}", "{x} {u} in {v}"]

def fmt_x(f):
    return str(f.numerator // f.denominator) if f.denominator == 1 else f"{float(f):.3f}".rstrip('0').rstrip('.')
def fmt_ans(f):
    return fmt_x(f)

def gen_problems(rng, dim_pairs, xs, n_per):
    out = []
    for (u, v) in dim_pairs:
        fu, fv = UNITS[u][1], UNITS[v][1]
        for x in xs:
            for t in TEMPLATES:
                out.append((t.format(x=fmt_x(x), u=u, v=v), fmt_ans(x * fu / fv)))
    rng.shuffle(out)
    return out[:n_per * len(dim_pairs) * len(xs)] if n_per else out

rng = np.random.default_rng(0)
pairs_by_dim = {'L': [('km', 'm'), ('m', 'cm'), ('cm', 'mm'), ('m', 'mm')],
                'M': [('kg', 'g'), ('g', 'mg')], 'T': [('h', 'min'), ('min', 's'), ('h', 's')]}
train_pairs = [('km', 'm'), ('m', 'cm'), ('kg', 'g'), ('h', 'min'), ('min', 's')]
unseen_pairs = [('m', 'mm'), ('cm', 'mm'), ('g', 'mg'), ('h', 's')]
train_xs = [Fraction(n) for n in range(1, 13)] + [Fraction(n, 2) for n in range(1, 25, 2)]  # ints 1..12 + halves .5..12
unseen_xs = [Fraction(n) for n in (13, 17, 25, 100)] + [Fraction(3, 4), Fraction(7, 2)]
train = gen_problems(np.random.default_rng(1), train_pairs, train_xs, 0)
test_seen = [p for p in gen_problems(np.random.default_rng(2), train_pairs, train_xs, 0)]
test_unx = gen_problems(np.random.default_rng(3), train_pairs, unseen_xs, 0)
test_unp = gen_problems(np.random.default_rng(4), unseen_pairs, train_xs, 0)

# symbolic arm
import re
def solve(q):
    toks = q.split()
    ni = [i for i, t in enumerate(toks) if re.fullmatch(r'\d+(\.\d+)?', t)]
    us = [t for t in toks if t in UNITS]
    if len(ni) != 1 or len(us) != 2 or ni[0] + 1 >= len(toks): return None
    x = Fraction(toks[ni[0]]); u = toks[ni[0] + 1]  # the unit the number quantifies = source
    if u not in UNITS: return None
    v = us[1] if us[0] == u else us[0]
    if UNITS[u][0] != UNITS[v][0]: return None
    return fmt_ans(x * UNITS[u][1] / UNITS[v][1])

# MLP arm: hashed word bits -> closed-set classifier over training answers
B = 2048
def bits(texts):
    X = np.zeros((len(texts), B))
    for i, t in enumerate(texts):
        for tok in set(t.split()):
            X[i, int.from_bytes(hashlib.md5(tok.encode()).digest()[:4], 'little') % B] = 1
    return X
answers = sorted(set(a for _, a in train))
aidx = {a: i for i, a in enumerate(answers)}
Xtr = bits([q for q, _ in train]); Ytr = np.array([aidx[a] for _, a in train])
def mlp_fit(seed, epochs=600):
    r = np.random.default_rng(seed)
    W1 = r.normal(0, .5, (B, 64)); b1 = np.zeros(64); W2 = r.normal(0, .5, (64, len(answers))); b2 = np.zeros(len(answers))
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9; Xs = (Xtr - mu) / sd; T = np.eye(len(answers))[Ytr]
    for ep in range(epochs):
        a1 = np.tanh(Xs @ W1 + b1); z = a1 @ W2 + b2
        p = np.exp(z - z.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
        d = (p - T) / len(Xs)
        dW2 = a1.T @ d; db2 = d.sum(0); d1 = (d @ W2.T) * (1 - a1 ** 2)
        W1 -= .5 * (Xs.T @ d1); b1 -= .5 * d1.sum(0); W2 -= .5 * dW2; b2 -= .5 * db2
    return (W1, b1, W2, b2, mu, sd)
def mlp_acc(model, rows):
    W1, b1, W2, b2, mu, sd = model
    X = (bits([q for q, _ in rows]) - mu) / sd
    pred = np.argmax(np.tanh(X @ W1 + b1) @ W2 + b2, 1)
    return np.mean([answers[p] == a for p, (_, a) in zip(pred, rows)])

res = {'n_train': len(train), 'n_answers': len(answers),
       'splits': {'seen': len(test_seen), 'unseen_x': len(test_unx), 'unseen_pair': len(test_unp)}}
for name, rows in (('seen', test_seen), ('unseen_x', test_unx), ('unseen_pair', test_unp)):
    sym = np.mean([solve(q) == a for q, a in rows])
    res[f'sym_{name}'] = round(float(sym), 4)
accs = {s: {} for s in ('seen', 'unseen_x', 'unseen_pair')}
for seed in range(3):
    m = mlp_fit(seed)
    for name, rows in (('seen', test_seen), ('unseen_x', test_unx), ('unseen_pair', test_unp)):
        accs[name][seed] = round(float(mlp_acc(m, rows)), 4)
res['mlp'] = {k: {'seeds': v, 'mean': round(float(np.mean(list(v.values()))), 4)} for k, v in accs.items()}
print(json.dumps(res), flush=True)
print('DONE', flush=True)
