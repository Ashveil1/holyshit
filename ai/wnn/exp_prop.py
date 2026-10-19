"""Guided vs unguided GP (K=3) on held-out tasks. python3 exp_prop.py TASKS [seeds] [evals]"""
import sys, pickle, numpy as np, time, gp, proposer as P
import __main__; __main__.MLP = P.MLP
net, mu, sd = pickle.load(open('/tmp/proposer.pkl', 'rb'))
def guide(data):
    x = (np.array([P.feats(data)], dtype=np.float32) - mu) / sd; _, p = net.fwd(x); p = p[0]
    ops = {o: 0.3 + 2.0 * p[i] for i, o in enumerate(P.OPN)}
    cw = {c: 0.3 + 2.0 * p[len(P.OPN) + i] for i, c in enumerate(P.CONS)}
    lw = {l: 0.3 + 2.0 * p[len(P.OPN) + len(P.CONS) + i] for i, l in enumerate(P.LEAF)}
    return ops, cw, lw, p
tasks = sys.argv[1].split(','); seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 6; evals = int(sys.argv[3]) if len(sys.argv) > 3 else 20000
for task in tasks:
    for guided in (False, True):
        sol = ok = 0; ev = []; t0 = time.time()
        for s in range(seeds):
            data = gp.make_train(task, 60, s); mode = gp.detect_mode(data); kw = {}
            if guided:
                ops, cw, lw, _ = guide(data[:8]); kw = dict(prior=ops, cw=cw, lw=lw)
            gn, n, mode = gp.evolve(data, 3, evals, s, **kw)
            if gn is None: continue
            sol += 1; ev.append(n); t = gp.test(task, gn, 3, mode); ok += min(t.values()) >= 99
        print(f'{task:15s} {"guided  " if guided else "unguided"} train-solved {sol}/{seeds} generalizes {ok}/{seeds} mean evals(solved) {np.mean(ev) if ev else 0:.0f} {time.time()-t0:.0f}s', flush=True)
