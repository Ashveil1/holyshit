"""B-551 harness: bounded three-hop verified composition (pre-registered in LEDGER
2026-10-25). Fresh nonce words only, verification-gate assertions, per-hop broken
chains, mid-chain retraction, bilingual twin."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
def hear(s): return h.hear(s)

X, A, A2, Y, Z = 'ซูโม่', 'กาเฟ่', 'ลาเต้', 'ม็อกก้า', 'โมจิ'
# C3b: nothing taught at all -> unknown
r = hear(f'{X} มี อะไรที่มี {Y} ที่มี {Z}')
check('C3b', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
# C3a: X-A and A-Y taught, Y-Z missing -> unknown
hear(f'{X} มี {A}'); hear(f'{A} มี {Y}')
r = hear(f'{X} มี อะไรที่มี {Y} ที่มี {Z}')
check('C3a', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
# C1: teach Y-Z -> composed naming A
hear(f'{Y} มี {Z}')
r = hear(f'{X} มี อะไรที่มี {Y} ที่มี {Z}')
ok = (r['kind'] == 'composed3' and r['as_'] == [A]
      and r['text'] == f'{X} มี {A} และ {A} มี {Y} และ {Y} มี {Z}')
check('C1', ok, r)
# C2: second candidate A2 also chaining X-A2-Y... needs A2-Y; Y-Z shared
hear(f'{X} มี {A2}'); hear(f'{A2} มี {Y}')
r = hear(f'{X} มี อะไรที่มี {Y} ที่มี {Z}')
ok = (r['kind'] == 'composed3' and sorted(r['as_']) == sorted([A, A2])
      and ' / ' in r['text'])
check('C2', ok, r)
# C3c: fresh X2 with X2-A3 taught but A3-Y missing
X2, A3 = 'โยกะ', 'พิลา'
hear(f'{X2} มี {A3}')
r = hear(f'{X2} มี อะไรที่มี {Y} ที่มี {Z}')
check('C3c', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
# C4: retract A-Y mid-chain -> A drops out; A2 still chains
r = hear(f'ไม่ใช่ {A} มี {Y}')
check('C4-retract', r['kind'] == 'retracted', r)
r = hear(f'{X} มี อะไรที่มี {Y} ที่มี {Z}')
ok = (r['kind'] == 'composed3' and r['as_'] == [A2])
check('C4', ok, r)
# C4b: retract the last A2-Y -> nothing left -> unknown
hear(f'ไม่ใช่ {A2} มี {Y}')
r = hear(f'{X} มี อะไรที่มี {Y} ที่มี {Z}')
check('C4b', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
# Bilingual twin: fresh system, English surfaces linked to Thai canonicals
h2 = HSML(seed=0)
def hear2(s): return h2.hear(s)
hear2('ปูม่า ภาษาอังกฤษคือ puma'); hear2('โคอาลา ภาษาอังกฤษคือ koala')
hear2('วอมแบท ภาษาอังกฤษคือ wombat'); hear2('คว็อกก้า ภาษาอังกฤษคือ quokka')
hear2('ปูม่า มี โคอาลา'); hear2('โคอาลา มี วอมแบท'); hear2('วอมแบท มี คว็อกก้า')
r = hear2('what does puma have that has wombat that has quokka')
ok = (r['kind'] == 'composed3' and r['as_'] == ['โคอาลา']
      and r['text'] == 'puma has โคอาลา and โคอาลา has wombat and wombat has quokka')
check('EN1', ok, r)
r = hear2('what does puma have that has quokka that has wombat')
check('EN-broken', r['kind'] == 'compose_unknown' and r['text'] == 'unknown', r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
