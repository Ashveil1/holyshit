"""B-566: is role assignment LEARNED better than POSITIONAL? (pre-registered in
LEDGER.md BEFORE this code). Bounded: from the B-565 error taxonomy (role
swaps on unfamiliar fillers dominate). Frozen mapper (S1 NBu), frozen evals,
raw-argmax protocol (labeled; abstention separate, never mixed).
ALL THREE eval sets are INSPECTED development comparisons, not held-out
validation; no production route is chosen on them alone.
Arms (train-only statistics; candidate SELECTION identical = S4's):
  A0 positional: roles assigned by surface order (zero learning).
  A1 pooled role-position stats (current S4 assignment).
  A2 per-intent role-position stats + positional fallback for unseen fillers.
Gates (fixed before code): G1 A2 mean joint >= A0 + 3pts on newtmpl AND
fresh3 with >=4/5 per-seed deltas non-negative vs A0; G2 frozen mean joint
not worse than A0 by >3pts. A2~=A0 -> honest null, keep the simpler arm.
Usage: python3 b566.py
"""
import json
from collections import Counter, defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, extract_s4, FRESH3_FAM, EVAL_VOCAB2

def learn_s4_perintent(train):
    """A2's role table: rolepos keyed PER INTENT (train only)."""
    by = defaultdict(list)
    for s, d, _, _ in train: by[d].append(s)
    frame1 = {}
    for d, ss in by.items():
        c = Counter(w for s in ss for w in set(s.split()))
        frame1[d] = {w for w, n in c.items() if n >= max(1, 0.5 * len(ss))}
    rolepos_pi = defaultdict(lambda: defaultdict(Counter))
    for d, ss in by.items():
        anchor_w = Counter(w for s in ss for w in s.split()).most_common(1)[0][0]
        for s in ss:
            sp = 0
            for w in s.split():
                if w not in frame1[d] and w != anchor_w:
                    rolepos_pi[d][w][sp] += 1; sp += 1
    return rolepos_pi

def _select(s, d, functionish, anchor, offstat, nslots):
    """S4 candidate selection, unchanged; returns (picked_in_rank_order, toks)."""
    toks = s.split()
    ap = toks.index(anchor[d]) if anchor[d] in toks else None
    cands = []
    for i, w in enumerate(toks):
        if w in functionish or w == anchor[d]: continue
        off = (i - ap) if ap is not None else None
        lik = offstat[d].get(off, 0) if off is not None else 0
        cands.append((lik, i, w))
    cands.sort(key=lambda t: (-t[0], t[1]))
    return [w for _, _, w in cands[:nslots]], toks

def assign_a0(picked, toks, nslots):
    """Surface order."""
    order = {w: i for i, w in enumerate(toks)}
    return tuple(sorted(picked, key=lambda w: order[w])[:nslots]) if len(picked) >= nslots else None

def assign_a2(picked, toks, rolepos_pi, d, nslots):
    """Per-intent stats; unseen fillers fall back to surface order."""
    if len(picked) < nslots: return None
    assigned = [None] * nslots; claimed = set()
    for w in picked:
        rp = rolepos_pi.get(d, {}).get(w)
        if rp:
            p = rp.most_common(1)[0][0]
            if p < nslots and assigned[p] is None:
                assigned[p] = w; claimed.add(w)
    order = {w: i for i, w in enumerate(toks)}
    leftover = sorted((w for w in picked if w not in claimed), key=lambda w: order[w])
    li = 0
    for p in range(nslots):
        if assigned[p] is None:
            assigned[p] = leftover[li] if li < len(leftover) else None; li += 1
    return tuple(assigned)

if __name__ == '__main__':
    for seed in [0, 1, 2, 3, 4]:
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        newtmpl = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
        fresh3 = [it for d in B.INTENTS for it in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        m = NBu(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        cands_t = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]})
        best_t, best_r = -1e18, -1
        for t in cands_t:
            ok = 0
            for s, d, _, _ in dev:
                p, mg = B.predict(m, B.encode(s), -1e18)
                p = p if mg >= t else None
                ok += (p == d) if d != 'NONE' else (p is None)
            if ok / len(dev) > best_r: best_r, best_t = ok / len(dev), t
        fn, anchor, offstat, rolepos = learn_s4(train)
        rolepos_pi = learn_s4_perintent(train)
        arms = {
            'A0_positional': lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d]),
            'A1_pooled_S4':  lambda s, d: extract_s4(s, d, fn, anchor, offstat, rolepos, B.NSLOTS[d]),
            'A2_perintent':  lambda s, d: assign_a2(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), rolepos_pi, d, B.NSLOTS[d]),
        }
        for aname, extract in arms.items():
            for ename, eset in (('frozen_INSPECTED', ev), ('newtmpl_INSPECTED1', newtmpl), ('fresh3_INSPECTED', fresh3)):
                ni = nc = jn = wrong = 0; slot_exact = 0; abstain_gated = 0; swaps = 0
                for s, d, gold, _ in eset:
                    p, mg = B.predict(m, B.encode(s), -1e18)
                    if mg < best_t: abstain_gated += 1
                    ni += 1
                    if p == d:
                        nc += 1
                        ps = extract(s, d)
                        if ps == tuple(gold): slot_exact += 1; jn += 1
                        elif ps is not None and set(ps) == set(gold): swaps += 1
                    else: wrong += 1
                print('ROW ' + json.dumps({'seed': seed, 'arm': aname, 'eval': ename,
                    'intent': round(nc / ni, 3), 'slot_exact_on_correct': round(slot_exact / max(nc, 1), 3),
                    'joint': round(jn / ni, 3), 'role_swaps': swaps, 'wrong_action': wrong,
                    'abstain_gated_SEPARATE': abstain_gated, 'n': ni}, ensure_ascii=False))
    print('DONE')
