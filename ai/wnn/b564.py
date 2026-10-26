"""B-564: bounded fixes for the two B-563-diagnosed collateral channels + joint-slot leg.
Pre-registered in LEDGER.md (B-564) BEFORE this code. FROZEN: b562 data/eval via
b562_diag.build (identical rng), k=8, 3-correction protocol, same metrics.
Variants: S0=NB-full (frozen reference), S1=NB uniform-prior (channel 1),
S3=S1+pooled slot extraction. NEW-TEMPLATE eval reported separately (no bar).
No production integration. Usage: python3 b564.py
"""
import json, math
from collections import Counter, defaultdict
import b562 as B
from b562_diag import build

class NBu(B.NB):  # S1: uniform prior (likelihood-only)
    def scores(self, feats):
        V = 50000; out = {}
        for d in self.intents:
            s = 0.0
            den = self.tot[d] + self.a * V
            for f, c in feats.items():
                s += c * math.log((self.fc[d][f] + self.a) / den)
            out[d] = s
        return out

def learn_slots_v2(train):
    """v2: frame words = union over ALL intents of per-intent >=50% tokens;
    role position stats POOLED across intents (both still learned from train only)."""
    by = defaultdict(list)
    for s, d, slots, _ in train: by[d].append(s)
    union_frame = set(); pooled = defaultdict(Counter)
    for d, ss in by.items():
        c = Counter(w for s in ss for w in set(s.split()))
        thr = max(1, 0.5 * len(ss))
        union_frame |= {w for w, n in c.items() if n >= thr}
    for s, d, gold, _ in train:
        fr = {w for w, n in Counter(w for s2 in by[d] for w in set(s2.split())).items() if n >= max(1, 0.5 * len(by[d]))}
        toks = [w for w in s.split() if w not in fr]
        for pos, w in enumerate(toks): pooled[w][pos] += 1
    return union_frame, pooled

def extract_v2(s, union_frame, pooled, nslots):
    toks = [w for w in s.split() if w not in union_frame]
    if len(toks) < nslots: return None
    toks = toks[:nslots]
    assigned = [None] * nslots; claimed = set()
    for w in toks:
        rp = pooled.get(w)
        if rp:
            p = rp.most_common(1)[0][0]
            if p < nslots and assigned[p] is None:
                assigned[p] = w; claimed.add(w)
    leftover = [w for w in toks if w not in claimed]
    li = 0
    for p in range(nslots):
        if assigned[p] is None:
            assigned[p] = leftover[li] if li < len(leftover) else toks[p]; li += 1
    return tuple(assigned)

NEW_EVAL_FAM = {  # authored, first use; same unfamiliar vocab pools (template novelty isolated)
 'teach_attr': [lambda x, y: f'{x} ตัวนี้ มี {y} ด้วยนะ', lambda x, y: f'{x} comes with {y}'],
 'ask_attr': [lambda x, y: f'ช่วยบอกหน่อยว่า {y} ของ {x} คืออะไร', lambda x, y: f'tell me the {y} of {x}'],
 'retract_attr': [lambda x, y: f'ที่จริง {x} ไม่มี {y} นะ', lambda x, y: f'{x} actually does not have {y}'],
 'teach_isa': [lambda x, y: f'{x} ถือว่าเป็น {y}', lambda x, y: f'{x} counts as a {y}'],
 'is_a_q': [lambda x, y: f'อยากถามว่า {x} เป็น {y} ไหม', lambda x, y: f'could you tell me if {x} is a {y}'],
 'name_skill': [lambda x, y: f'อยากได้ {x}', lambda x, y: f'{x} ได้ไหม'],
 'give_example': [lambda x, y: f'ลอง n เป็น {x} แล้วตอบ {y}', lambda x, y: f'when n is {x} you answer {y}'],
 'confirm_answer': [lambda x, y: f'ขอตอบ {x} ไป', lambda x, y: f'just answer {x}'],
}

for seed in [0, 1, 2, 3, 4]:
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
    newev = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
    arms = {'S0': B.NB(B.INTENTS), 'S1': NBu(B.INTENTS), 'S3': NBu(B.INTENTS)}
    for s, d, _, _ in train:
        f = B.encode(s)
        for m in arms.values(): m.add(f, d)
    # dev-frozen abstention margins per variant (same selection rule as b562)
    def devtau(m):
        cands = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]})
        best_t, best_r = -1e18, -1
        for t in cands:
            ok = 0
            for s, d, _, _ in dev:
                p, mg = B.predict(m, B.encode(s), -1e18)
                p = p if mg >= t else None
                ok += (p == d) if d != 'NONE' else (p is None)
            if ok / len(dev) > best_r: best_r, best_t = ok / len(dev), t
        return best_t
    frame_v2, pooled_v2 = learn_slots_v2(train)
    frame_v1, rolepos_v1 = B.learn_slots(train)
    for name, m in arms.items():
        t = devtau(m)
        def predict(s): return B.predict(m, B.encode(s), -1e18)[0]
        # frozen eval: intent / slotF1 / joint
        ni = nc = 0; sf1 = 0.0; joint = 0
        for s, d, gold, _ in ev:
            p = predict(s); ni += 1
            if p == d:
                nc += 1
                ps = (extract_v2(s, frame_v2, pooled_v2, B.NSLOTS[p]) if name == 'S3'
                      else B.extract_slots(s, p, frame_v1, rolepos_v1, B.NSLOTS[p]))
                gs, qs = set(gold), set(ps or ())
                inter = len(gs & qs)
                sf1 += (2 * inter / (len(gs) + len(qs))) if gs or qs else 1.0
                if ps == tuple(gold): joint += 1
        # new-template eval (intent only; slots share the same mechanism, reported too)
        nn_ = ncn = 0; jointn = 0
        for s, d, gold, _ in newev:
            p = predict(s); nn_ += 1
            if p == d:
                ncn += 1
                ps = (extract_v2(s, frame_v2, pooled_v2, B.NSLOTS[p]) if name == 'S3'
                      else B.extract_slots(s, p, frame_v1, rolepos_v1, B.NSLOTS[p]))
                if ps == tuple(gold): jointn += 1
        # collateral, 3-correction protocol (frozen)
        mis = [(s, d) for s, d, _, _ in ev if predict(s) != d][:3]
        before = {d: sum(predict(s) == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
        for s, d in mis: m.add(B.encode(s), d)
        after = {d: sum(predict(s) == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
        corr = {d for _, d in mis}
        degr = {d: round(100 * max(0, before[d] - after[d]), 1) for d in B.INTENTS if d not in corr}
        print('ROW ' + json.dumps({'seed': seed, 'variant': name,
            'frozen': {'intent': round(nc / ni, 3), 'slotf1': round(sf1 / max(nc, 1), 3), 'joint': round(joint / ni, 3)},
            'newtmpl': {'intent': round(ncn / nn_, 3), 'joint': round(jointn / nn_, 3)},
            'degr_points': degr, 'mean_degr': round(sum(degr.values()) / max(len(degr), 1), 2),
            'name_skill_degr': degr.get('name_skill', 0)}, ensure_ascii=False))
print('DONE')
