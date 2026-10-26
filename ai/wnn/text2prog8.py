"""F-5: Solomonoff-flavored soft Occam. P16 TwoStep drops every 2-step explanation when a single-op one exists
(categorical Occam). F-5 keeps all explanations and weights each by 2^-(number of ops). Same protocol as P16 (b).
python3 text2prog8.py"""
import random, math
from collections import defaultdict
from text2prog2 import *
from text2prog2 import TwoStep, splits, run2, run_hyp, numbers_of, feats, HYP, H2, two_step
class Soft(TwoStep):
    def fit(s, rows):
        for text, ans in rows:
            toks = text.split(); E = []
            for h1 in HYP:
                if run_hyp(h1, numbers_of(text)) == ans: E.append((None, h1, None))
            for k in splits(toks):
                L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                for h1 in HYP:
                    for h2 in H2:
                        if run2(h1, h2, L_, R_) == ans: E.append((k, h1, h2))
            if not E: continue
            w0 = 1.0 / sum(0.5 if e[0] is None else 0.25 for e in E)
            for k, h1, h2 in E:
                w = w0 * (0.5 if k is None else 0.25)
                if k is None:
                    for f in feats(text, 'tok'): s.A.tot[f] += w; s.A.cnt[f][h1] += w
                else:
                    L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                    for f in feats(L_, 'tok'): s.A.tot[f] += w; s.A.cnt[f][h1] += w
                    for f in feats(R_, 'tok'): s.B.tot[f] += w; s.B.cnt[f][h2] += w
                    s.bnd[(toks[k - 1], toks[k])][0] += w
                if k is None: s.bnd['__single__'][0] += w
            for k in splits(toks): s.bnd[(toks[k - 1], toks[k])][1] += 1
        s.nsent = len(rows)
def main():
    for n in (1000,):
        res = defaultdict(list)
        for sd in range(5):
            rng = random.Random(sd); M = Soft(); M.fit([(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(n))])
            r = random.Random(100 + sd)
            for nm, wh in (('same', 0), ('new', 1)):
                ok = 0
                for _ in range(300):
                    _, t, a, _ = two_step(r, wh, True)
                    try: ok += M.solve(t)[0] == a
                    except Exception: pass
                res[nm].append(ok / 300)
        print(f'soft-Occam n={n}: ' + ' | '.join(f'{k} {sum(v)/5:.2f} [{min(v):.2f}-{max(v):.2f}]' for k, v in res.items()), flush=True)
if __name__ == '__main__': main()
