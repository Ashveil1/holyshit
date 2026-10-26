"""P22: teaching a new wording by PARAPHRASE instead of by answer.
Definition: "<new-wording sentence with numbers> means <known-wording sentence with the same numbers>".
The learner reads the known-wording side with what it already knows (its own answer = a pseudo label) and fits the
new-wording side to that pseudo label. No ground-truth answer is given for the new wording. Compared with P15 fast mapping
(k labelled answers), and with nothing (k=0).
GIVEN: the split of a definition at the connective 'means' (hand-split), the known-wording side, templates (own synthetic text).
python3 text2prog6.py"""
import random
from collections import defaultdict
import text2prog as P
from text2prog import T, make, Learner, gen_set, evaluate

def make_pair(op, tm_new, rng, tm_known):
    """same drawn numbers rendered with a new-wording template and a known-wording template"""
    st = rng.getstate(); new, a1 = make(op, tm_new, rng); rng.setstate(st); known, a2 = make(op, tm_known, rng)
    return new, known, a1, a2
def run(kind, seed, ks=(0, 1, 2, 4, 8), n_train=300, mode='para'):
    res = {k: [] for k in ks}; pl_ok = {k: [] for k in ks}
    for op in T:
        for tm in T[op][2]:
            for k in ks:
                rng = random.Random(seed)
                L = Learner(kind); L.fit([(t, a) for _, t, a in gen_set(rng, 0, n_train)])
                good = 0
                for _ in range(k):
                    tmk = rng.choice(T[op][0]); new, known, a1, a2 = make_pair(op, tm, rng, tmk)
                    if mode == 'para':
                        try: pseudo = L.answer(known)[0]
                        except Exception: pseudo = None
                        good += pseudo == a1
                        if pseudo is not None: L.fit([(new, pseudo)])
                    else: L.fit([(new, a1)])
                if k: pl_ok[k].append(good / k)
                r = random.Random(500 + seed); ok = 0
                for _ in range(40):
                    text, ans = make(op, tm, r, big=True)
                    try: ok += L.answer(text)[0] == ans
                    except Exception: pass
                res[k].append(ok / 40)
    return {k: sum(v) / len(v) for k, v in res.items()}, {k: sum(v) / len(v) for k, v in pl_ok.items() if v}
if __name__ == '__main__':
    for kind in ('tok', 'char'):
        for mode in ('answer', 'para'):
            out = [run(kind, sd, mode=mode) for sd in range(3)]
            acc = {k: round(sum(o[0][k] for o in out) / 3, 2) for k in out[0][0]}
            extra = {k: round(sum(o[1][k] for o in out) / 3, 2) for k in out[0][1]} if mode == 'para' else ''
            print(f'{kind:5s} {mode:6s} accuracy on the new wording after k examples: {acc}' + (f' | pseudo-label correct: {extra}' if extra else ''), flush=True)
