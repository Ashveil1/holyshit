"""B-511 (F-2): declarative advice "order does not matter for add and mul" prunes duplicate
commutative direction-hypotheses from P15's HYP. EXACT P15 protocol. LEDGER pre-reg 2026-10-24."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, json, re
from collections import defaultdict
import text2prog as P
from text2prog import Learner, gen_set, evaluate

ADVICE = "order does not matter for add and mul"
def parse_advice(s):
    """Stated minimal parser: 'order does not matter for <op> and <op>' -> ops to de-duplicate."""
    m = re.match(r"order does not matter for (\w+) and (\w+)$", s.strip())
    if not m: raise ValueError('unrecognized advice form')
    return set(m.groups())
ADVISED_OPS = parse_advice(ADVICE)
HYP_FULL = list(P.HYP)
HYP_ADV = [h for h in HYP_FULL if not (h[1] == 'r' and h[0] in ADVISED_OPS)]

def run_arm(hyp, n, sd):
    P.HYP = hyp
    rng = random.Random(sd)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, n)])
    r = random.Random(100 + sd)
    return {nm: evaluate(L, gen_set(r, wh, 300, big=True))[0] for nm, wh in (('numbers', 0), ('frames', 1), ('synonyms', 2))}

if __name__ == '__main__':
    for n in (24, 60, 150):
        for sd in range(5):
            full = run_arm(HYP_FULL, n, sd); adv = run_arm(HYP_ADV, n, sd)
            print(json.dumps({'n': n, 'seed': sd,
                              'full': {k: round(v, 4) for k, v in full.items()},
                              'advised': {k: round(v, 4) for k, v in adv.items()}}), flush=True)
    P.HYP = HYP_FULL
    print('DONE', flush=True)
