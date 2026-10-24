"""B-514 (F-5): Soft (2^-len explanation weighting, text2prog8) vs TwoStep (categorical Occam, text2prog2),
same rows, same protocol; ambiguity-subset analysis. LEDGER pre-reg 2026-10-24."""
import random, json
from collections import defaultdict
from text2prog2 import *
from text2prog2 import TwoStep, splits, run2, run_hyp, numbers_of, HYP, H2, two_step
from text2prog8 import Soft

def explanations(text, ans):
    toks = text.split(); one = two = 0
    for h1 in HYP:
        if run_hyp(h1, numbers_of(text)) == ans: one += 1
    for k in splits(toks):
        L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
        for h1 in HYP:
            for h2 in H2:
                if run2(h1, h2, L_, R_) == ans: two += 1
    return one, two

for sd in range(5):
    rng = random.Random(sd)
    train = [(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(1000))]
    M_soft = Soft(); M_soft.fit(train)
    M_cat = TwoStep(); M_cat.fit(train)
    out = {'seed': sd}
    for nm, wh in (('same', 0), ('new', 1)):
        r = random.Random(100 + sd)
        ok = {'soft': 0, 'cat': 0}; amb = {'soft': 0, 'cat': 0, 'n': 0}
        for _ in range(300):
            _, t, a, _ = two_step(r, wh, True)
            try: ok['soft'] += M_soft.solve(t)[0] == a
            except Exception: pass
            try: ok['cat'] += M_cat.solve(t)[0] == a
            except Exception: pass
            one, two = explanations(t, a)
            if one and two:
                amb['n'] += 1
                try: amb['soft'] += M_soft.solve(t)[0] == a
                except Exception: pass
                try: amb['cat'] += M_cat.solve(t)[0] == a
                except Exception: pass
        out[nm] = {'soft': round(ok['soft'] / 300, 4), 'cat': round(ok['cat'] / 300, 4)}
        out[nm + '_amb'] = {'n': amb['n'], 'soft': round(amb['soft'] / max(amb['n'], 1), 4),
                            'cat': round(amb['cat'] / max(amb['n'], 1), 4)}
    print(json.dumps(out), flush=True)
print('DONE', flush=True)
