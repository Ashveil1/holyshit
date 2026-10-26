"""B-587: paired-seed operating-point validation (development robustness).
Usage: python3 b587.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    agg = {}
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        m = NBu(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        tau_dev, _ = pick_tau_precision(m, dev)
        seen = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, B.FAM[d], B.VOCAB[d], 8)]
        c21 = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8)]
        c22 = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        offt = [(s, 'NONE', (), -1) for s in B.WRONG_INTENT]
        for name, tau in (('tau5', 5.0), ('tau10', 10.0), ('tau_dev', tau_dev)):
            a = agg.setdefault(name, {'seen_act': 0, 'seen_right': 0, 'un_act': 0, 'un_wrong': 0, 'off_act': 0, 'seen_n': 0, 'un_n': 0, 'off_n': 0, 'taus': []})
            a['taus'].append(round(tau, 2)); a['seen_n'] += len(seen); a['un_n'] += len(c21) + len(c22); a['off_n'] += len(offt)
            for s, d, g, fi in seen:
                p, mg = B.predict(m, B.encode(s), -1e18)
                if p is not None and mg >= tau: a['seen_act'] += 1; a['seen_right'] += (p == d)
            for items in (c21, c22):
                for s, d, g, fi in items:
                    p, mg = B.predict(m, B.encode(s), -1e18)
                    if p is not None and mg >= tau: a['un_act'] += 1; a['un_wrong'] += (p != d)
            for s, d, g, fi in offt:
                p, mg = B.predict(m, B.encode(s), -1e18)
                if p is not None and mg >= tau: a['off_act'] += 1
    for name, a in agg.items():
        a.pop('taus')
        a['seen_cov'] = round(a['seen_act'] / a['seen_n'], 3)
        a['unseen_wrong_intent_rate_of_acted'] = round(a['un_wrong'] / max(a['un_act'], 1), 3)
        print('ROW ' + json.dumps({'gate': name, **a}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
