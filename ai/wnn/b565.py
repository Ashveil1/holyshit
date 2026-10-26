"""B-565: template-robust slot extraction (S4) vs B-564's pooled extractor (S3).
Pre-registered in LEDGER.md (B-565) BEFORE this code. Mapper FROZEN = S1
(uniform-prior NB). ONE protocol: raw argmax (labeled; abstention reported
separately via the dev-frozen gate, never mixed into accuracy).
Eval sets: FROZEN (b562, INSPECTED - reference only), NEWTMPL (b564's,
inspected once), FRESH3 (authored for this round + unfamiliar entity set #2).
Usage: python3 b565.py
"""
import json, math
from collections import Counter, defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM

FRESH3_FAM = {  # authored THIS round, never measured before
 'teach_attr': [lambda x, y: f'{x} มี {y} อยู่นะ', lambda x, y: f'{x} also has {y}'],
 'ask_attr': [lambda x, y: f'{y} ของ {x} คืออะไร รู้ไหม', lambda x, y: f'do you know the {y} of {x}'],
 'retract_attr': [lambda x, y: f'{x} ไม่มี {y} หรอก', lambda x, y: f'{x} does not really have {y}'],
 'teach_isa': [lambda x, y: f'{x} มัน เป็น {y}', lambda x, y: f'{x} is actually a {y}'],
 'is_a_q': [lambda x, y: f'{x} เป็น {y} ใช่ไหม', lambda x, y: f'is it true that {x} is a {y}'],
 'name_skill': [lambda x, y: f'ขอ {x}', lambda x, y: f'{x} หน่อย'],
 'give_example': [lambda x, y: f'เมื่อ n เป็น {x} แล้วตอบ {y}', lambda x, y: f'given n is {x} then answer {y}'],
 'confirm_answer': [lambda x, y: f'ตอบ {x} ไปเลย', lambda x, y: f'please answer {x}'],
}
EVAL_VOCAB2 = {  # unfamiliar entity set #2 (never in training, never in prior evals)
 'teach_attr': (['ม้า', 'ควาย', 'เป็ด', 'horse', 'duck'], ['ขน', 'จงอย่าง', 'ปาก', 'feather', 'beak']),
 'ask_attr': (['ม้า', 'ควาย', 'เป็ด', 'horse', 'duck'], ['ขน', 'จงอย่าง', 'ปาก', 'feather', 'beak']),
 'retract_attr': (['ม้า', 'ควาย', 'เป็ด'], ['ขน', 'จงอย่าง', 'ปาก']),
 'teach_isa': (['ม้า', 'ควาย', 'เป็ด', 'horse'], ['สัตว์ป่า', 'นกน้ำ', 'wild', 'waterfowl']),
 'is_a_q': (['ม้า', 'ควาย', 'เป็ด', 'horse'], ['สัตว์ป่า', 'นกน้ำ', 'wild', 'waterfowl']),
 'name_skill': (['แบ่ง', 'ลด'], [None]),
 'give_example': (['สิบ', 'แปด', 'eight'], ['เก้า', 'เจ็ด', 'nine']),
 'confirm_answer': (['เก้า', 'เจ็ด', 'nine'], [None]),
}

def learn_s4(train):
    by = defaultdict(list)
    for s, d, _, _ in train: by[d].append(s)
    # per-intent frame words (v1 rule) -> identify TRAIN slots
    frame1 = {}
    for d, ss in by.items():
        c = Counter(w for s in ss for w in set(s.split()))
        frame1[d] = {w for w, n in c.items() if n >= max(1, 0.5 * len(ss))}
    # function-ness: token in >=2 distinct intents' examples
    tok_intents = defaultdict(set)
    for d, ss in by.items():
        for s in ss:
            for w in set(s.split()): tok_intents[w].add(d)
    functionish = {w for w, ds in tok_intents.items() if len(ds) >= 2}
    # anchor per intent = its most frequent token; slot offset stats relative to anchor
    anchor, offstat, rolepos = {}, defaultdict(Counter), defaultdict(Counter)
    for d, ss in by.items():
        c = Counter(w for s in ss for w in s.split())
        anchor[d] = c.most_common(1)[0][0]
        for s in ss:
            toks = s.split()
            if anchor[d] not in toks: continue
            ap = toks.index(anchor[d])
            for i, w in enumerate(toks):
                if w not in frame1[d] and w != anchor[d]:
                    offstat[d][i - ap] += 1
            sp = 0
            for i, w in enumerate(toks):
                if w not in frame1[d] and w != anchor[d]:
                    rolepos[w][sp] += 1; sp += 1
    return functionish, anchor, offstat, rolepos

def extract_s4(s, d, functionish, anchor, offstat, rolepos, nslots):
    toks = s.split()
    ap = toks.index(anchor[d]) if anchor[d] in toks else None
    cands = []
    for i, w in enumerate(toks):
        if w in functionish or w == anchor[d]: continue
        off = (i - ap) if ap is not None else None
        lik = offstat[d].get(off, 0) if off is not None else 0
        cands.append((lik, i, w))
    cands.sort(key=lambda t: (-t[0], t[1]))
    picked = [w for _, _, w in cands[:nslots]]
    if len(picked) < nslots: return None
    assigned = [None] * nslots; claimed = set()
    for w in picked:
        rp = rolepos.get(w)
        if rp:
            p = rp.most_common(1)[0][0]
            if p < nslots and assigned[p] is None:
                assigned[p] = w; claimed.add(w)
    leftover = [w for w in picked if w not in claimed]
    li = 0
    for p in range(nslots):
        if assigned[p] is None:
            assigned[p] = leftover[li] if li < len(leftover) else picked[p]; li += 1
    return tuple(assigned)

from b564 import learn_slots_v2, extract_v2

if __name__ == '__main__':
    for seed in [0, 1, 2, 3, 4]:
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        newtmpl = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
        fresh3 = [it for d in B.INTENTS for it in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        m = NBu(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        # dev-frozen gate (reported separately, never mixed into accuracy)
        cands_t = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]})
        best_t, best_r = -1e18, -1
        for t in cands_t:
            ok = 0
            for s, d, _, _ in dev:
                p, mg = B.predict(m, B.encode(s), -1e18)
                p = p if mg >= t else None
                ok += (p == d) if d != 'NONE' else (p is None)
            if ok / len(dev) > best_r: best_r, best_t = ok / len(dev), t
        frame_v2, pooled_v2 = learn_slots_v2(train)
        fn, anchor, offstat, rolepos = learn_s4(train)
        for name, extract in (('S3', lambda s, d: extract_v2(s, frame_v2, pooled_v2, B.NSLOTS[d])),
                              ('S4', lambda s, d: extract_s4(s, d, fn, anchor, offstat, rolepos, B.NSLOTS[d]))):
            for ename, eset in (('frozen_INSPECTED', ev), ('newtmpl_INSPECTED1', newtmpl), ('fresh3', fresh3)):
                ni = nc = jn = wrong = 0; slot_exact = 0; abstain_gated = 0
                for s, d, gold, _ in eset:
                    p, mg = B.predict(m, B.encode(s), -1e18)
                    if mg < best_t: abstain_gated += 1
                    ni += 1
                    if p == d:
                        nc += 1
                        ps = extract(s, d)
                        if ps == tuple(gold): slot_exact += 1; jn += 1
                    else: wrong += 1
                print('ROW ' + json.dumps({'seed': seed, 'extractor': name, 'eval': ename,
                    'intent': round(nc / ni, 3), 'slot_exact_on_correct': round(slot_exact / max(nc, 1), 3),
                    'joint': round(jn / ni, 3), 'wrong_action': wrong, 'abstain_gated_SEPARATE': abstain_gated,
                    'n': ni}, ensure_ascii=False))
    print('DONE')
