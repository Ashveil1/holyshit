"""B-571: data-scale probe on the FROZEN B-570 implementation.
Pre-registered in LEDGER.md (B-571) BEFORE this code. Model code imported
UNCHANGED from b570; only training-set size varies (8/32/128 per intent,
nested prefixes, paired). Baseline recomputed inside for pairing.
1e9-byte live VmHVM watchdog (no child processes -> single-process VmHVM is
the whole tree); 10-min hard timeout. Usage: python3 b571.py
"""
import json, time
import numpy as np
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import PtrModel, tok_feats, ptr_predict, train_one, Watchdog, BUDGET, TIMEOUT_S

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time(); stopped = None
    for seed in [0, 1, 2, 3, 4]:
        rng, train8, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        import random as _random; rng2 = _random.Random(seed * 17 + 5)
        full = {d: B.gen(rng2, d, B.FAM[d], B.VOCAB[d], 128) for d in B.INTENTS}
        newtmpl = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
        fresh3 = [it for d in B.INTENTS for it in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        cell11 = [it for d in B.INTENTS for it in B.gen(rng, d, B.FAM[d], B.VOCAB[d], 8)]
        cell12 = [it for d in B.INTENTS for it in B.gen(rng, d, B.FAM[d], EVAL_VOCAB2[d], 8)]
        cell21 = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8)]
        cells = (('c11_seen_seen_INSPECTED', cell11), ('c12_seenT_unseenE_INSPECTED', cell12),
                 ('c21_unseenT_seenE_INSPECTED', cell21), ('c22_fresh3_INSPECTED', fresh3))
        for k in (8, 32, 128):
            if time.time() - t_start > TIMEOUT_S: stopped = 'TIMEOUT'; break
            if watchdog.exceeded: stopped = 'RESOURCE FAIL'; break
            train = [(s, d, sl, fi) for d in B.INTENTS for (s, d, sl, fi) in full[d][:k]]
            t0 = time.time()
            mp, _ = train_one(train, dev, seed)
            train_s = time.time() - t0
            fn, anchor, offstat, rolepos = learn_s4(train)
            extract0 = lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d])
            m0 = NBu(B.INTENTS)
            for s, d, _, _ in train: m0.add(B.encode(s), d)
            for aname in ('BASE_NBu_S4sel_pos', 'PTR'):
                for ename, eset in cells:
                    ni = nc = jn = 0
                    for s, d, gold, _ in eset:
                        ni += 1
                        if aname == 'PTR': p, ps = ptr_predict(mp, s)
                        else:
                            p, mg = B.predict(m0, B.encode(s), -1e18); ps = extract0(s, p) if p else None
                        if p == d:
                            nc += 1
                            if ps is not None and tuple(ps) == tuple(gold): jn += 1
                    print('ROW ' + json.dumps({'seed': seed, 'k': k, 'arm': aname, 'eval': ename,
                        'intent': round(nc / ni, 3), 'joint': round(jn / ni, 3), 'n': ni}, ensure_ascii=False))
            print('RES ' + json.dumps({'seed': seed, 'k': k, 'train_seconds': round(train_s, 1),
                'peak_rss_mb': round(watchdog.peak / 1e6, 1)}))
        if stopped: break
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'budget_bytes': BUDGET, 'stopped': stopped, 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
