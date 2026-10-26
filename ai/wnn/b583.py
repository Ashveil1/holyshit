"""B-583: local-confirmation accept rule - unassisted only on literally
confirmed (intent, role, prev, span, next) configurations.
Pre-registered in LEDGER.md (B-583). Usage: python3 b583.py
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

def sig(toks, sp, intent, role):
    i, j = sp
    prev = toks[i - 1] if i > 0 else '<BOS>'
    nxt = toks[j] if j < len(toks) else '<EOS>'
    return (intent, role, prev, ' '.join(toks[i:j]), nxt)

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
        for ename, fam, voc in (('c21', NEW_EVAL_FAM, B.VOCAB), ('c22', FRESH3_FAM, EVAL_VOCAB2)):
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, fam[d], voc[d], 8)]
            m0 = NBu(B.INTENTS)
            for s, d, _, _ in train: m0.add(B.encode(s), d)
            sb_all = 0
            for s, d, g, fi in items:
                p, _ = B.predict(m0, B.encode(s), -1e18)
                if p == d:
                    ps = extract0(s, p)
                    if ps is not None and tuple(ps) == tuple(g): sb_all += 1
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            scorer = SpanScorer()
            confirmed = set()
            iq = sq = retypes = 0
            recs = []
            for s, d, g, fi in items:
                toks = s.split()
                p, mg = B.predict(m, B.encode(s), -1e18)
                intent_helped = False
                if p is None or mg < intent_tau:
                    iq += 1; m.add(B.encode(s), d); intent = d; intent_helped = True
                else:
                    intent = p
                mi = marker_pos(toks, intent, anchor0)
                cands = spans_of(toks)
                slot_helped = False; slots_final = {}
                for role in range(B.NSLOTS[intent]):
                    key = (intent, role)
                    scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
                    accepted = None
                    for sc, sp in scored:
                        if sig(toks, sp, intent, role) in confirmed:
                            accepted = ' '.join(toks[sp[0]:sp[1]]); break
                    if accepted is None:
                        slot_helped = True
                        got = False
                        for sc, sp in scored[:3]:
                            sq += 1
                            txt = ' '.join(toks[sp[0]:sp[1]])
                            if intent == d and txt == g[role]:
                                scorer.add(key, span_feats(toks, sp, mi))
                                confirmed.add(sig(toks, sp, intent, role)); accepted = txt; got = True; break
                        if not got:
                            retypes += 1
                            accepted = g[role] if intent == d else ' '.join(toks[scored[0][1][0]:scored[0][1][1]])
                            if intent == d:
                                for sp in cands:
                                    if ' '.join(toks[sp[0]:sp[1]]) == g[role]:
                                        scorer.add(key, span_feats(toks, sp, mi))
                                        confirmed.add(sig(toks, sp, intent, role)); break
                    slots_final[role] = accepted
                jok = (intent == d) and len(g) == B.NSLOTS[intent] and all(slots_final[r] == g[r] for r in range(B.NSLOTS[intent]))
                recs.append({'helped': intent_helped or slot_helped, 'joint': jok,
                             'intent_helped': intent_helped, 'slot_helped': slot_helped})
            half = len(recs) // 2
            q = lambda r: 0  # burden counted via iq/sq/retypes streams below
            # recompute burden halves by replaying counters: approximate via per-item helped flags
            h1 = sum(int(r['intent_helped']) + int(r['slot_helped']) for r in recs[:half])
            h2 = sum(int(r['intent_helped']) + int(r['slot_helped']) for r in recs[half:])
            fu = [i for i, r in enumerate(recs) if not r['helped']]
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename,
                'n': len(recs), 'wrong_execution': sum(1 for r in recs if not r['joint']),
                'fully_unassisted': len(fu),
                'unassisted_correct_allitem': sum(recs[i]['joint'] for i in fu),
                'helped_joint': sum(r['joint'] for r in recs if r['helped']),
                'helped': sum(1 for r in recs if r['helped']),
                'intent_qs': iq, 'slot_qs': sq, 'retypes': retypes,
                'burden_h1_flags': h1, 'burden_h2_flags': h2,
                'static_allitem_joint': sb_all}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
