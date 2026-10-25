"""B-555 harness: inheritance-aware reverse query with provenance
(pre-registered in LEDGER 2026-10-25). Nonce words; live memory; dedup."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
def hear(s): return h.hear(s)

# C1: own + inherited with provenance
hear('มอล์ท มี กริบ'); hear('มอล์ท เป็น วินท์'); hear('วินท์ มี โพล่')
r = hear('มอล์ท มี อะไรบ้าง')
check('C1', r['kind'] == 'attr_list' and r['text'] == 'มอล์ท มี กริบ และจาก วินท์: โพล่', r)
# C2: no own attrs, inherited only
hear('แพลท เป็น วินท์')
r = hear('แพลท มี อะไรบ้าง')
check('C2', r['kind'] == 'attr_list' and r['text'] == 'แพลท มีจาก วินท์: โพล่', r)
# C3: dedup own vs inherited
hear('ดร็อป มี โพล่'); hear('ดร็อป เป็น วินท์')
r = hear('ดร็อป มี อะไรบ้าง')
check('C3', r['kind'] == 'attr_list' and r['text'] == 'ดร็อป มี โพล่', r)
# C4: two ancestors, BFS order (parent before grandparent)
hear('วินท์ เป็น ควอลท์'); hear('ควอลท์ มี เมิร์ก')
r = hear('มอล์ท มี อะไรบ้าง')
check('C4', r['kind'] == 'attr_list' and r['text'] == 'มอล์ท มี กริบ และจาก วินท์: โพล่ และจาก ควอลท์: เมิร์ก', r)
# C5: retract parent attr -> inherited group disappears
hear('ไม่ใช่ วินท์ มี โพล่')
r = hear('แพลท มี อะไรบ้าง')
check('C5', r['kind'] == 'attr_list' and r['text'] == 'แพลท มีจาก ควอลท์: เมิร์ก', r)
# C7: is-a via synonym surface
hear('เฟริก กับ มอล์ท คือคำเดียวกัน')
r = hear('เฟริก มี อะไรบ้าง')
check('C7', r['kind'] == 'attr_list' and 'ควอลท์' in r['text'], r)
# C6: EN twin
h2 = HSML(seed=0)
def hear2(s): return h2.hear(s)
hear2('ปั๊ม ภาษาอังกฤษคือ pum'); hear2('ก๊อบ ภาษาอังกฤษคือ gob')
hear2('ปั๊ม มี ชิ้น'); hear2('ปั๊ม เป็น ก๊อบ'); hear2('ก๊อบ มี เบล่')
r = hear2('what does pum have')
check('C6', r['kind'] == 'attr_list' and r['text'] == 'pum has ชิ้น and from ก๊อบ: เบล่', r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
