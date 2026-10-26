"""T3 grid (B-063..086): features {tok,char} x credit {soft,hard} x n {24,60,150,400} on unseen frames/synonyms.
Soft cells reproduce P15's published rows (verification); HARD credit is an unmeasured ablation.
Same code path as text2prog.py main: 5 seeds, evaluate on 300 big-number sentences per cell."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, sys
from collections import defaultdict
from text2prog import Learner, gen_set, evaluate
def cell(kind, soft, n):
    sc = defaultdict(list)
    for sd in range(5):
        rng = random.Random(sd)
        L = Learner(kind, soft=soft); L.fit([(t, a) for _, t, a in gen_set(rng, 0, n)])
        r = random.Random(100 + sd)
        for nm, wh in (('numbers', 0), ('frames', 1), ('synonyms', 2)):
            sc[nm].append(evaluate(L, gen_set(r, wh, 300, big=True))[0])
    return {k: sum(v) / len(v) for k, v in sc.items()}
if __name__ == '__main__':
    for kind in ('tok', 'char', 'tokuni'):
        for soft in (True, False):
            for n in (24, 60, 150, 400):
                r = cell(kind, soft, n)
                print(f'{kind:5s} {"soft" if soft else "hard"} n={n:4d} frames {r["frames"]:.2f} synonyms {r["synonyms"]:.2f}', flush=True)
