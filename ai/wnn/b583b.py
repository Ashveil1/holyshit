"""B-583b: novelty + collision controls for the local-confirmation rule.
(a) NOVELTY: after teaching c21+c22, stream a THIRD unseen family (EVAL_FAM,
excluding the audited-invalid teach_attr '{y} ของ {x} สวย' template) -
executions on genuinely new templates are safety leaks; questions expected.
(b) COLLISION: count items where a confirmed signature fired but the gold
slot value differed (ambiguity control; protocol-expectation ~0, measured).
Usage: python3 b583b.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b578 import spans_of, span_feats, SpanScorer, marker_pos
from b583 import sig

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
        m = NBu(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        scorer = SpanScorer(); confirmed = set()
        def teach_stream(items):
            for s, d, g, fi in items:
                toks = s.split()
                p, mg = B.predict(m, B.encode(s), -1e18)
                if p is None or mg < intent_tau:
                    m.add(B.encode(s), d); intent = d
                else:
                    intent = p
                mi = marker_pos(toks, intent, anchor0)
                cands = spans_of(toks)
                for role in range(B.NSLOTS[intent]):
                    key = (intent, role)
                    scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
                    if any(sig(toks, sp, intent, role) in confirmed for sc, sp in scored): continue
                    got = False
                    for sc, sp in scored[:3]:
                        if intent == d and ' '.join(toks[sp[0]:sp[1]]) == g[role]:
                            scorer.add(key, span_feats(toks, sp, mi)); confirmed.add(sig(toks, sp, intent, role)); got = True; break
                    if not got and intent == d:
                        for sp in cands:
                            if ' '.join(toks[sp[0]:sp[1]]) == g[role]:
                                scorer.add(key, span_feats(toks, sp, mi)); confirmed.add(sig(toks, sp, intent, role)); break
        c21 = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8)]
        c22 = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        teach_stream(c21); teach_stream(c22)
        # (a) novelty: EVAL_FAM minus invalid template (fi==1 for teach_attr is '{y} ของ {x} สวย')
        novel = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, B.EVAL_FAM[d], B.EVAL_VOCAB[d], 8)
                 if not (d == 'teach_attr' and fi == 1)]
        n_exec = n_q = n_exec_wrong = n_coll = 0
        for s, d, g, fi in novel:
            toks = s.split()
            p, mg = B.predict(m, B.encode(s), -1e18)
            if p is None or mg < intent_tau: n_q += 1; continue
            intent = p
            mi = marker_pos(toks, intent, anchor0)
            cands = spans_of(toks)
            acted = True; slots_final = {}
            for role in range(B.NSLOTS[intent]):
                key = (intent, role)
                scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
                hit = None
                for sc, sp in scored:
                    if sig(toks, sp, intent, role) in confirmed: hit = sp; break
                if hit is None: acted = False; break
                slots_final[role] = ' '.join(toks[hit[0]:hit[1]])
                if intent == d and slots_final[role] != g[role]: n_coll += 1
            if acted:
                n_exec += 1
                jok = (intent == d) and len(g) == B.NSLOTS[intent] and all(slots_final[r] == g[r] for r in range(B.NSLOTS[intent]))
                if not jok: n_exec_wrong += 1
            else:
                n_q += 1
        print('ROW ' + json.dumps({'seed': seed, 'novel_items': len(novel),
            'novel_executed': n_exec, 'novel_wrong_execution': n_exec_wrong,
            'novel_questions': n_q, 'slot_signature_collisions': n_coll}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
