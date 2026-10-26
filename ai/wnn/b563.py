"""B-563: diagnosis-only - what drives B-562 correction collateral in online NB.
Pre-registered in LEDGER.md (B-563) BEFORE this code. FROZEN: same b562 data
(identical rng order), same k=8 NB state, same 3-correction protocol, same eval.
ONLY the correction update varies: A_full / A_prior_only / A_feat_only / A_replay.
No pass/fail bar; outcome is a mechanism attribution table. Null is a result.
Usage: python3 b563.py
"""
import json
import b562 as B
from b562_diag import build  # reproduces b562 run4 data + trained arms exactly

class NBUp(B.NB):
    """NB with decomposable correction update (diagnostic only; b562 NB untouched)."""
    def corr(self, feats, d, mode):
        if mode in ('full', 'replay'):
            self.add(feats, d)
        elif mode == 'prior_only':
            self.docs[d] += 1
        elif mode == 'feat_only':
            self.fc[d].update(feats); self.tot[d] += sum(feats.values())

def jaccard(a, b):
    return len(a & b) / max(len(a | b), 1)

for seed in [0, 1, 2, 3, 4]:
    rng, train, dev, ev, ev_wrong, arms, taus, pred = build(seed)
    mis = [(s, d) for s, d, _, _ in ev
           if B.predict(arms['nb'], B.encode(s), -1e18)[0] != d][:3]
    for mode in ('full', 'prior_only', 'feat_only', 'replay'):
        m = NBUp(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        before = {d: sum(B.predict(m, B.encode(s), -1e18)[0] == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
        for s, d in mis: m.corr(B.encode(s), d, mode)
        if mode == 'replay':
            for s, d, _, _ in train:
                if d not in {dd for _, dd in mis}: m.add(B.encode(s), d)
        after = {d: sum(B.predict(m, B.encode(s), -1e18)[0] == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
        corr = {d for _, d in mis}
        degr = {d: round(100 * max(0, before[d] - after[d]), 1) for d in B.INTENTS if d not in corr}
        print('ARM ' + json.dumps({'seed': seed, 'mode': mode, 'corrections': [(s[:24], d) for s, d in mis],
              'degr_points': degr, 'mean_degr': round(sum(degr.values()) / max(len(degr), 1), 2),
              'max_degr': max(degr.values() or [0])}, ensure_ascii=False))
    # shared-marker overlap: corrected-intent correction features vs each degraded intent's eval features
    corr_feats = {}
    for s, d in mis: corr_feats.setdefault(d, set()).update(B.encode(s))
    ev_feats = {d: set() for d in B.INTENTS}
    for s, d, _, _ in ev: ev_feats[d].update(B.encode(s))
    ov = {cd: {d: round(jaccard(cf, ef), 4) for d, ef in ev_feats.items()} for cd, cf in corr_feats.items()}
    print('OVERLAP ' + json.dumps({'seed': seed, 'jaccard_corrXeval': ov}, ensure_ascii=False))
print('DONE')
