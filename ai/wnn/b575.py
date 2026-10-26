"""B-575: descriptive analysis - safety/coverage frontier + retention probe.
Pre-registered in LEDGER.md (B-575). No success gate; measurement only.
Usage: python3 b575.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        cells = (('c21', {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22', {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            # (a) frontier: static mapper, tau grid
            margs = [B.predict(m, B.encode(s), -1e18)[1] for s, d, g, fi in items]
            grid = sorted({round(x, 2) for x in margs[::max(1, len(margs)//16)]} | {0.0})
            curve = []
            for t in grid:
                acted = wrong = 0
                for (s, d, g, fi), mg in zip(items, margs):
                    if mg < t: continue
                    acted += 1
                    p, _ = B.predict(m, B.encode(s), -1e18)
                    if p != d: wrong += 1
                curve.append({'t': t, 'cov': round(acted / len(items), 3),
                              'wrate': round(wrong / max(acted, 1), 3)})
            print('FRONTIER ' + json.dumps({'seed': seed, 'eval': ename, 'curve': curve}))
            # (b) retention: interactive stream at precision tau, then re-predict everything
            m2 = NBu(B.INTENTS)
            for s, d, _, _ in train: m2.add(B.encode(s), d)
            tau, _ = pick_tau_precision(m2, dev)
            taught = []; first_pass = {}
            for i, (s, d, g, fi) in enumerate(items):
                p, mg = B.predict(m2, B.encode(s), -1e18)
                if p is None or mg < tau:
                    m2.add(B.encode(s), d); taught.append(i)
                else:
                    first_pass[i] = (p == d)
            ret_taught = ret_acted = 0
            for i, (s, d, g, fi) in enumerate(items):
                p, mg = B.predict(m2, B.encode(s), -1e18)
                if i in taught: ret_taught += (p == d)
                else: ret_acted += (p == d)
            n_taught = len(taught); n_acted = len(items) - n_taught
            drift = sum(1 for i, ok in first_pass.items()
                        if B.predict(m2, B.encode(items[i][0]), -1e18)[0] != items[i][1] and ok)
            print('RETENTION ' + json.dumps({'seed': seed, 'eval': ename,
                'taught': n_taught, 'taught_retained': ret_taught,
                'taught_recall': round(ret_taught / max(n_taught, 1), 3),
                'first_pass_acted_right': sum(first_pass.values()), 'n_acted': n_acted,
                'acted_right_after_stream': ret_acted,
                'acted_recall_after': round(ret_acted / max(n_acted, 1), 3),
                'previously_right_now_wrong': drift}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
