"""B-548 harness: bounded two-hop composition (pre-registered in LEDGER 2026-10-25).
Fresh nonce words only (no seed-corpus overlap), held-out question strings,
verification-gate assertions, retraction, bilingual twin, ambiguity."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
inputs = []  # every sentence ever heard (for the never-input assertion)
memcount = lambda: sum(len(r) for r in h.mem.attrs.C.values())

def hear(s):
    inputs.append(s)
    return h.hear(s)

A, B, B2, C, D, U = 'ซูโม่', 'ฟา', 'โลโม่', 'ทริบ', 'เจ', 'วิ'
# C3a: broken chain - A มี B taught, nothing holds C
r = hear(f'{A} มี {B}'); assert r['kind'] == 'observed', r
r = hear(f'{A} มี อะไรที่มี {C}')
check('C3a', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
# C1: teach B มี C -> composed answer naming B
hear(f'{B} มี {C}')
r = hear(f'{A} มี อะไรที่มี {C}')
ok = (r['kind'] == 'composed' and r['zs'] == [B]
      and r['text'] == f'{A} มี {B} และ {B} มี {C}'
      and r['text'] not in inputs                     # surface string never input
      and h.mem.attrs.holds(A, B) and h.mem.attrs.holds(B, C))  # every link verified
check('C1', ok, r)
# C2: second independent path -> both listed
hear(f'{A} มี {B2}'); hear(f'{B2} มี {C}')
r = hear(f'{A} มี อะไรที่มี {C}')
check('C2', r['kind'] == 'composed' and sorted(r['zs']) == sorted([B, B2])
      and all(h.mem.attrs.holds(A, z) and h.mem.attrs.holds(z, C) for z in r['zs']), r)
# C3b: D มี C taught but A มี D never taught -> D never appears; unknown A -> ไม่รู้
hear(f'{D} มี {C}')
r = hear(f'{A} มี อะไรที่มี {C}')
check('C3b', r['kind'] == 'composed' and D not in r['zs'], r)
r = hear(f'{U} มี อะไรที่มี {C}')
check('C3b2', r['kind'] == 'compose_unknown', r)
# C4: retraction removes the path; full retraction -> ไม่รู้; re-teach restores
hear(f'{B} ไม่มี {C}')
r = hear(f'{A} มี อะไรที่มี {C}')
check('C4a', r['kind'] == 'composed' and r['zs'] == [B2] and B not in r['text'], r)
hear(f'{B2} ไม่มี {C}')
r = hear(f'{A} มี อะไรที่มี {C}')
check('C4b', r['kind'] == 'compose_unknown', r)
hear(f'{B} มี {C}'); hear(f'{B2} มี {C}')
r = hear(f'{A} มี อะไรที่มี {C}')
check('C4c', r['kind'] == 'composed' and sorted(r['zs']) == sorted([B, B2]), r)
# C5: unknown word slots -> ไม่รู้; queries store nothing
before = memcount()
r1 = hear(f'{A} มี อะไรที่มี ไม่เคยได้ยิน')
r2 = hear('ไม่เคยได้ยิน มี อะไรที่มี ' + C)
check('C5a', r1['kind'] == 'compose_unknown' and r2['kind'] == 'compose_unknown', (r1, r2))
check('C5b', memcount() == before and 'อะไรที่มี' not in h.mem.attrs.vocab()
      and 'ไม่เคยได้ยิน' not in h.mem.attrs.names(), (before, memcount()))
# C6: bilingual twin via taught links; ambiguity abstains naming candidates
hear(f'{A} ภาษาอังกฤษคือ zumo'); hear(f'{C} ภาษาอังกฤษคือ trip')
r = hear('what does zumo have that has trip')
check('C6a', r['kind'] == 'composed' and sorted(r['zs']) == sorted([B, B2])
      and 'zumo has' in r['text'] and 'has trip' in r['text'], r)
hear(f'{B} ภาษาอังกฤษคือ bond'); hear(f'{B2} ภาษาอังกฤษคือ bond')
r = hear('what does bond have that has trip')
check('C6b', r['kind'] == 'abstain' and r['source'] == 'link_ambiguous'
      and B in r['text'] and B2 in r['text'], r)
hear(f'{B2} ภาษาอังกฤษไม่ใช่ bond')   # resolve ambiguity -> bond = B
r = hear('does bond have trip')
check('C6c', r['kind'] == 'yesno' and r['text'] == 'yes', r)
# guarded slots
r = hear('กี่ตัว มี อะไรที่มี ' + C)
check('guard', r['kind'] == 'abstain', r)

print('RESULT:', 'PASS' if not FAILS else f'FAIL {FAILS}', flush=True)
sys.exit(1 if FAILS else 0)
