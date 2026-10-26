"""P23: fewer examples for a new wording. At k=1 paraphrase definition, the pseudo label is right ~91% but accuracy is
only ~75: the new sentence's unseen tokens carry no learned weight. Try ALIGNMENT weight transfer: content tokens that
appear on the new side but not the known side inherit the op-weights of content tokens on the known side but not the
new side (and vice versa is not needed). Compare: para (P22), para+align, and true answer, at k=1 and k=2.
python3 text2prog7.py"""
import random, re
from collections import defaultdict
import text2prog as P
from text2prog import T, make, Learner, gen_set, feats
from text2prog6 import make_pair
def content_tokens(text):
    return [w for w in re.sub(r'\d+', ' ', text.lower()).split() if len(w) > 1]
def align_transfer(L, new, known):
    nt = [w for w in content_tokens(new) if w not in L.tot and w not in content_tokens(known)]
    kt = [w for w in content_tokens(known) if w in L.tot and w not in content_tokens(new)]
    if not nt or not kt: return 0
    moved = 0
    for wn in nt:
        for wk in kt:
            if wk in L.tot and L.tot[wk] > 0:
                for h, c in L.cnt[wk].items(): L.cnt[wn][h] += c / len(kt)
                L.tot[wn] += L.tot[wk] / len(kt)
        moved += 1
    return moved
def margin(L, text):
    import math
    from text2prog import HYP, feats
    fs = [f for f in feats(text, L.kind) if f in L.tot]; sc = []
    for h in HYP:
        sc.append(sum(math.log((L.cnt[f].get(h, 0) + 0.05) / (L.tot[f] + 0.05 * len(HYP))) for f in fs))
    sc.sort(reverse=True); return sc[0] - sc[1] if len(sc) > 1 else 0
def run(kind, seed, ks=(1, 2), n_train=300, mode='para'):
    res = {k: [] for k in ks}
    for op in T:
        for tm in T[op][2]:
            for k in ks:
                rng = random.Random(seed)
                L = Learner(kind); L.fit([(t, a) for _, t, a in gen_set(rng, 0, n_train)])
                for _ in range(k):
                    tmk = rng.choice(T[op][0]); new, known, a1, a2 = make_pair(op, tm, rng, tmk)
                    if mode == 'answer': L.fit([(new, a1)])
                    else:
                        try: pseudo = L.answer(known)[0]
                        except Exception: pseudo = None
                        if mode == 'para+conf' and margin(L, known) < 2.0: pseudo = None
                        if pseudo is not None: L.fit([(new, pseudo)])
                        if mode in ('para+align', 'para+conf'): align_transfer(L, new, known)
                r = random.Random(500 + seed); ok = 0
                for _ in range(40):
                    text, ans = make(op, tm, r, big=True)
                    try: ok += L.answer(text)[0] == ans
                    except Exception: pass
                res[k].append(ok / 40)
    return {k: sum(v) / len(v) for k, v in res.items()}
if __name__ == '__main__':
    for kind in ('tok', 'char'):
        for mode in ('answer', 'para', 'para+align', 'para+conf'):
            out = [run(kind, sd, mode=mode) for sd in range(3)]
            acc = {k: round(sum(o[k] for o in out) / 3, 2) for k in out[0]}
            print(f'{kind:5s} {mode:11s} new-wording accuracy after k examples: {acc}', flush=True)
