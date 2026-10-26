"""B-504: tiny pure-numpy transformer as a same-protocol reference point on the P15
unseen-synonyms task. Hypothesis classification over text2prog.HYP (21 labels) with
soft CE over the consistent-hypothesis set; answer via run_hyp on real numbers.
Protocol = text2prog.py __main__: train gen_set(rng,0,400), eval gen_set(r,wh,300,big=True).
Gradient-checked before training (pre-registered harness sanity)."""
import random, math, json, time
import numpy as np
import text2prog as P
from text2prog import Learner, gen_set, evaluate, HYP, run_hyp, numbers_of

D, FF, LR, EPOCHS, LMAX, NTR, NEV, SEEDS = 32, 64, 3e-3, 30, 24, 400, 300, range(3)
OPS_L = list({h[0] for h in HYP})

def tok_ids(text, vocab):
    ids = []
    for t in text.split():
        if any(c.isdigit() for c in t): t = '<NUM>'
        ids.append(vocab.get(t, vocab['<unk>']))
    return ids[:LMAX]

def soft_label(text, ans):
    nums = numbers_of(text); cons = [i for i, h in enumerate(HYP) if run_hyp(h, nums) == ans]
    if not cons: return None
    y = np.zeros(len(HYP)); y[cons] = 1.0 / len(cons)
    return y

class TF:
    def __init__(s, V, rng):
        k = lambda *sh: rng.standard_normal(sh) * 0.05
        s.p = {'E': k(V, D), 'P': k(LMAX, D), 'Wq': k(D, D), 'Wk': k(D, D), 'Wv': k(D, D),
               'Wo': k(D, D), 'W1': k(D, FF), 'b1': np.zeros(FF), 'W2': k(FF, D), 'b2': np.zeros(D),
               'Wh': k(D, len(HYP)), 'bh': np.zeros(len(HYP))}
        s.m = {k2: np.zeros_like(v) for k2, v in s.p.items()}; s.v = {k2: np.zeros_like(v) for k2, v in s.p.items()}; s.t = 0
    def fwd(s, ids):
        p = s.p; n = len(ids)
        X = p['E'][ids] + p['P'][:n]                                    # n x D
        Q, K, Vv = X @ p['Wq'], X @ p['Wk'], X @ p['Wv']
        A = Q @ K.T / math.sqrt(D); A = A - A.max(1, keepdims=True)
        S = np.exp(A); S = S / S.sum(1, keepdims=True)                  # softmax rows
        attn = S @ Vv; Z1 = X + attn @ p['Wo']                          # residual 1
        H = np.maximum(0, Z1 @ p['W1'] + p['b1']); Z2 = Z1 + H @ p['W2'] + p['b2']  # residual 2
        pooled = Z2.mean(0); logits = pooled @ p['Wh'] + p['bh']
        logits = logits - logits.max(); ex = np.exp(logits); prob = ex / ex.sum()
        s.cache = (ids, n, X, Q, K, Vv, S, attn, Z1, H, Z2, pooled, prob)
        return prob
    def loss(s, ids, y):
        prob = s.fwd(ids)
        return -float((y * np.log(prob + 1e-12)).sum())
    def bwd(s, y):
        p = s.p; (ids, n, X, Q, K, Vv, S, attn, Z1, H, Z2, pooled, prob) = s.cache
        g = {k2: np.zeros_like(v) for k2, v in p.items()}
        dl = prob - y                                                   # n/a: soft CE grad
        g['Wh'] = np.outer(pooled, dl); g['bh'] = dl
        dpooled = p['Wh'] @ dl
        dZ2 = np.repeat(dpooled[None, :] / n, n, axis=0)                # n x D
        dH = dZ2 @ p['W2'].T; g['W2'] = H.T @ dZ2; g['b2'] = dZ2.sum(0)
        dZ1 = dZ2 + (dH * (H > 0)) @ p['W1'].T; g['W1'] = Z1.T @ (dH * (H > 0)); g['b1'] = (dH * (H > 0)).sum(0)
        dattn = dZ1 @ p['Wo'].T; g['Wo'] = attn.T @ dZ1
        dS = dattn @ Vv.T
        dA = S * (dS - (dS * S).sum(1, keepdims=True))                  # softmax jacobian
        dA = dA / math.sqrt(D)
        dQ = dA @ K; dK = dA.T @ Q; dV = S.T @ dattn
        g['Wq'] = X.T @ dQ; g['Wk'] = X.T @ dK; g['Wv'] = X.T @ dV
        dX = dZ1 + dQ @ p['Wq'].T + dK @ p['Wk'].T + dV @ p['Wv'].T
        for i, tid in enumerate(ids):
            g['E'][tid] += dX[i]; g['P'][i] += dX[i]
        return g
    def step(s, g):
        s.t += 1
        for k2 in s.p:
            s.m[k2] = 0.9 * s.m[k2] + 0.1 * g[k2]; s.v[k2] = 0.999 * s.v[k2] + 0.001 * g[k2] ** 2
            mh = s.m[k2] / (1 - 0.9 ** s.t); vh = s.v[k2] / (1 - 0.999 ** s.t)
            s.p[k2] -= LR * mh / (np.sqrt(vh) + 1e-8)
    def predict(s, ids):
        return HYP[int(np.argmax(s.fwd(ids)))]

def gradcheck(model, ids, y):
    eps = 1e-5; rng = np.random.default_rng(0); bad = 0; checked = 0
    model.fwd(ids); ga = model.bwd(y)
    for key in model.p:
        flat = model.p[key].ravel()
        idx = rng.choice(flat.size, size=min(4, flat.size), replace=False)
        for i in idx:
            orig = flat[i]
            flat[i] = orig + eps; lp = model.loss(ids, y)
            flat[i] = orig - eps; lm = model.loss(ids, y)
            flat[i] = orig
            num = (lp - lm) / (2 * eps); ana = ga[key].ravel()[i]
            rel = abs(num - ana) / max(1e-8, abs(num) + abs(ana))
            checked += 1; bad += (abs(num - ana) > 1e-6 and rel > 1e-3)  # amended combined criterion, LEDGER 2026-10-24
    return checked, bad

class Ref:
    """wraps TF to the Learner.answer interface for evaluate()"""
    def __init__(s, model, vocab): s.model, s.vocab = model, vocab
    def answer(s, text):
        h = s.model.predict(tok_ids(text, s.vocab))
        return run_hyp(h, numbers_of(text)), h, 0

def arm(sd):
    rng = random.Random(sd)
    train = gen_set(rng, 0, NTR)
    r = random.Random(100 + sd)
    evals = {wh: gen_set(random.Random(100 + sd), wh, NEV, big=True) for wh in (0, 1, 2)}
    # wnn reference row (same data)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in train])
    wnn = {wh: evaluate(L, rows)[0] for wh, rows in evals.items()}
    # transformer
    vocab = {'<unk>': 0, '<NUM>': 1}
    for _, t, a in train:
        for tok in t.split():
            if any(c.isdigit() for c in tok): tok = '<NUM>'
            if tok not in vocab: vocab[tok] = len(vocab)
    nrng = np.random.default_rng(sd)
    M = TF(len(vocab), nrng)
    rows = []
    skipped = 0
    for _, t, a in train:
        y = soft_label(t, a)
        if y is None: skipped += 1; continue
        rows.append((tok_ids(t, vocab), y))
    checked, bad = gradcheck(M, rows[0][0], rows[0][1])
    if bad: return {'seed': sd, 'gradcheck': f'FAIL {bad}/{checked}'}
    for ep in range(EPOCHS):
        random.Random(sd * 100 + ep).shuffle(rows)
        for ids, y in rows:
            M.fwd(ids); M.step(M.bwd(y))
    R = Ref(M, vocab)
    tf = {wh: evaluate(R, rows2)[0] for wh, rows2 in evals.items()}
    return {'seed': sd, 'gradcheck': f'pass {checked}', 'vocab': len(vocab), 'skipped': skipped,
            'wnn': {str(k): round(v, 3) for k, v in wnn.items()}, 'tf': {str(k): round(v, 3) for k, v in tf.items()}}

if __name__ == '__main__':
    t0 = time.time(); out = []
    for sd in SEEDS:
        row = arm(sd); out.append(row); print(json.dumps(row), flush=True)
        if 'gradcheck' in row and 'FAIL' in row['gradcheck']: print('DONE gradcheck-failed', flush=True); break
    else:
        for wh in ('0', '1', '2'):
            mw = sum(r['wnn'][wh] for r in out) / len(out); mt = sum(r['tf'][wh] for r in out) / len(out)
            print(f'MEAN wh={wh}: wnn {mw:.3f} | tf {mt:.3f}', flush=True)
    print(f'DONE wall_s={round(time.time() - t0)}', flush=True)
