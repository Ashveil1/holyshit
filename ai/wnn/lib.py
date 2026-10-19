"""P8: library learning (DreamCoder-style, tiny). Solve base tasks with the raw DSL, MINE repeated
(op, const) patterns from the solved programs' text, add them as cheap primitives (cost +1 over
the child instead of +2), then solve NEW tasks with a much smaller bank than raw needs.
Run: python3 lib.py"""
import induce as I, random, time, re, collections, gc
def tr(task, seed=1):
    rng = random.Random(seed); hard = task in ('sub', 'compare')
    return [I.mk(task, rng, rng.choice([1, 2, 3, 4] if hard else [1, 2, 3])) for _ in range(40 if hard else 20)]
def ev(task, prog):
    rng = random.Random(7)
    out = []
    for n in (4, 6, 10, 20, 50):
        ok = 0
        for _ in range(200):
            xs, ys, o = I.mk(task, rng, n); ok += I.run(prog, xs, ys) == o
        out.append(f'{n}:{ok/2:.0f}%')
    return ' '.join(out)
def run_set(tasks, maxs, lib, label):
    I._CACHE.clear(); gc.collect()
    t0 = time.time(); bank = I.build(maxs, lib=lib); nb = sum(len(v) for v in bank.values()); tb = time.time() - t0
    print(f'[{label}] bank size<={maxs} lib={list(lib)}: {nb} exprs, built {tb:.1f}s', flush=True)
    sols = {}
    for t in tasks:
        t1 = time.time(); best = I.search(tr(t), bank, maxs); dt = time.time() - t1
        if not best: print(f'  {t:8s} NOT FOUND {dt:.0f}s', flush=True); continue
        print(f'  {t:8s} f={best[2][0]} g={best[2][1]} cost={best[0]} {dt:.0f}s  {ev(t, best[1])}', flush=True)
        sols[t] = best[2]
    return sols
if __name__ == '__main__':
    import sys
    NEW = ['mul1', 'addmod']
    sols = run_set(['inc', 'add', 'sub'], 7, (), 'raw7 base')
    cnt = collections.Counter()
    for t, (f, g) in sols.items():
        for prog in (f, g):
            for m in re.finditer(r'(%|//)(\d+)\)', prog): cnt[(m.group(1), m.group(2))] += 1
    print('mined pattern counts (op,const):', dict(cnt))
    lib = tuple(p for p, c in cnt.items() if c >= 2) or tuple(cnt)
    print('library adopted:', lib)
    run_set(NEW, 5, (), 'raw5 (no library)')
    run_set(NEW + ['add', 'sub'], 5, lib, 'lib5')
