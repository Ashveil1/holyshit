"""B-579: matched-baseline reconciliation of B-578 G3 (measurement, no gate).
Static baseline computed on EXACTLY the fully-unassisted item set.
Usage: python3 b579.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b578 import spans_of, span_feats, SpanScorer, marker_pos

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        m_tau = NBu(B.INTENTS)
        for s, d, _, _ in train: m_tau.add(B.encode(s), d)
        intent_tau, _ = pick_tau_precision(m_tau, dev)
        fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
        extract0 = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
        m0 = NBu(B.INTENTS)   # static baseline mapper
        for s, d, _, _ in train: m0.add(B.encode(s), d)
        cells = (('c21', {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22', {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            scorer = SpanScorer()
            fu_idx, helped_idx = [], []
            joint_fu = joint_helped = 0
            for idx, (s, d, g, fi) in enumerate(items):
                toks = s.split()
                p, mg = B.predict(m, B.encode(s), -1e18)
                intent_helped = False
                if p is None or mg < intent_tau:
                    m.add(B.encode(s), d); intent = d; intent_helped = True
                else:
                    intent = p
                mi = marker_pos(toks, intent, anchor0)
                cands = spans_of(toks)
                slot_helped = False; slots_final = {}
                for role in range(B.NSLOTS[intent]):
                    key = (intent, role)
                    scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
                    accepted = None
                    if scorer.n[key] >= 1 and scored:
                        b1 = scored[0][0]; b2 = scored[1][0] if len(scored) > 1 else -1e18
                        if b1 - b2 >= 0.0:
                            accepted = ' '.join(toks[scored[0][1][0]:scored[0][1][1]])
                    if accepted is None:
                        slot_helped = True
                        got = False
                        for sc, sp in scored[:3]:
                            txt = ' '.join(toks[sp[0]:sp[1]])
                            if txt == g[role]:
                                scorer.add(key, span_feats(toks, sp, mi)); accepted = txt; got = True; break
                        if not got:
                            accepted = g[role]
                            for sp in cands:
                                if ' '.join(toks[sp[0]:sp[1]]) == g[role]:
                                    scorer.add(key, span_feats(toks, sp, mi)); break
                    slots_final[role] = accepted
                jok = (intent == d) and all(slots_final[r] == g[r] for r in range(B.NSLOTS[intent]))
                if intent_helped or slot_helped:
                    helped_idx.append(idx); joint_helped += jok
                else:
                    fu_idx.append(idx); joint_fu += jok
            # static baseline on EXACTLY the fully-unassisted set + on all items
            sb_fu = sb_all = 0
            for idx, (s, d, g, fi) in enumerate(items):
                p, _ = B.predict(m0, B.encode(s), -1e18)
                ok = False
                if p == d:
                    ps = extract0(s, p)
                    ok = ps is not None and tuple(ps) == tuple(g)
                sb_all += ok
                if idx in set(fu_idx): sb_fu += ok
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename, 'n': len(items),
                'fully_unassisted': len(fu_idx), 'helped': len(helped_idx),
                'interactive_joint_on_fu': joint_fu,
                'static_joint_on_fu': sb_fu,
                'interactive_joint_on_helped': joint_helped,
                'static_joint_all_items': sb_all}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
