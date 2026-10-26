"""B-580: failure accounting on B-579's helped items (diagnostic, no arm).
For each helped item, classify the joint failure source:
A) acted intent WRONG (no intent question fired) - slots never recoverable;
B) intent confirmed by teacher, but >=1 slot UNASSISTED-accepted and wrong;
C) intent confirmed AND all slots teacher-confirmed (retype/offer) yet
   execution still wrong (should be impossible - counts as invariant check).
Also splits helped into intent-helped-only vs slot-helped vs both.
Usage: python3 b580.py
"""
import json, time
from collections import Counter
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b578 import spans_of, span_feats, SpanScorer, marker_pos
from b565 import learn_s4

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        m_tau = NBu(B.INTENTS)
        for s, d, _, _ in train: m_tau.add(B.encode(s), d)
        intent_tau, _ = pick_tau_precision(m_tau, dev)
        fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
        cells = (('c21', {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22', {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            scorer = SpanScorer()
            cls = Counter()
            for s, d, g, fi in items:
                toks = s.split()
                p, mg = B.predict(m, B.encode(s), -1e18)
                intent_helped = False
                if p is None or mg < intent_tau:
                    m.add(B.encode(s), d); intent = d; intent_helped = True
                else:
                    intent = p
                mi = marker_pos(toks, intent, anchor0)
                cands = spans_of(toks)
                slot_helped = False; slot_unassisted_wrong = False; slots_final = {}
                for role in range(B.NSLOTS[intent]):
                    key = (intent, role)
                    gold_role = g[role] if intent == d and role < len(g) else None
                    scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
                    accepted = None
                    if scorer.n[key] >= 1 and scored:
                        b1 = scored[0][0]; b2 = scored[1][0] if len(scored) > 1 else -1e18
                        if b1 - b2 >= 0.0:
                            accepted = ' '.join(toks[scored[0][1][0]:scored[0][1][1]])
                            if intent == d and accepted != g[role]: slot_unassisted_wrong = True
                    if accepted is None:
                        slot_helped = True
                        got = False
                        for sc, sp in scored[:3]:
                            txt = ' '.join(toks[sp[0]:sp[1]])
                            if intent == d and txt == g[role]:
                                scorer.add(key, span_feats(toks, sp, mi)); accepted = txt; got = True; break
                        if not got:
                            accepted = g[role] if intent == d else ' '.join(toks[scored[0][1][0]:scored[0][1][1]])
                            if intent == d:
                                for sp in cands:
                                    if ' '.join(toks[sp[0]:sp[1]]) == g[role]:
                                        scorer.add(key, span_feats(toks, sp, mi)); break
                    slots_final[role] = accepted
                helped = intent_helped or slot_helped
                if not helped: continue
                jok = (intent == d) and all(slots_final.get(r) == g[r] for r in range(B.NSLOTS[intent]) if r < len(g)) and len(g) == B.NSLOTS[intent]
                kind = ('both' if intent_helped and slot_helped else
                        'intent_only' if intent_helped else 'slot_only')
                if jok: cls['helped_' + kind + '_OK'] += 1
                elif intent != d: cls['A_wrong_acted_intent__' + kind] += 1
                elif slot_unassisted_wrong: cls['B_confirmed_intent_unassisted_slot_wrong__' + kind] += 1
                else: cls['C_all_confirmed_still_wrong__' + kind] += 1
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename, 'classes': dict(cls)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
