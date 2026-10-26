"""B-578: slot-teaching feasibility prototype.
Pre-registered in LEDGER.md (B-578) BEFORE this code. Usage: python3 b578.py
"""
import json, time, math
from collections import Counter, defaultdict
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision

def spans_of(toks, maxlen=5):
    out = []
    for i in range(len(toks)):
        for n in range(1, min(maxlen, len(toks) - i) + 1):
            out.append((i, i + n))
    return out

def span_feats(toks, sp, marker_idx):
    i, j = sp
    st = toks[i:j]
    f = {'len': j - i, 'start%d' % i: 1, 'end_from_right%d' % (len(toks) - j): 1}
    for t in st: f['tok:' + t] = 1
    f['first:' + st[0]] = 1; f['last:' + st[-1]] = 1
    if marker_idx is not None:
        f['dist_m%d' % (i - marker_idx)] = 1
    if i > 0: f['prev:' + toks[i - 1]] = 1
    if j < len(toks): f['next:' + toks[j]] = 1
    return f

class SpanScorer:
    """NBu-style counts over (intent, role) -> feature -> count."""
    def __init__(self, a=0.1):
        self.fc = defaultdict(Counter); self.tot = Counter(); self.n = Counter(); self.a = a
    def add(self, key, feats):
        for f, c in feats.items(): self.fc[key][f] += c
        self.tot[key] += sum(feats.values()); self.n[key] += 1
    def score(self, key, feats):
        if not self.n[key]: return -1e18
        V = 50000; den = self.tot[key] + self.a * V
        return sum(c * math.log((self.fc[key][f] + self.a) / den) for f, c in feats.items())

def marker_pos(toks, intent, anchor):
    # supplied: position of the train-derived per-intent anchor token, else None
    a = anchor.get(intent)
    return toks.index(a) if a in toks else None

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    for seed in [0, 1, 2, 3, 4]:
        if time.time() - t_start > TIMEOUT_S: print('TIMEOUT'); break
        if watchdog.exceeded: print('RESOURCE FAIL'); break
        rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(seed)
        intent_tau, _ = pick_tau_precision(
            (lambda m: [m.add(B.encode(s), d) for s, d, _, _ in train] and m)(NBu(B.INTENTS)), dev)
        cells = (('c21', {d: B.gen(rng, d, NEW_EVAL_FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}),
                 ('c22', {d: B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8) for d in B.INTENTS}))
        for ename, byd in cells:
            items = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in byd[d]]
            # static M0 all-item joint baseline
            m0 = NBu(B.INTENTS)
            for s, d, _, _ in train: m0.add(B.encode(s), d)
            from b566 import _select, assign_a0
            fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
            extract0 = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
            bj = 0
            for s, d, g, fi in items:
                p, _ = B.predict(m0, B.encode(s), -1e18)
                if p == d:
                    ps = extract0(s, p)
                    if ps is not None and tuple(ps) == tuple(g): bj += 1
            # interactive slot teaching
            m = NBu(B.INTENTS)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            scorer = SpanScorer()
            SLOT_TAU = 0.0  # prereg: accept unassisted iff >=1 confirmed example and margin >= 0
            iq = sq = offers = retypes = 0
            executed = exec_correct = unassisted_exec = unassisted_correct = 0
            half = len(items) // 2
            burden_h1 = burden_h2 = 0
            taught_items = []
            for idx, (s, d, g, fi) in enumerate(items):
                burden0 = iq + sq + retypes
                toks = s.split()
                p, mg = B.predict(m, B.encode(s), -1e18)
                if p is None or mg < intent_tau:
                    iq += 1; m.add(B.encode(s), d); intent = d; intent_confirmed = True
                else:
                    intent = p; intent_confirmed = False
                mi = marker_pos(toks, intent, anchor0)
                cands = spans_of(toks)
                goldmap = {k: v for k, v in enumerate(g)}
                slots_final = {}; all_ok = True; needed_help = False
                for role in range(B.NSLOTS[intent]):
                    gold_span_text = goldmap.get(role)
                    key = (intent, role)
                    scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands),
                                    key=lambda x: -x[0])
                    accepted = None
                    if scorer.n[key] >= 1 and scored:
                        (b1, sp1), (b2, sp2) = scored[0], (scored[1] if len(scored) > 1 else (-1e18, None))
                        if b1 - b2 >= SLOT_TAU and ' '.join(toks[sp1[0]:sp1[1]]) == gold_span_text:
                            accepted = ' '.join(toks[sp1[0]:sp1[1]])
                        elif b1 - b2 >= SLOT_TAU:
                            accepted = ' '.join(toks[sp1[0]:sp1[1]])  # unassisted accept (may be wrong)
                    if accepted is None:
                        needed_help = True
                        got = False
                        for sc, sp in scored[:3]:
                            offers += 1; sq += 1
                            txt = ' '.join(toks[sp[0]:sp[1]])
                            if txt == gold_span_text:
                                scorer.add(key, span_feats(toks, sp, mi)); accepted = txt; got = True; break
                        if not got:
                            retypes += 1
                            accepted = gold_span_text  # teacher retypes exact value
                            gsp = None
                            for sp in cands:
                                if ' '.join(toks[sp[0]:sp[1]]) == gold_span_text: gsp = sp; break
                            if gsp is not None: scorer.add(key, span_feats(toks, gsp, mi))
                    slots_final[role] = accepted
                burden = (iq + sq + retypes) - burden0
                if idx < half: burden_h1 += burden
                else: burden_h2 += burden
                executed += 1
                joint_ok = (intent == d) and all(slots_final[r] == goldmap.get(r) for r in range(B.NSLOTS[intent]))
                if joint_ok: exec_correct += 1
                if not needed_help and not (iq and intent_confirmed):
                    pass
                if not needed_help:
                    unassisted_exec += 1
                    if joint_ok: unassisted_correct += 1
                taught_items.append((s, d, g))
            # retention probe: unassisted re-predict taught items' slots
            ret_ok = ret_n = 0
            for s, d, g in taught_items:
                toks = s.split(); mi = marker_pos(toks, d, anchor0)
                okall = True
                for role in range(B.NSLOTS[d]):
                    key = (d, role)
                    if not scorer.n[key]: okall = False; break
                    cands = spans_of(toks)
                    scored = sorted(((scorer.score(key, span_feats(toks, sp, mi)), sp) for sp in cands), key=lambda x: -x[0])
                    if ' '.join(toks[scored[0][1][0]:scored[0][1][1]]) != g[role]: okall = False; break
                ret_n += 1; ret_ok += okall
            print('ROW ' + json.dumps({'seed': seed, 'eval': ename,
                'intent_qs': iq, 'slot_qs': sq, 'offer_rounds': offers, 'retypes': retypes,
                'executed': executed, 'exec_correct': exec_correct,
                'wrong_execution': executed - exec_correct,
                'unassisted_exec': unassisted_exec, 'unassisted_correct': unassisted_correct,
                'burden_h1': burden_h1, 'burden_h2': burden_h2,
                'static_M0_allitem_joint': bj, 'n': len(items),
                'retention': round(ret_ok / max(ret_n, 1), 3)}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1),
        'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
