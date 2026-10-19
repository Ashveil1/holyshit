"""P18: EM reweighting of two-step explanations (uses the P16 TwoStep model as init)."""
import sys, math, random
from collections import defaultdict
from text2prog2 import *
from text2prog2 import TwoStep, splits, run2, run_hyp, numbers_of, feats, HYP, H2, two_step
class EM(TwoStep):
    def fit_em(s, rows, iters=2):
        s.fit(rows)
        for _ in range(iters):
            old = s
            n = TwoStep(); n.nsent = 0
            for text, ans in rows:
                toks = text.split(); E = []
                for h1 in HYP:
                    if run_hyp(h1, numbers_of(text)) == ans:
                        E.append(((None, h1, None), old.bnd['__single__'][0] and math.log((old.bnd['__single__'][0] + 1) / (old.nsent + 2)) + old._lik(old.A, text, h1)))
                for k in splits(toks):
                    L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                    b = old.bnd[(toks[k - 1], toks[k])]; pb = (b[0] + 0.01) / (b[1] + 1.0)
                    for h1 in HYP:
                        for h2 in H2:
                            if run2(h1, h2, L_, R_) == ans:
                                E.append(((k, h1, h2), math.log(pb) + old._lik(old.A, L_, h1) + old._lik2(old.B, R_, h2)))
                if any(e[0][0] is None for e in E): E = [e for e in E if e[0][0] is None]
                if not E: continue
                m = max(sc for _, sc in E); ws = [math.exp(sc - m) for _, sc in E]; z = sum(ws)
                for ((k, h1, h2), _), w in zip(E, ws):
                    w /= z
                    if k is None:
                        for f in feats(text, 'tok'): n.A.tot[f] += w; n.A.cnt[f][h1] += w
                    else:
                        L_, R_ = ' '.join(toks[:k]), ' '.join(toks[k:])
                        for f in feats(L_, 'tok'): n.A.tot[f] += w; n.A.cnt[f][h1] += w
                        for f in feats(R_, 'tok'): n.B.tot[f] += w; n.B.cnt[f][h2] += w
                        n.bnd[(toks[k - 1], toks[k])][0] += w
                    if k is None: n.bnd['__single__'][0] += w
                for k in splits(toks): n.bnd[(toks[k - 1], toks[k])][1] += 1
            n.nsent = len(rows); s.A, s.B, s.bnd, s.nsent = n.A, n.B, n.bnd, n.nsent
def main():
    for n in (100, 300):
        res = defaultdict(list)
        for it in (0, 1, 2):
            for sd in range(5):
                rng = random.Random(sd); rows = [(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(n))]
                M = EM(); M.fit_em(rows, it); r = random.Random(100 + sd)
                for nm, wh in (('same', 0), ('new', 1)):
                    ok = 0
                    for _ in range(300):
                        _, t, a, _ = two_step(r, wh, True)
                        try: ok += M.solve(t)[0] == a
                        except Exception: pass
                    res[(it, nm)].append(ok / 300)
        for k, v in sorted(res.items()): print(f'n={n} EM iters={k[0]} {k[1]}: {sum(v)/5:.2f}', flush=True)
if __name__ == '__main__': main()
