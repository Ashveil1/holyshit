#!/usr/bin/env python3
"""MLP continual-learning baseline for the same protocol as worm_learn.holy.
Raw pixels (not the worm reservoir) - this is the FAVORABLE case for the MLP.
Small MLP, SGD sequential fine-tuning = the classic catastrophic-forgetting setup.
Phase A: train 0-4 (300/class). Phase B: train 5-8 (375/class). Phase C: 1-shot 9.
"""
import numpy as np
from sklearn.neural_network import MLPClassifier

def load(path):
    X, y = [], []
    with open(path) as f:
        next(f)
        for line in f:
            line = line.rstrip("\n")
            if not line: continue
            y.append(int(line[0]))
            X.append([int(line[2+j], 16) * 17 for j in range(784)])
    return np.array(X, dtype=np.float32) / 255.0, np.array(y)

Xtr, ytr = load("mnist_train.txt")
Xte, yte = load("mnist_test.txt")

def pick(X, y, clslist, per):
    idx = []
    for c in clslist:
        w = np.where(y == c)[0][:per]
        idx.append(w)
    idx = np.concatenate(idx)
    return X[idx], y[idx]

gA, gB = [0,1,2,3,4], [5,6,7,8]
Xa, ya = pick(Xtr, ytr, gA, 300)
Xb, yb = pick(Xtr, ytr, gB, 375)
Xta, yta = pick(Xte, yte, gA, 50)
Xtb, ytb = pick(Xte, yte, gB, 50)
Xt9, yt9 = pick(Xte, yte, [9], 50)
X9, y9 = pick(Xtr, ytr, [9], 1)

clf = MLPClassifier(hidden_layer_sizes=(64,), max_iter=1, random_state=0)
for epoch in range(30):
    clf.partial_fit(Xa, ya, classes=np.arange(10))  # Phase A
print("after A, 0-4:", clf.score(Xta, yta))
print("after A, 5-8 (unseen):", clf.score(Xtb, ytb))
# sequential fine-tune: continue training the SAME net on B only
for epoch in range(30):
    clf.partial_fit(Xb, yb)
print("after B, 0-4 (forgetting check):", clf.score(Xta, yta))
print("after B, 5-8:", clf.score(Xtb, ytb))
clf.partial_fit(X9, y9)  # one-shot
print("after 1-shot, unseen 9:", clf.score(Xt9, yt9))
print("after 1-shot, 0-4 re-check:", clf.score(Xta, yta))
