"""B-591b: example-pair definitions v2 - LCS aligner + ONE follow-up
question per definition (which tokens are variable). Simulated user marks
variable SURFACE positions (derived from authored case setup). Measures:
compile success, fire on novel instances, no-fire on near-misses,
mapper action correctness on fired canonicals, questions per definition.
Usage: python3 b591b.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision

def lcs(a, b):
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1, -1, -1):
        for j in range(m-1, -1, -1):
            dp[i][j] = dp[i+1][j+1] + 1 if a[i] == b[j] else max(dp[i+1][j], dp[i][j+1])
    i = j = 0; out = []
    while i < n and j < m:
        if a[i] == b[j]: out.append((i, j)); i += 1; j += 1
        elif dp[i+1][j] >= dp[i][j+1]: i += 1
        else: j += 1
    return out

def compile_def(surface, canonical, var_positions):
    """surface/canonical: token lists; var_positions: surface indices the
    (simulated) user marked as variable. Returns (surface_pattern, canonical_builder)."""
    st, ct = surface, canonical
    pairs = lcs(st, ct)
    smap = {i: j for i, j in pairs}
    pat = []; canon = []
    for i, t in enumerate(st):
        if i in var_positions:
            if i not in smap: return None  # variable must appear in canonical
            pat.append(('VAR', i)); 
        else:
            pat.append(('TOK', t))
    # canonical builder: matched canonical tokens of variables + canonical constants
    var_canon = {i: ct[j] for i, j in pairs if i in var_positions}
    used_j = {j for i, j in pairs if i in var_positions}
    # build canonical: variables' canonical counterparts in canonical order,
    # plus unmatched canonical constants are NOT insertable (kept simple, disclosed)
    seq = []
    for i in sorted(var_positions):
        seq.append(('VAR', i))
    # constants of canonical that equal surface constants: checked at fire time via pattern match; omitted from output
    return {'pattern': pat, 'var_canon': var_canon, 'canonical_tokens': ct, 'pairs': pairs, 'var_positions': sorted(var_positions)}

def fire(rule, s):
    toks = s.split()
    pat = rule['pattern']
    if len(toks) != len(pat): return None
    out = {}
    for (kind, v), t in zip(pat, toks):
        if kind == 'TOK' and v != t: return None
        if kind == 'VAR': out[v] = t
    # build canonical: replace variable canonical positions, keep constants
    ct = list(rule['canonical_tokens'])
    for i, j in rule['pairs']:
        if i in out: ct[j] = out[i]
    return ' '.join(ct)

DEFS = [  # (surface, canonical, variable surface positions, note)
    ('เหยี่ยว น่ะ เป็น นก', 'เหยี่ยว เป็น นก', [0, 3], "'X น่ะ เป็น Y' -> teach_isa(X,Y)"),
    ('แพะ ก็ มี เขา', 'แพะ มี เขา', [0, 3], "'X ก็ มี Y' -> teach_attr(X,Y)"),
]
CASES = [
    ('กวาง น่ะ เป็น สัตว์', 'fire', ('teach_isa', ('กวาง', 'สัตว์'))),
    ('ม้า ก็ มี ขน', 'fire', ('teach_attr', ('ม้า', 'ขน'))),
    ('กวาง น่ะ มี เขา', 'nofire', None),
    ('ม้า ก็ เป็น เป็ด', 'nofire', None),
    ('เป็ด น่ะ เป็น นกน้ำ', 'fire', ('teach_isa', ('เป็ด', 'นกน้ำ'))),
    ('กวาง น่ะ เป็น สัตว์ จริงๆ', 'nofire', None),  # length differs
]

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    rules = []; q_per_def = []
    for surf, canon, varpos, note in DEFS:
        r = compile_def(surf.split(), canon.split(), varpos)
        rules.append(r) if r else None
        q_per_def.append(1)  # the one variable-marking question
        print('DEF ' + json.dumps({'def': [surf, canon], 'compiled': r is not None, 'note': note}, ensure_ascii=False))
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    from b566 import _select, assign_a0
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    ok_n = 0
    for s, expect, gold in CASES:
        hit = None
        for r in rules:
            if r and fire(r, s): hit = fire(r, s); break
        fired = hit is not None
        action_ok = None
        if fired:
            p, mg = B.predict(m, B.encode(hit), -1e18)
            sl = extract(hit, p) if p else None
            action_ok = (p, tuple(sl) if sl else None) == (gold[0], gold[1])
        ok = (fired == (expect == 'fire')) and (not fired or action_ok)
        ok_n += ok
        print('CASE ' + json.dumps({'case': s, 'expect': expect, 'fired': fired,
            'canonical': hit, 'action_correct': action_ok, 'ok': ok}, ensure_ascii=False))
    print('SUMMARY ' + json.dumps({'cases_ok': ok_n, 'cases': len(CASES),
        'defs_compiled': len(rules), 'defs_total': len(DEFS),
        'questions_per_def': q_per_def}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
