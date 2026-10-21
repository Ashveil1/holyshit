"""T3 min-count ablation (B-111..128): drop features with document frequency < k at n=150.
Default (min-count 1) = P15 default. 2-step cells (B-113/116/119/122/125/128) are not run:
the P15 learner has no two-step capability (that is P16/text2prog2.py's task)."""
import random
from collections import defaultdict
import text2prog as T
class MCLearner(T.Learner):
    def __init__(s, kind, soft=True, mc=1):
        super().__init__(kind, soft); s.mc = mc
    def fit(s, data):
        df = defaultdict(int)
        for text, _ in data:
            for f in T.feats(text, s.kind): df[f] += 1
        keep = {f for f, c in df.items() if c >= s.mc}
        orig = T.feats
        T.feats = lambda text, kind: orig(text, kind) & keep
        try: super().fit(data)
        finally: T.feats = orig
def cell(kind, mc, n=150):
    sc = defaultdict(list)
    for sd in range(5):
        rng = random.Random(sd)
        L = MCLearner(kind, mc=mc); L.fit([(t, a) for _, t, a in T.gen_set(rng, 0, n)])
        r = random.Random(100 + sd)
        for nm, wh in (('numbers', 0), ('frames', 1), ('synonyms', 2)):
            sc[nm].append(T.evaluate(L, T.gen_set(r, wh, 300, big=True))[0])
    return {k: sum(v) / len(v) for k, v in sc.items()}
if __name__ == '__main__':
    for kind in ('tok', 'tokuni'):
        for mc in (2, 4):
            r = cell(kind, mc)
            print(f'{kind:7s} mc={mc} n=150 frames {r["frames"]:.2f} synonyms {r["synonyms"]:.2f}', flush=True)
