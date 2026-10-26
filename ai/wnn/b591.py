"""B-591: example-pair definitions - user teaches pattern by one pair.
SUPPLIED aligner compiles (surface -> canonical) with variables at differing
token positions. Usage: python3 b591.py
"""
import json, time
import b562 as B
from b562_diag import build
from b564 import NBu
from b565 import learn_s4
from b566 import _select, assign_a0
from b570 import Watchdog, BUDGET, TIMEOUT_S
from b574 import pick_tau_precision
from b588 import Shell2

def align_compile(surface, canonical):
    """Differing positions (aligned by index after longest common tokens) ->
    variables shared by name. SUPPLIED aligner: positional on equal lengths,
    else fail."""
    st, ct = surface.split(), canonical.split()
    if len(st) != len(ct): return None
    varmap = {}; pat_s = []; pat_c = []
    for a, b in zip(st, ct):
        if a == b: pat_s.append(a); pat_c.append(b)
        else:
            if a not in varmap: varmap[a] = 'V%d' % len(varmap)
            v = varmap[a]
            if b not in varmap.values(): varmap[b] = v
            pat_s.append(v); pat_c.append(v if varmap.get(b) == v else varmap.setdefault(b, v))
    # ensure both sides use same variable per pair
    pairs = {}
    ok = True
    ps, pc = [], []
    for a, b in zip(st, ct):
        if a == b: ps.append(a); pc.append(b); continue
        k = (a, b)
        if a in pairs and pairs[a] != b: ok = False; break
        if b in pairs.values() and pairs.get(a) != b: ok = False; break
        pairs[a] = b
        ps.append('?' + a); pc.append('?' + a)
    if not ok: return None
    return (ps, pc)

def fire(rule, s):
    ps, pc = rule
    toks = s.split()
    if len(toks) != len(ps): return None
    bind = {}
    for p, t in zip(ps, toks):
        if p.startswith('?'):
            bind[p[1:]] = t
        elif p != t: return None
    return [bind.get(c[1:], c) if c.startswith('?') else c for c in pc]

if __name__ == '__main__':
    watchdog = Watchdog(BUDGET); watchdog.start()
    t_start = time.time()
    rng, train, dev, ev, ev_wrong, arms0, taus0, pred0 = build(0)
    m = NBu(B.INTENTS)
    for s, d, _, _ in train: m.add(B.encode(s), d)
    tau_hi, _ = pick_tau_precision(m, dev)
    fn0, anchor0, offstat0, rolepos0 = learn_s4(train)
    extract = lambda s, d: assign_a0(*_select(s, d, fn0, anchor0, offstat0, B.NSLOTS[d]), B.NSLOTS[d])
    sh = Shell2(m, tau_hi, 1.0, extract)
    rules = []
    definitions = [
        ('แมวตัวนี้ชื่อมิโลนะ', 'มิโล เป็น แมว'),       # 'Xตัวนี้ชื่อYนะ' won't align (len 1 vs 3) -> expect compile FAIL (honest)
        ('นก มี ปีก ด้วยนะ', 'นก มี ปีก'),               # teach_attr variant, len 4 vs 2 -> FAIL
        ('กวาง มี เขา จริงๆ', 'กวาง มี เขา'),            # len 4 vs 3 -> FAIL
    ]
    # note: length-mismatch pairs cannot be compiled by the positional aligner - measured as failures
    results = []
    for surf, canon in definitions:
        r = align_compile(surf, canon)
        results.append({'definition': [surf, canon], 'compiled': r is not None})
    # equal-length workable definitions
    workable = [
        ('เหยี่ยว น่ะ เป็น นก', 'เหยี่ยว เป็น นก'),       # X น่ะ เป็น Y -> X เป็น Y
        ('แพะ ก็ มี เขา', 'แพะ มี เขา'),                   # X ก็ มี Y -> X มี Y
    ]
    for surf, canon in workable:
        r = align_compile(surf, canon)
        results.append({'definition': [surf, canon], 'compiled': r is not None})
        if r: rules.append((r, canon))
    cases = [
        ('กวาง น่ะ เป็น สัตว์', 'fire', 'เหยี่ยว-rule novel instance'),
        ('ม้า ก็ มี ขน', 'fire', 'แพะ-rule novel instance'),
        ('กวาง น่ะ มี เขา', 'nofire', 'near-miss: น่ะ with มี (rule says เป็น)'),
        ('ม้า ก็ เป็น เป็ด', 'nofire', 'near-miss: ก็ with เป็น (rule says มี)'),
        ('กวาง น่ะ เป็น นก', 'fire', 'second novel instance'),
    ]
    for s, expect, note in cases:
        hit = None
        for rule, canon in rules:
            out = fire(rule, s)
            if out: hit = ' '.join(out); break
        fired = hit is not None
        ok = (fired == (expect == 'fire'))
        acted = None
        if fired:
            p, mg = B.predict(m, B.encode(hit), -1e18)
            acted = p
        results.append({'case': s, 'expect': expect, 'fired': fired, 'ok': ok,
                        'canonical': hit, 'mapper_intent_on_canonical': acted, 'note': note})
    print('ROW ' + json.dumps({'results': results}, ensure_ascii=False))
    watchdog.stop()
    print('RES-FINAL ' + json.dumps({'peak_rss_mb_overall': round(watchdog.peak / 1e6, 1), 'wall_seconds': round(time.time() - t_start, 1)}))
    print('DONE')
