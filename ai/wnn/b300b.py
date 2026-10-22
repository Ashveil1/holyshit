"""B-300 exploratory arm (pre-stated here before running): the plurality implementation double-counts
commutative/direction-duplicate hypotheses (measured: k3 -23.8pts, k5 -38.9pts vs top1).
FAIR reading of 'execution agreement': marginalize hypothesis posterior over EXECUTION-EQUIVALENCE
classes - answer score = logsumexp of hypothesis scores producing that answer (within top-k and over
all 21 hyps); argmax over answers. Same protocol as b300.py otherwise. PASS criterion unchanged (+3pts)."""
import random, math, json
from collections import defaultdict
from text2prog import Learner, gen_set, HYP, run_hyp, numbers_of, feats

def scores(L, text):
    fs = [f for f in feats(text, L.kind) if f in L.tot]
    return {h: sum(math.log((L.cnt[f].get(h, 0) + 0.05) / (L.tot[f] + 0.05 * len(HYP))) for f in fs) for h in HYP}

def lse(xs):
    m = max(xs); return m + math.log(sum(math.exp(x - m) for x in xs))

def marg_answer(L, text, k):
    sc = scores(L, text)
    hyps = sorted(sc, key=sc.get, reverse=True)[:k] if k else list(sc)
    nums = numbers_of(text); agg = defaultdict(list)
    for h in hyps:
        try: agg[run_hyp(h, nums)].append(sc[h])
        except Exception: continue
    if not agg: return None
    return max(agg, key=lambda r: lse(agg[r]))

res = []
for seed in range(5):
    rng = random.Random(seed); tr = gen_set(rng, 0, 300)
    rng2 = random.Random(1000 + seed); te = gen_set(rng2, 1, 300)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in tr])
    acc = defaultdict(int)
    for op, text, ans in te:
        sc = scores(L, text); h1 = max(sc, key=sc.get)
        try: r1 = run_hyp(h1, numbers_of(text))
        except Exception: r1 = None
        acc['top1'] += r1 == ans
        for k in (3, 5, 0):
            acc[f'm{k}'] += marg_answer(L, text, k) == ans
    row = {'seed': seed, **{kk: round(vv / len(te), 4) for kk, vv in acc.items()}}
    res.append(row); print(json.dumps(row), flush=True)
m = {kk: sum(r[kk] for r in res) / len(res) for kk in ('top1', 'm3', 'm5', 'm0')}
print(json.dumps({'mean': {kk: round(vv, 4) for kk, vv in m.items()},
                  'gain_m3': round(100*(m['m3']-m['top1']),2), 'gain_m5': round(100*(m['m5']-m['top1']),2),
                  'gain_mall': round(100*(m['m0']-m['top1']),2)}), flush=True)
