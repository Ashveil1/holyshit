"""B-573: interactive teach-once acquisition channel.
Pre-registered in LEDGER.md (B-573) BEFORE this code. Frozen NBu + frozen
extractor; NEW channel: margin-gated ask-the-teacher on INSPECTED unseen-
template cells (simulated teacher = AUTHORED validation). Taught items are
excluded from metrics. Usage: python3 b573.py
"""
import json, time
from collections import Counter, defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        fn, anchor, offstat, rolepos = learn_s4(train)
        extract0 = lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d])
        cells = (('c21_unseenT_seenE_INSPECTED',
                  {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22_fresh3_INSPECTED',
                  {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        # static M0 baseline on the same cell items (non-interactive, all items scored)
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            m0 = NBu(B.INTENTS)
            for s, d, _, _ in train: m0.add(B.encode(s), d)
            ni0 = nc0 = 0
            for s, d, g, fi in items:
                p, _ = B.predict(m0, B.encode(s), -1e18); ni0 += 1; nc0 += (p == d)
            # interactive: fresh mapper, tau calibrated on authored dev (same procedure as build)
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            cands = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]})
            best_t, best_r = 0.0, -1
            for t in cands:
                ok = 0
                for s, d, _, _ in dev:
                    p, mg = B.predict(m, B.encode(s), -1e18); p = p if mg >= t else None
                    ok += (p == d) if d != 'NONE' else (p is None)
                if ok / len(dev) > best_r: best_r, best_t = ok / len(dev), t
            asked = Counter(); acted = right = joint = wrong = 0
            for s, d, g, fi in items:
                p, mg = B.predict(m, B.encode(s), -1e18)
                if p is None or mg < best_t:
                    asked[d] += 1
                    m.add(B.encode(s), d)   # simulated teacher supplies gold intent
                    continue                 # taught item EXCLUDED from metrics
                acted += 1
                if p == d:
                    right += 1
                    ps = extract0(s, p)
                    if ps is not None and tuple(ps) == tuple(g): joint += 1
                else: wrong += 1
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename, 'tau': round(best_t, 4),
                'static_M0_intent': round(nc0 / ni0, 3),
                'acted': acted, 'asked': sum(asked.values()),
                'acted_intent': round(right / max(acted, 1), 3),
                'acted_joint': round(joint / max(acted, 1), 3),
                'wrong_action': wrong, 'wrong_rate': round(wrong / max(acted, 1), 3),
                'asks_per_family': dict(asked)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'budget_bytes': BUDGET, 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
