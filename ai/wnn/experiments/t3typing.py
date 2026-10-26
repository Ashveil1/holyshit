"""B-185: typing - restrict fit candidates by arg-count signature before run_hyp.
UNARY ops need exactly 1 number; fixed-binary (sub/div/mod/power) need >=2; variadic (add/mul/gcd/...) need >=2.
Success: same accuracy, faster fit. Measures fit wall time + P15 acc spot-check (tok, n=150/400, 5 seeds)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import time, random
from text2prog import Learner, gen_set, evaluate, HYP, run_hyp, numbers_of, UNARY
FIXED2 = ('sub', 'div', 'mod', 'power')
def arity_ok(h, n):
    op = h[0]
    if op in UNARY: return n == 1
    return n >= 2
def fit_typed(L, data):
    for text, ans in data:
        nums = numbers_of(text); C = [h for h in HYP if arity_ok(h, len(nums)) and run_hyp(h, nums) == ans]
        if not C: continue
        w = 1.0 / len(C) if L.soft else 1.0
        from text2prog import feats
        for f in feats(text, L.kind):
            L.tot[f] += w
            for h in C: L.cnt[f][h] += w
        for h in C: L.prior[h] += w
def bench(fitfn, n):
    t0 = time.time(); accs = {}
    for sd in range(5):
        rng = random.Random(sd); L = Learner('tok')
        fitfn(L, [(t, a) for _, t, a in gen_set(rng, 0, n)])
        r = random.Random(100 + sd)
        for nm, wh in (('numbers', 0), ('frames', 1), ('synonyms', 2)): accs.setdefault(nm, []).append(evaluate(L, gen_set(r, wh, 300, big=True))[0])
    return time.time() - t0, {k: round(sum(v) / 5, 3) for k, v in accs.items()}
if __name__ == '__main__':
    for n in (150, 400):
        t0, a0 = bench(lambda L, d: Learner.fit(L, d), n)
        t1, a1 = bench(fit_typed, n)
        print(f'n={n}: default {t0:.1f}s {a0} | typed {t1:.1f}s {a1} | speedup {t0/t1:.2f}x', flush=True)
