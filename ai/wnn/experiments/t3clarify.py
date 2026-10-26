"""B-183: active clarification. When top-2 hypothesis scores are close (gap < DELTA), ask the
simulated user which reading was meant (1 question); user answers with the correct reading.
Baseline: no clarification (always top-1). Task: 1-step unseen frames+synonyms, tok, n=150, 5 seeds.
Success: clarify accuracy > top-1 accuracy."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import math, random
from collections import defaultdict
from text2prog import Learner, gen_set, HYP, run_hyp, feats, numbers_of
def top2(L, text):
    fs = [f for f in feats(text, L.kind) if f in L.tot]
    sc = []
    for h in HYP:
        s = 0.0
        for f in fs: s += math.log((L.cnt[f].get(h, 0) + 0.05) / (L.tot[f] + 0.05 * len(HYP)))
        sc.append((s, h))
    sc.sort(reverse=True)
    return sc[0], sc[1]
def run(delta, which, sd):
    rng = random.Random(sd)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 150)])
    r = random.Random(100 + sd); rows = gen_set(r, which, 300, big=True)
    base_ok = clar_ok = asked = asked_ok = 0
    for op, text, ans in rows:
        nums = numbers_of(text)
        (s1, h1), (s2, h2) = top2(L, text)
        base_ok += run_hyp(h1, nums) == ans
        if s1 - s2 < delta and h1 != h2:
            asked += 1
            good = [h for h in (h1, h2) if run_hyp(h, nums) == ans]
            h = good[0] if good else h1
        else:
            h = h1
        ok = run_hyp(h, nums) == ans; clar_ok += ok; asked_ok += ok if (s1 - s2 < delta and h1 != h2) else 0
    return base_ok / 300, clar_ok / 300, asked / 300
if __name__ == '__main__':
    for which, nm in ((1, 'frames'), (2, 'synonyms')):
        for delta in (0.5, 2.0):
            b, c, a = zip(*[run(delta, which, sd) for sd in range(5)])
            print(f'{nm:9s} delta={delta}: top1 {sum(b)/5:.3f} | clarify {sum(c)/5:.3f} | asked {sum(a)/5:.2f}', flush=True)
