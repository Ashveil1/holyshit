"""B-577: metric reconciliation rerun of the B-574 and B-576 protocols with
EXACT counters. Same frozen protocols/thresholds; only metric names corrected
per review: wrong-intent vs wrong-execution (acted and NOT joint-correct),
abstention, exact joint counts, all-item joint baselines. No gate.
Usage: python3 b577.py
"""
import json, time
from collections import Counter
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b576 import pick_tau_accuracy

def run_arm(name, items, train, dev, extract0, two_tier):
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    tau_lo = pick_tau_accuracy(m, dev) if two_tier else None
    confirmed = set()
    abstained = acted = wrong_intent = joint_ok = 0
    for s, d, g, fi in items:
        p, mg = B.predict(m, B.encode(s), -1e18)
        act = False
        if p is not None:
            if mg >= tau_hi: act = True
            elif two_tier and mg >= tau_lo and p in confirmed: act = True
        if not act:
            abstained += 1; m.add(B.encode(s), d); confirmed.add(d); continue
        acted += 1
        if p != d: wrong_intent += 1
        else:
            ps = extract0(s, p)
            if ps is not None and tuple(ps) == tuple(g): joint_ok += 1
    return {'arm': name, 'n': len(items), 'abstained': abstained, 'acted': acted,
            'wrong_intent': wrong_intent, 'joint_correct': joint_ok,
            'wrong_execution': acted - joint_ok}

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        fn, anchor, offstat, rolepos = learn_s4(train)
        extract0 = lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d])
        cells = (('c21', {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22', {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            # static all-item baseline (no asks): exact counters
            m0 = NBu(B.INTENTS)
            for s, d, _, _ in train: m0.add(B.encode(s), d)
            b_acted = b_wi = b_j = 0
            for s, d, g, fi in items:
                p, _ = B.predict(m0, B.encode(s), -1e18)
                b_acted += 1
                if p != d: b_wi += 1
                else:
                    ps = extract0(s, p)
                    if ps is not None and tuple(ps) == tuple(g): b_j += 1
            print('BASE ' + json.dumps({'seed': seed, 'eval': ename, 'n': len(items),
                'all_item_wrong_intent': b_wi, 'all_item_joint': b_j,
                'all_item_wrong_execution': b_acted - b_j}))
            for name, tt in (('B574_precision', False), ('B576_two_tier', True)):
                r = run_arm(name, items, train, dev, extract0, tt); r['seed'] = seed; r['eval'] = ename
                print('RECON ' + json.dumps(r))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
