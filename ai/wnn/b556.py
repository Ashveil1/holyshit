"""B-556 harness: composition through is-a (pre-registered in LEDGER 2026-10-25).
Nonce words; live memory; provenance checked per hop."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, '' if cond else str(detail)[:200], flush=True)
    if not cond: FAILS.append(cid)

h = HSML(seed=0)
# C1: first hop inherited
h.hear('มอล์ท เป็น วินท์'); h.hear('วินท์ มี โพล่'); h.hear('โพล่ มี เมิร์ก')
r = h.hear('มอล์ท มี อะไรที่มี เมิร์ก')
check('C1', r['kind'] == 'composed' and r['text'] == 'มอล์ท มี โพล่ และ โพล่ มี เมิร์ก'
      and r['prov'] == [('โพล่', ('inherited', 'วินท์'), ('own', None))], r)
# C2: second hop inherited
h.hear('แพลท มี ช้อ') ; h.hear('ช้อ เป็น ดริบ'); h.hear('ดริบ มี ฟลั่ม')
r = h.hear('แพลท มี อะไรที่มี ฟลั่ม')
check('C2', r['kind'] == 'composed' and r['text'] == 'แพลท มี ช้อ และ ช้อ มี ฟลั่ม'
      and r['prov'] == [('ช้อ', ('own', None), ('inherited', 'ดริบ'))], r)
# C3: prefer own over inherited for the same z
h.hear('สเก้า มี วิ้ง'); h.hear('สเก้า เป็น บร็อก'); h.hear('บร็อก มี วิ้ง'); h.hear('วิ้ง มี แคล่')
r = h.hear('สเก้า มี อะไรที่มี แคล่')
check('C3', r['kind'] == 'composed' and r['prov'] == [('วิ้ง', ('own', None), ('own', None))], r)
# C4: retract ancestor attr -> chain breaks
h.hear('ไม่ใช่ วินท์ มี โพล่')
r = h.hear('มอล์ท มี อะไรที่มี เมิร์ก')
check('C4', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
# C5: three-hop with an is-a hop in the middle
h.hear('โบ๊ะ มี แก๊บ'); h.hear('แก๊บ เป็น ฮั่น'); h.hear('ฮั่น มี ลิโม่'); h.hear('ลิโม่ มี จ๊อก')
r = h.hear('โบ๊ะ มี อะไรที่มี ลิโม่ ที่มี จ๊อก')
check('C5', r['kind'] == 'composed3' and r['text'] == 'โบ๊ะ มี แก๊บ และ แก๊บ มี ลิโม่ และ ลิโม่ มี จ๊อก'
      and r['prov'] == [('แก๊บ', ('own', None), ('inherited', 'ฮั่น'), ('own', None))], r)
# C6: EN twin
h.hear('ปั๊ม ภาษาอังกฤษคือ pum'); h.hear('ก๊อบ ภาษาอังกฤษคือ gob'); h.hear('ชิ้น ภาษาอังกฤษคือ chin'); h.hear('เบล่ ภาษาอังกฤษคือ bel')
h.hear('ปั๊ม เป็น ก๊อบ'); h.hear('ก๊อบ มี ชิ้น'); h.hear('ชิ้น มี เบล่')
r = h.hear('what does pum have that has bel')
check('C6', r['kind'] == 'composed' and r['text'] == 'pum has ชิ้น and ชิ้น has bel'
      and r['prov'] == [('ชิ้น', ('inherited', 'ก๊อบ'), ('own', None))], r)
# C7: is-a cycle does not hang or crash
h2 = HSML(seed=0)
h2.hear('เอ็ก เป็น วาย'); h2.hear('วาย เป็น เอ็ก'); h2.hear('วาย มี แซด'); h2.hear('แซด มี คิว')
r = h2.hear('เอ็ก มี อะไรที่มี คิว')
check('C7', r['kind'] == 'composed' and r['zs'] == ['แซด'], r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
