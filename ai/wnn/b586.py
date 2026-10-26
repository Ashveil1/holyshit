"""B-586: WHY does the precision gate refuse seen items? Margin-scale
diagnostic + one bounded representation variant: length-normalized scores
(average log-likelihood per feature) for BOTH mapper and gate.
Diagnostic + variant, labeled. Usage: python3 b586.py
"""
import json, time, math
import b562 as B
from b562_diag import build
from b564 import NBu, NEW_EVAL_FAM
from b565 import learn_s4, FRESH3_FAM, EVAL_VOCAB2
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision

class NBn(NBu):
    """NBu with per-feature-average scores (length-normalized)."""
    def scores(self, feats):
        raw = super().scores(feats)
        nf = max(1, sum(feats.values()))
        return {d: s / nf for d, s in raw.items()}

def margins_of(m, items):
    out = []
    for s, d, g, fi in items:
        _, mg = B.predict(m, B.encode(s), -1e18)
        out.append((mg, d))
    return out

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    seen = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, B.FAM[d], B.VOCAB[d], 8)]
    c22 = [(s, d, g, fi) for d in B.INTENTS for (s, d, g, fi) in B.gen(rng, d, FRESH3_FAM[d], EVAL_VOCAB2[d], 8)]
    for name, cls in (('NBu_raw', NBu), ('NBn_normalized', NBn)):
        m = cls(B.INTENTS)
        for s, d, _, _ in train: m.add(B.encode(s), d)
        tau, dev_wr = pick_tau_precision(m, dev)
        ms = sorted(mg for mg, _ in margins_of(m, seen))
        mu = sorted(mg for mg, _ in margins_of(m, c22))
        n = len(ms)
        seen_pass = sum(1 for mg, _ in margins_of(m, seen) if mg >= tau)
        unseen_pass = sum(1 for mg, _ in margins_of(m, c22) if mg >= tau)
        # wrong-intent among unseen passers
        wu = 0
        for s, d, g, fi in c22:
            p, mg = B.predict(m, B.encode(s), -1e18)
            if p is not None and mg >= tau and p != d: wu += 1
        print('ROW ' + json.dumps({'arm': name, 'tau': round(tau, 4), 'dev_wrong_at_tau': round(dev_wr, 3),
            'seen_margin_median': round(ms[n//2], 3), 'unseen_margin_median': round(mu[len(mu)//2], 3),
            'seen_pass': seen_pass, 'seen_n': n,
            'unseen_pass': unseen_pass, 'unseen_n': len(c22),
            'unseen_pass_wrong_intent': wu}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
