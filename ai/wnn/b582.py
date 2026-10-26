"""B-582: cross-session persistence probe (measurement, no gate).
Session 1: stream c22 with teacher (B-578 run1 protocol, margin>=0).
Break: serialize learned state (pickle), rebuild.
Session 2a: unassisted correctness on FRESH items of taught families.
Session 2b: stream c21 (new families) with teacher, then re-test 2a set
(interference). Usage: python3 b582.py
"""
import json, time, pickle, io as _io
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b578 import spans_of, span_feats, SpanScorer, marker_pos
from b581 import stream

def fresh_items(rng, fam, voc, n=8):
    return [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, fam[d], voc[d], n)]

def unassisted_joint(items, m, scorer, anchor0):
    """No teacher: predict intent (raw argmax), score slots top-1; count joint."""
    ok = 0
    for s, d, g, fi in items:
        toks = s.split()
        p, _ = B.predict(m, B.encode(s), -1e18)
        if p != d: continue
        mi = marker_pos(toks, d, anchor0)
        cands = spans_of(toks)
        good = True
        for role in range(B.NSLOTS[d]):
            key = (d, role)
            if not scorer.n[key]: good = False; break
            scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
            if ' '.join(toks[scored[0][1][0]:scored[0][1][1]]) != g[role]: good = False; break
        ok += good
    return ok

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
        # session 1: teach c22
        m = NBu(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        scorer = SpanScorer()
        s1 = fresh_items(rng, FRESH3_FAM, EVAL_VOCAB2)
        recs1 = stream(s1, m, scorer, intent_tau, 0.0, anchor0)
        # BREAK: serialize + rebuild
        blob = pickle.dumps({'fc': dict(scorer.fc), 'tot': scorer.tot, 'n': scorer.n,
                             'mfc': {d: dict(m.fc[d]) for d in B.INTENTS}, 'mtot': dict(m.tot)})
        st = pickle.loads(blob)
        scorer2 = SpanScorer()
        for k, v in st['fc'].items(): scorer2.fc[k].update(v)
        scorer2.tot.update(st['tot']); scorer2.n.update(st['n'])
        m2 = NBu(B.INTENTS)
        for d in B.INTENTS: m2.fc[d].update(st['mfc'][d]); m2.tot[d] = st['mtot'][d]
        # session 2a: fresh items of TAUGHT families, unassisted
        s2a = fresh_items(rng, FRESH3_FAM, EVAL_VOCAB2)
        ok_a = unassisted_joint(s2a, m2, scorer2, anchor0)
        # session 2b: teach NEW families (c21), then re-test taught-family set
        s2b = fresh_items(rng, NEW_EVAL_FAM, B.VOCAB)
        recs2b = stream(s2b, m2, scorer2, intent_tau, 0.0, anchor0)
        s2c = fresh_items(rng, FRESH3_FAM, EVAL_VOCAB2)
        ok_c = unassisted_joint(s2c, m2, scorer2, anchor0)
        print('ROW ' + json.dumps({'seed': seed,
            'session1_items': len(s1), 'session1_wrong_execution': sum(1 for r in recs1 if not r['joint']),
            's2a_fresh_taught_family_unassisted_joint': ok_a, 's2a_n': len(s2a),
            's2c_after_new_families_joint': ok_c, 's2c_n': len(s2c)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
