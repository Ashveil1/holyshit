"""B-300 (pre-registered 2026-10-22): ensemble of learner hypotheses with EXECUTION AGREEMENT on text2prog.
Question: does voting the learner's top-k hypotheses (executed on the sentence's numbers, plurality
over answers) beat top-1 argmax on UNSEEN FRAMES? Voting can only fix example-dependent noise
(lexical ambiguity), not systematic errors (LEDGER B-279..298 line).
Protocol: kind='tok', soft counts; train gen_set(rng,0,300) (train frames); test gen_set(rng2,1,300)
(unseen new_frames templates). Seeds 0-4. Arms: top1; vote k=3; vote k=5 (plurality over executed
answers; tie -> larger summed hypothesis score mass -> top-1 answer; execution failures skip a vote).
PASS criterion (pre-stated): mean unseen-frame accuracy of best vote arm >= top1 + 3 points.
Ceiling caveat pre-stated: if top1 >= 97% the +3 criterion is unattainable -> report as ceiling-vacuous."""
import random, math, json
from collections import defaultdict
from text2prog import Learner, gen_set, HYP, run_hyp, numbers_of, feats

def scores(L, text):
    fs = [f for f in feats(text, L.kind) if f in L.tot]
    sc = {}
    for h in HYP:
        s = 0.0
        for f in fs: s += math.log((L.cnt[f].get(h, 0) + 0.05) / (L.tot[f] + 0.05 * len(HYP)))
        sc[h] = s
    return sc

def vote_answer(L, text, k):
    sc = scores(L, text)
    top = sorted(sc, key=sc.get, reverse=True)[:k]
    nums = numbers_of(text)
    agg = defaultdict(float); cnt = defaultdict(int)
    for h in top:
        try: r = run_hyp(h, nums)
        except Exception: continue
        agg[r] += sc[h]; cnt[r] += 1
    if not cnt: return None
    best_count = max(cnt.values())
    cands = [r for r in cnt if cnt[r] == best_count]
    return max(cands, key=lambda r: agg[r])

res = []
for seed in range(5):
    rng = random.Random(seed); tr = gen_set(rng, 0, 300)
    rng2 = random.Random(1000 + seed); te = gen_set(rng2, 1, 300)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in tr])
    acc = {'top1': 0, 'k3': 0, 'k5': 0}
    for op, text, ans in te:
        sc = scores(L, text); h1 = max(sc, key=sc.get)
        try: r1 = run_hyp(h1, numbers_of(text))
        except Exception: r1 = None
        acc['top1'] += r1 == ans
        for k in (3, 5):
            acc[f'k{k}'] += vote_answer(L, text, k) == ans
    row = {'seed': seed, **{kk: round(vv / len(te), 4) for kk, vv in acc.items()}}
    res.append(row); print(json.dumps(row), flush=True)
m = {kk: sum(r[kk] for r in res) / len(res) for kk in ('top1', 'k3', 'k5')}
print(json.dumps({'mean': {kk: round(vv, 4) for kk, vv in m.items()},
                  'gain_k3_pts': round(100 * (m['k3'] - m['top1']), 2),
                  'gain_k5_pts': round(100 * (m['k5'] - m['top1']), 2)}), flush=True)
