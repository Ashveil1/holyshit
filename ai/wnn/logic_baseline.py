#!/usr/bin/env python3
"""MLP + lookup baselines for logic.holy (P5), same splits and raw encodings.
Split rule and encodings match logic.holy exactly (xr_next RNG replicated).
Prints train/held-out accuracy for each experiment."""
import numpy as np
from sklearn.neural_network import MLPClassifier

MASK = 17592186044415
def xr_next(s):
    s = (s ^ ((s << 13) & MASK)) & MASK
    s = s ^ (s >> 7)
    s = (s ^ ((s << 17) & MASK)) & MASK
    return s

def split_mask(P, seed):
    te = np.zeros(P, dtype=bool); s = seed
    for i in range(P):
        s = xr_next(s + i*7919 + 1)
        te[i] = (s % 4) == 0
    return te

def bipolar_rows(patterns):
    X = np.zeros((len(patterns), 2*len(patterns[0])), dtype=float)
    for i, bits in enumerate(patterns):
        X[i, [2*j if b else 2*j+1 for j, b in enumerate(bits)]] = 1
    return X

def chan_rows(chan_lists, nch):
    X = np.zeros((len(chan_lists), nch), dtype=float)
    for i, ch in enumerate(chan_lists): X[i, ch] = 1
    return X

def therm(v, w): return list(range(v+1))
def onehot(v, w): return [v]

def mlp(X, y, te):
    clf = MLPClassifier(hidden_layer_sizes=(64,), max_iter=2000, random_state=0)
    clf.fit(X[~te], y[~te])
    return clf.score(X[~te], y[~te]), clf.score(X[te], y[te])

def lookup(y, te):
    vals, cnt = np.unique(y[~te], return_counts=True)
    maj = vals[cnt.argmax()]
    return 1.0, float(np.mean(y[te] == maj))

def rep(name, m, l):
    print(f"{name}: MLP train {m[0]:.3f} held-out {m[1]:.3f} | lookup held-out {l[1]:.3f}")

# E1
te = split_mask(256, 555)
bits = [[(x>>b)&1 for b in range(8)] for x in range(256)]
X = bipolar_rows(bits)
funcs = {
  "MAJORITY8": lambda x: int(sum(bits[x]) >= 4),
  "PARITY8": lambda x: sum(bits[x]) % 2,
  "DNF4": lambda x: int(any(((x>>(2*t))&3)==3 for t in range(4))),
}
for name, f in funcs.items():
    y = np.array([f(x) for x in range(256)])
    rep(f"E1 {name}", mlp(X, y, te), lookup(y, te))

# E2
te2 = split_mask(256, 777)
pairs = [(a,b) for a in range(16) for b in range(16)]
yadd = np.array([a+b for a,b in pairs])
te_sys = np.array([a >= 8 for a,b in pairs])
for ename, ef in (("onehot", onehot), ("therm", therm)):
    chans = [[c+off for c, off in zip(ef(a,16)+[x+16 for x in ef(b,16)], [0]*16)] for a,b in pairs]
    chans = [ef(a,16) + [16+x for x in ef(b,16)] for a,b in pairs]
    X2 = chan_rows(chans, 32)
    rep(f"E2 add[{ename}] in-domain", mlp(X2, yadd, te2), lookup(yadd, te2))
    rep(f"E2 add[{ename}] systematic", mlp(X2, yadd, te_sys), lookup(yadd, te_sys))

# E3
spairs = [(a,d) for a in range(32) for d in range(1,8)]
yseq = np.array([(a+2*d) % 32 for a,d in spairs])
te3 = split_mask(len(spairs), 999)
te3s = np.array([d == 7 for a,d in spairs])
chans = [therm(a,32) + [32+x for x in therm((a+d)%32,32)] for a,d in spairs]
X3 = chan_rows(chans, 64)
rep("E3 seq in-domain", mlp(X3, yseq, te3), lookup(yseq, te3))
rep("E3 seq systematic(d=7)", mlp(X3, yseq, te3s), lookup(yseq, te3s))

# E4 continual
def fnout(fn, x):
    if fn == 0: return int(x == 255)
    if fn == 1: return int(x != 0)
    return sum(bits[x]) % 2
raw20 = {}
for fn in (0,1,2):
    pats = [[(x>>b)&1 for b in range(8)] + [fn&1, (fn>>1)&1] for x in range(256)]
    raw20[fn] = bipolar_rows(pats)
clf = MLPClassifier(hidden_layer_sizes=(64,), max_iter=1, warm_start=True, random_state=0)
first = True
for fn in (0,1,2):
    yf = np.array([fnout(fn,x) for x in range(256)])
    for ep in range(300):
        if first:
            clf.partial_fit(raw20[fn], yf, classes=np.array([0,1])); first = False
        else:
            clf.partial_fit(raw20[fn], yf)
    row = [clf.score(raw20[f], np.array([fnout(f,x) for x in range(256)])) for f in (0,1,2)]
    print(f"E4 MLP after fn{fn}: AND {row[0]:.3f} OR {row[1]:.3f} PARITY {row[2]:.3f}")
