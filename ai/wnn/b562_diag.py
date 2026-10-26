"""B-562 metric reconciliation (review-requested, no new hypotheses, no criterion changes).
Reproduces run4's exact data (same rng order), then reports:
A) H2 confusion per arm k=8 with explicit definitions and raw counts
B) margin calibration: dev vs eval margin quartiles per arm
C) confirmation decomposition: same-item RECALL vs FRESH-ITEM TRANSFER vs RETENTION-after-more-teaching
D) seed-0 collateral validation: per-intent before/after accuracies + doc counts + small-correction variant
Usage: python3 b562_diag.py
"""
import json, random
from collections import Counter
import b562 as B

def build(seed):
    rng = random.Random(1000 + seed)
    train_full = {d: B.gen(rng, d, B.FAM[d], B.VOCAB[d], 8) for d in B.INTENTS}
    dev = [it for d in B.INTENTS for it in B.gen(rng, d, [B.DEV_FAM[d]], B.VOCAB[d], 4)]
    dev += [(s, 'NONE', (), -1) for s in rng.sample(B.WRONG_INTENT, 8)]
    ev = [it for d in B.INTENTS for it in B.gen(rng, d, B.EVAL_FAM[d], B.EVAL_VOCAB[d], 8)]
    ev_wrong = [(s, 'NONE', (), -1) for s in [w for w in B.WRONG_INTENT if w not in {x[0] for x in dev}]]
    train = [(s, d, sl, fi) for d in B.INTENTS for (s, d, sl, fi) in train_full[d][:8]]
    # WNN bleach/tau selection identical to b562.main
    best_cfg, best_j = None, -1
    for bleach in (1, 2):
        for tau in (1, 2, 4):
            m = B.WNN(B.INTENTS, seed, bleach=bleach)
            for s, d, _, _ in train: m.add(B.encode(s), d)
            ok = sum((B.predict(m, B.encode(s), tau)[0] == d) if d != 'NONE' else (B.predict(m, B.encode(s), tau)[0] is None) for s, d, _, _ in dev)
            if ok / len(dev) > best_j: best_j, best_cfg = ok / len(dev), (bleach, tau)
    bleach, wtau = best_cfg
    arms = {'wnn': B.WNN(B.INTENTS, seed, bleach=bleach), 'nb': B.NB(B.INTENTS), 't2p': B.T2P(B.INTENTS), 'nn1': B.NN1(B.INTENTS)}
    for s, d, _, _ in train:
        f = B.encode(s)
        for m in arms.values(): m.add(f, d)
    taus = {}
    for name, m in arms.items():
        if name == 'wnn': taus[name] = ('score', wtau); continue
        cands = sorted({round(mg, 4) for s, d, _, _ in dev for _, mg in [B.predict(m, B.encode(s), -1e18)]})
        best_t, best_r = -1e18, -1
        for t in cands:
            ok = 0
            for s, d, _, _ in dev:
                p, mg = B.predict(m, B.encode(s), -1e18)
                p = p if mg >= t else None
                ok += (p == d) if d != 'NONE' else (p is None)
            if ok / len(dev) > best_r: best_r, best_t = ok / len(dev), t
        taus[name] = ('margin', best_t)
    def pred(name, s):
        kind, t = taus[name]
        if kind == 'score': return B.predict(arms[name], B.encode(s), t)[0]
        p, mg = B.predict(arms[name], B.encode(s), -1e18)
        return p if mg >= t else None
    return rng, train, dev, ev, ev_wrong, arms, taus, pred

if __name__ == '__main__':
    for seed in [0, 1, 2, 3, 4]:
        rng, train, dev, ev, ev_wrong, arms, taus, pred = build(seed)
        # A) H2 confusion (definitions below) + margins
        for name in arms:
            acc_cor = acc_wrg = ab_real = 0
            margins_ev = []
            for s, d, _, _ in ev:
                p = pred(name, s)
                mg = B.predict(arms[name], B.encode(s), -1e18)[1]
                margins_ev.append(round(mg, 3))
                if p is None: ab_real += 1
                elif p == d: acc_cor += 1
                else: acc_wrg += 1
            tn = fp = 0
            for s, _, _, _ in ev_wrong:
                if pred(name, s) is None: tn += 1
                else: fp += 1
            margins_ev.sort()
            q = lambda v, p: v[int(p * (len(v) - 1))]
            print('H2 ' + json.dumps({'seed': seed, 'arm': name,
                'defs': 'accepted_correct=real eval accepted with gold intent; accepted_wrong=real eval accepted with wrong intent; abstained_real=real eval abstained; NONE_abstained=TN; NONE_forced=FP. precision=NONE_abstained/(NONE_abstained+abstained_real); recall=NONE_abstained/N_total',
                'accepted_correct': acc_cor, 'accepted_wrong': acc_wrg, 'abstained_real': ab_real,
                'NONE_abstained': tn, 'NONE_forced': fp, 'N_real': len(ev), 'N_NONE': len(ev_wrong),
                'precision': round(tn / max(tn + ab_real, 1), 3), 'recall': round(tn / len(ev_wrong), 3),
                'eval_margin_q': [q(margins_ev, p) for p in (0.25, 0.5, 0.75)]}, ensure_ascii=False))
        # winner as in run4
        accs = {n: sum(pred(n, s) == d for s, d, _, _ in ev) / len(ev) for n in arms}
        winner = max(accs, key=accs.get)
        kind, wt = taus[winner]
        # C) confirmation decomposition on winner
        msrc = arms[winner]
        margins = sorted(round(B.predict(msrc, B.encode(s), -1e18)[1], 4) for s, d, _, _ in dev if d != 'NONE')
        conf_t = margins[len(margins) // 4] if margins else 0.0
        low = [(s, d, fi) for s, d, _, fi in ev if B.predict(msrc, B.encode(s), -1e18)[1] < conf_t]
        # fresh mapper copy at post-training state
        m2 = {'wnn': lambda: B.WNN(B.INTENTS, seed, bleach=taus['wnn'][1]), 'nb': lambda: B.NB(B.INTENTS),
              't2p': lambda: B.T2P(B.INTENTS), 'nn1': lambda: B.NN1(B.INTENTS)}[winner]()
        for s, d, _, _ in train: m2.add(B.encode(s), d)
        same_recall = transfer = 0
        confirmed = []
        for s, d, fi in low:
            m2.add(B.encode(s), d)  # one confirmed example
            same_recall += B.predict(m2, B.encode(s), -1e18)[0] == d
            confirmed.append((s, d, fi))
        # fresh transfer: NEW unseen items, same intents + eval families, fresh rng draws
        tr_ok = tr_n = 0
        for s, d, fi in confirmed:
            fam = B.EVAL_FAM[d][fi]
            xs, ys = B.EVAL_VOCAB[d]
            fresh_items = []
            for _ in range(4):
                x = rng.choice(xs); y = rng.choice(ys) if ys[0] is not None else None
                fresh_items.append((fam(x, y), tuple(v for v in (x, y) if v is not None)))
            for fs, _ in fresh_items:
                tr_ok += B.predict(m2, B.encode(fs), -1e18)[0] == d; tr_n += 1
        # retention: teach 4 fresh examples of every OTHER intent, re-test confirmed items
        for d in B.INTENTS:
            others = [it for it in B.gen(rng, d, B.FAM[d], B.VOCAB[d], 4)]
            for s2, d2, _, _ in others: m2.add(B.encode(s2), d2)
        retention = sum(B.predict(m2, B.encode(s), -1e18)[0] == d for s, d, fi in confirmed)
        print('CONF ' + json.dumps({'seed': seed, 'winner': winner, 'conf_t': conf_t, 'n_confirmed': len(confirmed),
            'same_item_recall': f'{same_recall}/{len(confirmed)}',
            'fresh_transfer': f'{tr_ok}/{tr_n}', 'retention_after_more_teaching': f'{retention}/{len(confirmed)}'},
            ensure_ascii=False))
        # D) collateral validation on seed 0 only + small-correction variant on every seed
        if seed == 0:
            m3 = {'nb': B.NB, 't2p': B.T2P, 'nn1': B.NN1, 'wnn': None}[winner]
            m3 = m3(B.INTENTS)
            for s, d, _, _ in train: m3.add(B.encode(s), d)
            before = {d: sum(B.predict(m3, B.encode(s), -1e18)[0] == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
            docs_before = dict(m3.docs) if hasattr(m3, 'docs') else {}
            mis = [(s, d) for s, d, _, _ in ev if B.predict(m3, B.encode(s), -1e18)[0] != d]
            for s, d in mis: m3.add(B.encode(s), d)
            after = {d: sum(B.predict(m3, B.encode(s), -1e18)[0] == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
            docs_after = dict(m3.docs)
            corrected = {d for _, d in mis}
            print('COLLATERAL ' + json.dumps({'seed': 0, 'arm': winner, 'n_corrections': len(mis),
                'corrected_intents': sorted(corrected),
                'docs_before': docs_before, 'docs_after': docs_after,
                'acc_before': before, 'acc_after': after,
                'degr_points_uncorrected': {d: round(100 * max(0, before[d] - after[d]), 1) for d in B.INTENTS if d not in corrected}},
                ensure_ascii=False))
        # small-correction variant (dialogue-realistic: 3 corrections)
        m4 = {'wnn': lambda: B.WNN(B.INTENTS, seed, bleach=taus['wnn'][1]), 'nb': lambda: B.NB(B.INTENTS),
              't2p': lambda: B.T2P(B.INTENTS), 'nn1': lambda: B.NN1(B.INTENTS)}[winner]()
        for s, d, _, _ in train: m4.add(B.encode(s), d)
        mis4 = [(s, d) for s, d, _, _ in ev if B.predict(m4, B.encode(s), -1e18)[0] != d][:3]
        before4 = {d: sum(B.predict(m4, B.encode(s), -1e18)[0] == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
        for s, d in mis4: m4.add(B.encode(s), d)
        after4 = {d: sum(B.predict(m4, B.encode(s), -1e18)[0] == d for s, dd, g, _ in ev if dd == d) / 8 for d in B.INTENTS}
        corr4 = {d for _, d in mis4}
        degr4 = [max(0, before4[d] - after4[d]) for d in B.INTENTS if d not in corr4]
        print('SMALLCORR ' + json.dumps({'seed': seed, 'arm': winner, 'n': len(mis4),
            'degr_points': [round(100 * x, 1) for x in degr4],
            'mean_degr_points': round(100 * sum(degr4) / max(len(degr4), 1), 2)}, ensure_ascii=False))
    print('DONE')
