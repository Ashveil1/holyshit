"""B-574: precision-targeted gate calibration for the teach-once channel.
Pre-registered in LEDGER.md (B-574) BEFORE this code. tau chosen on authored
dev for wrong-action <= 5% (tightest achieving; else tightest available).
Teacher supplies INTENT LABEL ONLY. Reports coverage, wrong-action, acted
intent/joint, asks per family together. Usage: python3 b574.py
"""
import json, time
from collections import Counter
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S

def pick_tau_precision(m, dev):
    """Tightest margin threshold with dev wrong-action <= 5%; if none, the
    threshold minimizing wrong-action (G1 will then fail)."""
    cands = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]} | {1e9})
    best_any = (1e9, None)
    for t in cands:
        acted = wrong = 0
        for s, d, _, _ in dev:
            p, mg = B.predict(m, B.encode(s), -1e18)
            if p is None or mg < t: continue
            acted += 1
            if p != d: wrong += 1
        rate = wrong / max(acted, 1)
        if rate < best_any[0]: best_any = (rate, t)
        if acted and rate <= 0.05: return t, rate
    return best_any[1], best_any[0]

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    agg = {}
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        fn, anchor, offstat, rolepos = learn_s4(train)
        extract0 = lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d])
        cells = (('c21_unseenT_seenE_DEVCAL',
                  {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22_fresh3_DEVCAL',
                  {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            m0 = NBu(B.INTENTS)
            for s, d, _, _ in train: m0.add(B.encode(s), d)
            ni0 = nc0 = j0 = 0
            for s, d, g, fi in items:
                p, _ = B.predict(m0, B.encode(s), -1e18); ni0 += 1
                if p == d:
                    nc0 += 1
                    ps = extract0(s, p)
                    if ps is not None and tuple(ps) == tuple(g): j0 += 1
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            tau, dev_rate = pick_tau_precision(m, dev)
            asked = Counter(); acted = right = joint = wrong = 0
            for s, d, g, fi in items:
                p, mg = B.predict(m, B.encode(s), -1e18)
                if p is None or mg < tau:
                    asked[d] += 1
                    m.add(B.encode(s), d)
                    continue
                acted += 1
                if p == d:
                    right += 1
                    ps = extract0(s, p)
                    if ps is not None and tuple(ps) == tuple(g): joint += 1
                else: wrong += 1
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename,
                'tau': round(tau, 4), 'dev_wrong_rate_at_tau': round(dev_rate, 3),
                'static_M0_intent': round(nc0 / ni0, 3), 'static_M0_joint': round(j0 / ni0, 3),
                'coverage': round(acted / len(items), 3), 'acted': acted, 'asked': sum(asked.values()),
                'acted_intent': round(right / max(acted, 1), 3),
                'acted_joint': round(joint / max(acted, 1), 3),
                'wrong_action': wrong, 'wrong_rate': round(wrong / max(acted, 1), 3),
                'asks_per_family': dict(asked)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'budget_bytes': BUDGET, 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
