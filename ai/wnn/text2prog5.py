"""P21: three-step sentences. A TwoStep model (P16) is trained ONLY on 1- and 2-step sentences; the solver then
chains it: left clause (op1) + clause 2 (op2 on result) + clause 3 (op3 on result). No 3-step training sentence is used.
python3 text2prog5.py"""
import sys, random, math
from collections import defaultdict
from text2prog2 import *
from text2prog2 import TwoStep, splits, run2, run_hyp, numbers_of, two_step, C1, C2, CONN, H2
import text2prog as P
def three_step(rng, which):
    for _ in range(100):
        o1 = rng.choice(list(C1)); o2 = rng.choice(list(C2)); o3 = rng.choice(list(C2))
        t1, r = P.make(o1, rng.choice(C1[o1][0 if which == 0 else which]), rng, big=False)
        parts = [t1]; ops = [o1]; ok = True
        for o in (o2, o3):
            c = rng.randrange(2, 12)
            tm = rng.choice(C2[o][0 if which == 0 else 1]); parts.append(rng.choice(CONN[0 if which == 0 else 1]) + ' ' + tm.format(c=c))
            if o == 'add': r = r + c
            elif o == 'sub': r = r - c
            elif o == 'mul': r = r * c
            elif o == 'div': r = r // c
            elif o == 'fact':
                if r < 0 or r > 8: ok = False; break
                r = math.factorial(r)
            else: r = int(P.isp(r))
            if abs(r) > 10 ** 7: ok = False; break
            ops.append(o)
        if ok: return tuple(ops), ' '.join(parts), int(r)
    return three_step(rng, which)
def solve3(M, text):
    toks = text.split(); best = (None, -1e18)
    ks = splits(toks)
    for k1 in ks:
        for k2 in range(k1 + 1, len(toks)):
            if not any(ch.isdigit() for t in toks[k1:k2] for ch in t) and True:
                pass
            L_, R1, R2 = ' '.join(toks[:k1]), ' '.join(toks[k1:k2]), ' '.join(toks[k2:])
            h1, _ = M.A.predict(L_); h2 = M._pred(M.B, R1, H2); h3 = M._pred(M.B, R2, H2)
            b1 = M.bnd[(toks[k1 - 1], toks[k1])]; b2 = M.bnd[(toks[k2 - 1], toks[k2])]
            sc = math.log((b1[0] + .01) / (b1[1] + 1)) + math.log((b2[0] + .01) / (b2[1] + 1)) + M._lik(M.A, L_, h1) + M._lik2(M.B, R1, h2) + M._lik2(M.B, R2, h3)
            if sc > best[1]: best = ((k1, k2, h1, h2, h3), sc)
    if best[0] is None: return None, None
    k1, k2, h1, h2, h3 = best[0]
    r1 = run_hyp(h1, numbers_of(' '.join(toks[:k1])))
    if r1 is None: return None, best[0]
    for h, cl in ((h2, ' '.join(toks[k1:k2])), (h3, ' '.join(toks[k2:]))):
        r1 = run2(None, h, str(r1), cl) if False else _step(r1, h, cl)
        if r1 is None: return None, best[0]
    return r1, best[0]
def _step(r1, h2, right):
    op, d = h2; nr = numbers_of(right)
    try:
        if op in ('fact', 'isprime'): return int(OPS[op](r1))
        if len(nr) != 1: return None
        a, b = (r1, nr[0]) if d == 'f' else (nr[0], r1)
        return int(OPS[op](a, b))
    except Exception: return None
def main():
    for n in (300, 1000):
        res = defaultdict(list)
        for sd in range(5):
            rng = random.Random(sd); M = TwoStep(); M.fit([(t, a) for _, t, a, _ in (two_step(rng, 0, False) for _ in range(n))])
            r = random.Random(100 + sd)
            for nm, wh in (('same phrasing', 0), ('new connectors+frames', 1)):
                ok = 0; ops_ok = 0
                for _ in range(200):
                    o, t, a = three_step(r, wh)
                    try: pred, cfg = solve3(M, t)
                    except Exception: pred = None
                    ok += pred == a
                res[nm].append(ok / 200)
            # reference: 2-step accuracy of the same model
            ok = 0
            for _ in range(200):
                _, t, a, _ = two_step(r, 0, True)
                try: ok += M.solve(t)[0] == a
                except Exception: pass
            res['(ref) 2-step same phrasing'].append(ok / 200)
        print(f'n={n}: ' + ' | '.join(f'{k} {sum(v)/5:.2f} [{min(v):.2f}-{max(v):.2f}]' for k, v in res.items()), flush=True)
if __name__ == '__main__': main()
