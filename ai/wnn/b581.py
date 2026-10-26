"""B-581: dev-calibrated slot tau (the originally preregistered B-578 variant).
Standalone arm, no burden mechanism. Usage: python3 b581.py
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

def stream(items, m, scorer, intent_tau, slot_tau, anchor0, dev_mode=False):
    """Run the teaching loop. Returns per-item records."""
    recs = []
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
        slot_helped = False; unassisted_wrong = False; slots_final = {}; margins = []
        for role in range(B.NSLOTS[intent]):
            key = (intent, role)
            scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
            accepted = None
            if scorer.n[key] >= 1 and scored:
                b1 = scored[0][0]; b2 = scored[1][0] if len(scored) > 1 else -1e18
                mgap = b1 - b2
                margins.append((mgap, intent == d and ' '.join(toks[scored[0][1][0]:scored[0][1][1]]) == g[role]))
                if mgap >= slot_tau:
                    accepted = ' '.join(toks[scored[0][1][0]:scored[0][1][1]])
                    if intent == d and accepted != g[role]: unassisted_wrong = True
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
        jok = (intent == d) and len(g) == B.NSLOTS[intent] and all(slots_final[r] == g[r] for r in range(B.NSLOTS[intent]))
        recs.append({'helped': intent_helped or slot_helped, 'joint': jok,
                     'unassisted_wrong': unassisted_wrong, 'margins': margins,
                     'intent_helped': intent_helped, 'slot_helped': slot_helped})
    return recs

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
        # calibrate SLOT_TAU on authored dev: run teaching loop on dev, collect margins
        m_dev = NBu(B.INTENTS)
        for s, d, _, _ in train: m_dev.add(B.encode(s), d)
        scorer_dev = SpanScorer()
        dev_recs = stream([(s, d, g, fi) for s, d, g, fi in dev if d != 'NONE'], m_dev, scorer_dev, intent_tau, -1e18, anchor0, dev_mode=True)
        # margins recorded before any accepts (slot_tau=-inf means none accepted unassisted... margins still recorded)
        allm = [x for r in dev_recs for x in r['margins']]
        cands = sorted({round(mv, 4) for mv, _ in allm} | {1e9})
        slot_tau, best = 1e9, None
        for t in cands:
            acc = [(mv, ok) for mv, ok in allm if mv >= t]
            if not acc: continue
            wr = sum(1 for _, ok in acc if not ok) / len(acc)
            if best is None or wr < best[0]: best = (wr, t)
            if wr <= 0.05: slot_tau = t; break
        if best and best[0] > 0.05 and slot_tau == 1e9: slot_tau = best[1]
        dev_wr = best[0] if best else None
        for ename, fam in (('c21', NEW_EVAL_FAM), ('c22', FRESH3_FAM)):
            voc = B.VOCAB if ename == 'c21' else EVAL_VOCAB2
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
            # transplant dev-learned scorer state? NO - fresh scorer, calibration only transfers tau
            recs = stream(items, m, scorer, intent_tau, slot_tau, anchor0)
            half = len(recs) // 2
            q = lambda r: int(r['intent_helped']) + int(r['slot_helped'])
            fu = [i for i, r in enumerate(recs) if not r['helped']]
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename, 'slot_tau': round(slot_tau, 4),
                'dev_wrong_accept_at_tau': dev_wr,
                'n': len(recs), 'wrong_execution': sum(1 for r in recs if not r['joint']),
                'fully_unassisted': len(fu),
                'unassisted_correct_allitem': sum(recs[i]['joint'] for i in fu),
                'burden_h1': sum(q(r) for r in recs[:half]), 'burden_h2': sum(q(r) for r in recs[half:]),
                'static_allitem_joint': sb_all}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
