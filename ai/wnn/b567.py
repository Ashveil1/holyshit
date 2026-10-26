"""B-567: discriminative feature weighting for the intent mapper.
Pre-registered in LEDGER.md (B-567) BEFORE this code - final bounded round.
M0 = NBu (frozen baseline). M1 = NBu x per-feature w(f)=ln(1+8/df(f)),
df = #distinct train intents containing f. Extractor FROZEN: S4 selection +
positional assignment (B-566). Raw-argmax protocol; abstention separate.
All evals INSPECTED development comparisons. Usage: python3 b567.py
"""
import json, math
from collections import defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0

class NBw(NBu):  # M1: discriminative-weighted NBu
    def fit_weights(self, train):
        df = defaultdict(set)
        for s, d, _, _ in train:
            for f in B.encode(s): df[f].add(d)
        self.w = {f: math.log(1 + 8.0 / len(ds)) for f, ds in df.items()}
    def scores(self, feats):
        V = 50000; out = {}
        for d in self.intents:
            s = 0.0
            den = self.tot[d] + self.a * V
            for f, c in feats.items():
                s += self.w.get(f, math.log(9.0)) * c * math.log((self.fc[d][f] + self.a) / den)
            out[d] = s
        return out

if __name__ == '__main__':
    for seed in [0, 1, 2, 3, 4]:
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        newtmpl = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
        fresh3 = [it for d in B.INTENTS for it in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        fn, anchor, offstat, rolepos = learn_s4(train)
        extract = lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d])
        m0 = NBu(B.INTENTS)
        m1 = NBw(B.INTENTS); m1.fit_weights(train)
        for s, d, _, _ in train: m0.add(B.encode(s), d); m1.add(B.encode(s), d)
        for aname, m in (('M0_NBu', m0), ('M1_weighted', m1)):
            for ename, eset in (('frozen_INSPECTED', ev), ('newtmpl_INSPECTED1', newtmpl), ('fresh3_INSPECTED', fresh3)):
                ni = nc = jn = wrong = 0; slot_exact = 0; abstain_gated = 0
                # dev-frozen gate recomputed per arm (gate belongs to the mapper)
                cands_t = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]})
                best_t, best_r = -1e18, -1
                for t in cands_t:
                    ok = 0
                    for s, d, _, _ in dev:
                        p, mg = B.predict(m, B.encode(s), -1e18)
                        p = p if mg >= t else None
                        ok += (p == d) if d != 'NONE' else (p is None)
                    if ok / len(dev) > best_r: best_r, best_t = ok / len(dev), t
                for s, d, gold, _ in eset:
                    p, mg = B.predict(m, B.encode(s), -1e18)
                    if mg < best_t: abstain_gated += 1
                    ni += 1
                    if p == d:
                        nc += 1
                        ps = extract(s, d)
                        if ps == tuple(gold): slot_exact += 1; jn += 1
                    else: wrong += 1
                print('ROW ' + json.dumps({'seed': seed, 'arm': aname, 'eval': ename,
                    'intent': round(nc / ni, 3), 'slot_exact_on_correct': round(slot_exact / max(nc, 1), 3),
                    'joint': round(jn / ni, 3), 'wrong_action': wrong,
                    'abstain_gated_SEPARATE': abstain_gated, 'n': ni}, ensure_ascii=False))
    print('DONE')
