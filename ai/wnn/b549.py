"""B-549 harness: learn-while-chatting confidence separation + natural corrections
(pre-registered in LEDGER 2026-10-25)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
memcount = lambda: sum(len(r) for r in h.mem.attrs.C.values())

# C1: every Thai marker variant stores nothing; yes/no afterwards -> ไม่รู้
markers = ['อาจจะ', 'อาจ', 'น่าจะ', 'คงจะ', 'ไม่แน่ใจ', 'มั้ง']
ok = True
for i, mk in enumerate(markers):
    name, attr = f'ตัว{i}', f'สิ่ง{i}'
    r = h.hear(f'{mk} {name} มี {attr}') if mk != 'มั้ง' else h.hear(f'{name} มี {attr} {mk}')
    if r['kind'] != 'uncertain_not_stored': ok = False; print('  bad-ack', mk, r)
    q = h.hear(f'{name} มี {attr} ไหม')
    if not (q['kind'] == 'yesno' and q['text'] == 'ไม่รู้'): ok = False; print('  bad-yesno', mk, q)
check('C1-th', ok, f'{len(markers)} markers')
# C1-en: 'maybe a bird has wings' with links -> nothing stored -> unknown
h.hear('นก ภาษาอังกฤษคือ bird'); h.hear('ปีก ภาษาอังกฤษคือ wings')
before = memcount()
r = h.hear('maybe a bird has wings')
q = h.hear('does bird have wings')
check('C1-en', r['kind'] == 'uncertain_not_stored' and memcount() == before
      and q['kind'] == 'yesno' and q['text'] == 'unknown', (r, q))
# C2: marker tokens never enter vocab/names; ack is never 'จำไว้แล้ว'
v = h.mem.attrs.vocab(); ns = h.mem.attrs.names()
check('C2', not any(m in v or m in ns for m in list(markers) + ['maybe']), 'vocab/names clean')
# C3: natural correction
h.hear('ฟา มี ทริบ')
r = h.hear('ไม่ใช่ ฟา มี ทริบ')
q = h.hear('ฟา มี ทริบ ไหม')
check('C3a', r['kind'] == 'retracted' and r.get('retracted') == ['ทริบ']
      and q['kind'] == 'yesno' and q['text'] == 'ไม่', (r, q))
r = h.hear('ไม่ใช่ ฟา มี มุก')
check('C3b', r['kind'] == 'nothing_to_retract', r)
before = memcount()
r = h.hear('ไม่ใช่ ฝนตกหนักมาก')
check('C3c', r['kind'] == 'abstain' and memcount() == before, r)
# C4: confident statement still stores; skill frames unaffected
r = h.hear('ฟา มี ทริบ')
q = h.hear('ฟา มี ทริบ ไหม')
check('C4a', r['kind'] == 'observed' and q['text'] == 'ใช่', (r, q))
r = h.hear('เลขคู่ ของ 100 คืออะไร')
check('C4b', r['kind'] == 'skill_answer' and r.get('result') == 1, r)
print('RESULT:', 'PASS' if not FAILS else f'FAIL {FAILS}', flush=True)
sys.exit(1 if FAILS else 0)
