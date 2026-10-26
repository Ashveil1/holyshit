"""B-572: Class B targeted test - order-sensitive intent features.
Pre-registered in LEDGER.md (B-572) BEFORE this code. Frozen: protocol,
2x2 cells (INSPECTED dev/debug only), extractor (S4-selection+positional),
baseline M0. Arms SEPARATED for attribution: M-BI (+word bigrams),
M-POS (+edge-relative position features). Positional/bigram cues are
deliberately supplied representation design, not autonomous grammar
discovery. Usage: python3 b572.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S

def encode_bi(s):
    f = B.encode(s)
    toks = s.split()
    for a, b in zip(toks, toks[1:]):
        f['b:' + a + '|' + b] += 1
    return f

def encode_pos(s):
    f = B.encode(s)
    toks = s.split(); n = len(toks)
    for i, w in enumerate(toks):
        if i < 2: f['head%d:%s' % (i, w)] += 1
        r = n - 1 - i
        if r < 3: f['tail%d:%s' % (r, w)] += 1
    return f

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        newtmpl = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
        fresh3 = [it for d in B.INTENTS for it in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
        cell11 = [it for d in B.INTENTS for it in B.gen(rng, d, B.FAM[d], B.VOCAB[d], 8)]
        cell12 = [it for d in B.INTENTS for it in B.gen(rng, d, B.FAM[d], EVAL_VOCAB2[d], 8)]
        cell21 = [it for d in B.INTENTS for it in B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8)]
        cells = (('c11_seen_seen_INSPECTED', cell11), ('c12_seenT_unseenE_INSPECTED', cell12),
                 ('c21_unseenT_seenE_INSPECTED', cell21), ('c22_fresh3_INSPECTED', fresh3))
        fn, anchor, offstat, rolepos = learn_s4(train)
        extract0 = lambda s, d: assign_a0(*_select(s, d, fn, anchor, offstat, B.NSLOTS[d]), B.NSLOTS[d])
        mappers = {}
        for aname, enc in (('M0_NBu', B.encode), ('M-BI_bigram', encode_bi), ('M-POS_edge', encode_pos)):
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(enc(s), d)
            mappers[aname] = (m, enc)
        for aname, (m, enc) in mappers.items():
            for ename, eset in cells:
                ni = nc = jn = wrong = 0
                for s, d, gold, _ in eset:
                    p, mg = B.predict(m, enc(s), -1e18)
                    ni += 1
                    if p == d:
                        nc += 1
                        ps = extract0(s, p)
                        if ps is not None and tuple(ps) == tuple(gold): jn += 1
                    else: wrong += 1
                print('ROW ' + json.dumps({'seed': seed, 'arm': aname, 'eval': ename,
                    'intent': round(nc / ni, 3), 'joint': round(jn / ni, 3),
                    'wrong_action': wrong, 'n': ni}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'budget_bytes': BUDGET, 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
