"""P10b: curriculum / transfer. Learn skill A with GP, mine its subtrees as macros (reusable parts),
then learn skill B with the macros available; compare to B alone (same seeds, same budget).
'mixed' = macros mined from ALL earlier skills at once (does a shared library connect tasks?).
python3 curr.py [seeds] [evals]"""
import sys, time, gp, random, numpy as np
def subs(e, out):
    if isinstance(e, tuple):
        if 3 <= gp.size(e) <= 9: out.add(e)
        for c in e[1:]: subs(c, out)
def learn_skill(task, evals=30000, tries=6):
    for s in range(tries):
        data = gp.make_train(task, 60, 100 + s); gn, n, mode = gp.evolve(data, 3, evals, 100 + s)
        if gn and min(gp.test(task, gn, 3, mode).values()) >= 99: return gn
    return None
def macros_of(gns):
    out = set()
    for gn in gns:
        for e in list(gn.g) + [gn.f]: subs(e, out)
    return sorted(out, key=lambda e: (gp.size(e), gp.src(e)))
def solve(task, seeds, evals, macros):
    sol = ok = 0; ev = []
    for s in range(seeds):
        data = gp.make_train(task, 60, s); gn, n, mode = gp.evolve(data, 3, evals, s, macros=macros)
        if gn is None: continue
        sol += 1; ev.append(n); ok += min(gp.test(task, gn, 3, mode).values()) >= 99
    return sol, ok, (np.mean(ev) if ev else 0)
if __name__ == '__main__':
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6; evals = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    SK = ['sumdigits', 'max', 'count3', 'parity_sum', 'compare', 'add', 'sub']
    learned = {}
    for a in SK:
        t0 = time.time(); learned[a] = learn_skill(a)
        print('skill', a, 'learned' if learned[a] else 'FAILED', (gp.src(learned[a].f), [gp.src(g) for g in learned[a].g]) if learned[a] else '', f'{time.time()-t0:.0f}s', flush=True)
    chains = {'second_max': ['max'], 'count_max': ['max', 'count3'], 'max_minus_min': ['max'], 'mul1': ['add'], 'alt_sum': ['sumdigits', 'parity_sum'], 'count_gt_first': ['count3', 'compare']}
    allg = [g for g in learned.values() if g]
    for B, As in chains.items():
        for label, gns in (('alone', []), ('chain ' + '+'.join(As), [learned[a] for a in As if learned[a]]), ('mixed (all skills)', allg)):
            m = macros_of(gns); t0 = time.time(); sol, ok, ev = solve(B, seeds, evals, m)
            print(f'{B:15s} {label:28s} macros={len(m):3d} train-solved {sol}/{seeds} generalizes {ok}/{seeds} mean evals {ev:.0f} {time.time()-t0:.0f}s', flush=True)
