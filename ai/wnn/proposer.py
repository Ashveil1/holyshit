"""P10: learned program proposer. A small numpy MLP reads hand-designed features of a few I/O examples and
predicts which operators / constants / registers the hidden program uses; predictions bias the GP sampler.
Trained ONLY on random synthetic programs (never on the evaluation tasks).
Run: python3 proposer.py train"""
import random, numpy as np, sys, time, pickle
import gp
OPN = gp.OPS2 + ['ite']; LEAF = ['x', 'y', 'r0', 'r1', 'r2']; CONS = gp.CONSTS
def toks(e, acc):
    if isinstance(e, tuple):
        acc.append(e[0]); [toks(c, acc) for c in e[1:]]
    else: acc.append(e)
def labels(gn):
    acc = []; toks(gn.f, acc); [toks(g, acc) for g in gn.g]
    S = set(acc) | set(str(a) for a in acc)
    return np.array([1.0 if o in acc else 0.0 for o in OPN] + [1.0 if c in acc else 0.0 for c in CONS] + [1.0 if l in acc else 0.0 for l in LEAF], dtype=np.float32)
def feats(data):
    F = []
    mode = gp.detect_mode(data)
    F += [mode == 'tape', mode == 'tape+r', mode == 'final', data[0][1] is not None]
    acc = {}
    def a(k, v): acc.setdefault(k, []).append(float(v))
    for xs, ys, o in data:
        n = len(xs); ps = [sum(xs[:i + 1]) for i in range(n)]; pm = [max(xs[:i + 1]) for i in range(n)]
        z = ys if ys else [0] * n
        if mode == 'final':
            v = o[0]
            for k, ref in (('sum', sum(xs)), ('sum2', sum(xs) % 2), ('sum10', sum(xs) % 10), ('max', max(xs)), ('min', min(xs)), ('len', n),
                           ('first', xs[0]), ('last', xs[-1]), ('cnt_max', xs.count(max(xs))), ('range', max(xs) - min(xs)),
                           ('gtfirst', sum(q > xs[0] for q in xs)), ('alt', sum(q if i % 2 == 0 else -q for i, q in enumerate(xs))),
                           ('2nd', sorted(xs)[-2] if n > 1 else 0), ('cmp', 1.0 if num(xs) > num(z) else 0.0), ('cmp_r', 1.0 if num(xs[::-1]) > num(z[::-1]) else 0.0)):
                a('f_' + k, v == ref)
            a('f_bin', v in (0, 1)); a('f_neg', v < 0); a('f_val', v / 10.0); a('f_small', v <= n)
            for c in (0, 1, 2, 3): a(f'f_cnt{c}', v == xs.count(c))
        else:
            for oo in (o, o[::-1]):
                m = min(len(oo), n)
                a('t_x', np.mean([oo[i] == xs[i] for i in range(m)])); a('t_rx', np.mean([oo[i] == xs[n - 1 - i] for i in range(m)]) if oo is o else 0)
            m = min(len(o), n)
            for nm, ref in (('y', z), ('xy10', [(p + q) % 10 for p, q in zip(xs, z)]), ('ps10', [p % 10 for p in ps]), ('ps2', [p % 2 for p in ps]),
                            ('pm', pm), ('x1', [(p + 1) % 10 for p in xs]), ('xy_rev10', [(p + q) % 10 for p, q in zip(xs[::-1], z[::-1])]),
                            ('add', [int(c) for c in str(num(xs) + num(z)).zfill(n + 1)][::-1]), ('addr', [int(c) for c in str(num(xs) + num(z)).zfill(n + 1)]),
                            ('sub', [int(c) for c in str(abs(num(xs) - num(z))).zfill(n)]), ('mul', [int(c) for c in str(num(xs) * (z[0] if z else 0)).zfill(n + 1)])):
                for oo in (o, o[::-1]):
                    mm = min(len(oo), len(ref)); a('t_' + nm, np.mean([oo[i] == ref[i] for i in range(mm)]) if mm else 0)
            a('t_bin', all(v in (0, 1) for v in o)); a('t_mean', np.mean(o) / 10); a('t_len', len(o) - n)
    global KEYS
    if KEYS is None or any(k not in KEYS for k in acc): KEYS = sorted(set(KEYS or []) | set(acc))
    F += [np.mean(acc[k]) if k in acc else 0.0 for k in KEYS]
    return F
def num(ds): return int(''.join(map(str, ds))) if ds else 0
KEYS = None
_d = [([1,2,3],[4,5,6],[5,7,9])]; _t = [([1,2,3],None,[3])]
feats(_d); feats(_t); feats([([1,2,3],[1,1,1],[1,2,3,4])])
KEYS = sorted(KEYS)
def sample_tasks(N, seed):
    rng = random.Random(seed); X = []; Y = []; tries = 0
    while len(X) < N:
        tries += 1
        two = rng.random() < .35; K = 3
        leaves = ['x'] + (['y'] if two else []) + ['r0', 'r1', 'r2']
        ctx = gp.Ctx(K, leaves, None, False)
        g = [(f'r{i}' if rng.random() < .55 else ctx.tree(rng, rng.choice([1, 2, 2, 3]))) for i in range(K)]
        gn = gp.G(rng.choice(['fwd', 'bwd']), rng.choice(['fwd', 'bwd']), g, ctx.tree(rng, rng.choice([1, 2, 2])))
        mode = rng.choice(['tape', 'final', 'tape+r'])
        try:
            data = []
            for _ in range(8):
                n = rng.randrange(2, 7); xs = [rng.randrange(10) for _ in range(n)]; ys = [rng.randrange(10) for _ in range(n)] if two else None
                data.append((xs, ys, gp.run(gn, K, xs, ys, mode)))
            outs = [tuple(o) for _, _, o in data]
            if len(set(outs)) < 4: continue
            if any(abs(v) > 10**4 for _, _, o in data for v in o): continue
            X.append(feats(data)); Y.append(labels(gn))
        except Exception: continue
    return np.array(X, dtype=np.float32), np.array(Y)
class MLP:
    def __init__(s, d, h, o, seed=0):
        r = np.random.RandomState(seed); s.W1 = r.randn(d, h).astype(np.float32) * .2; s.b1 = np.zeros(h, np.float32)
        s.W2 = r.randn(h, o).astype(np.float32) * .2; s.b2 = np.zeros(o, np.float32)
    def fwd(s, X):
        H = np.tanh(X @ s.W1 + s.b1); return H, 1 / (1 + np.exp(-(H @ s.W2 + s.b2)))
    def fit(s, X, Y, ep=60, lr=0.01, bs=128):
        m = [np.zeros_like(p) for p in (s.W1, s.b1, s.W2, s.b2)]; v = [np.zeros_like(p) for p in m]; t = 0
        for e in range(ep):
            idx = np.random.permutation(len(X))
            for i in range(0, len(X), bs):
                b = idx[i:i + bs]; H, P = s.fwd(X[b]); dO = (P - Y[b]) / len(b)
                gW2 = H.T @ dO; gb2 = dO.sum(0); dH = (dO @ s.W2.T) * (1 - H ** 2); gW1 = X[b].T @ dH; gb1 = dH.sum(0)
                t += 1
                for k, (p, g) in enumerate(zip((s.W1, s.b1, s.W2, s.b2), (gW1, gb1, gW2, gb2))):
                    m[k] = .9 * m[k] + .1 * g; v[k] = .999 * v[k] + .001 * g * g
                    p -= lr * (m[k] / (1 - .9 ** t)) / (np.sqrt(v[k] / (1 - .999 ** t)) + 1e-8)
if __name__ == '__main__':
    t0 = time.time(); N = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    X, Y = sample_tasks(N, 1); Xt, Yt = sample_tasks(2000, 2); print('data', X.shape, round(time.time() - t0), 's', flush=True)
    mu, sd = X.mean(0), X.std(0) + 1e-6; net = MLP(X.shape[1], 96, Y.shape[1]); net.fit((X - mu) / sd, Y)
    _, P = net.fwd((Xt - mu) / sd); base = Yt.mean(0)
    names = OPN + [f'c{c}' for c in CONS] + LEAF
    ll = lambda p: -np.mean(Yt * np.log(p + 1e-9) + (1 - Yt) * np.log(1 - p + 1e-9))
    print('held-out programs: logloss net %.3f vs base-rate %.3f' % (ll(np.clip(P, 1e-3, 1 - 1e-3)), ll(np.tile(np.clip(base, 1e-3, 1 - 1e-3), (len(Yt), 1)))))
    for i, nme in enumerate(names):
        o = np.argsort(P[:, i]); n2 = len(o) // 2; print(f'  {nme:5s} base {base[i]:.2f}  P(label|pred high) {Yt[o[n2:], i].mean():.2f}  P(label|pred low) {Yt[o[:n2], i].mean():.2f}')
    pickle.dump((net, mu, sd), open('/tmp/proposer.pkl', 'wb')); print('saved', round(time.time() - t0), 's')
