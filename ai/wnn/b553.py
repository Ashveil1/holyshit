"""B-553 harness: Thai synonym intake while chatting (pre-registered in LEDGER
2026-10-25). Nonce words only; direct links; union query; conflict -> ไม่รู้."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
def hear(s): return h.hear(s)

# C1: teach under X, link X=Z, query Z
hear('บลิบ มี วูป')
r = hear('บลิบ กับ ซวก คือคำเดียวกัน')
check('C1-link', r['kind'] == 'syn_stored', r)
r = hear('ซวก มี อะไรบ้าง')
check('C1', r['kind'] == 'attr_list' and r['attrs'] == ['วูป'], r)
# C2: symmetric - teach under Z, query X
hear('ซวก มี เฟล็ด')
r = hear('บลิบ มี อะไรบ้าง')
check('C2', r['kind'] == 'attr_list' and sorted(r['attrs']) == ['วูป', 'เฟล็ด'], r)
# C3: yes/no via synonym
r = hear('ซวก มี วูป ไหม')
check('C3', r['kind'] == 'yesno' and r['answer'] == 'yes', r)
# C5: uncertain synonym sentence stores nothing
r = hear('อาจจะ ปู๊ด กับ เฟิ๊ด คือคำเดียวกัน')
check('C5a', r['kind'] == 'uncertain_not_stored', r)
r = hear('ปู๊ด กับ เฟิ๊ด ไม่ใช่คำเดียวกัน')
check('C5b', r['kind'] == 'nothing_to_retract', r)
# C8: composition through a synonym hop (2-hop and 3-hop)
hear('วูป มี เกล็น'); hear('เกล็น มี ฮ็อก')
r = hear('ซวก มี อะไรที่มี เกล็น')
check('C8a', r['kind'] == 'composed' and 'วูป' in r['zs'], r)
r = hear('ซวก มี อะไรที่มี เกล็น ที่มี ฮ็อก')
check('C8b', r['kind'] == 'composed3' and 'วูป' in r['as_'], r)
# C7: retraction via synonym removes from the holding surface
r = hear('ไม่ใช่ ซวก มี วูป')
check('C7a', r['kind'] == 'retracted' and r['retracted'] == ['วูป'], r)
r = hear('บลิบ มี วูป ไหม')
check('C7b', r['kind'] == 'yesno' and r['answer'] in ('no_explicit', 'unknown'), r)
# C4: retract the link -> re-ask -> honest absence
r = hear('บลิบ กับ ซวก ไม่ใช่คำเดียวกัน')
check('C4a', r['kind'] == 'syn_retracted', r)
r = hear('ซวก มี อะไรบ้าง')
check('C4b', r['kind'] == 'attr_list' and 'วูป' not in r['attrs'], r)
r = hear('ซวก มี เฟล็ด ไหม')
check('C4c', r['kind'] == 'yesno' and r['answer'] == 'yes', r)  # own fact survives
# C6: conflict -> ไม่รู้ (fresh pair)
hear('จิ๊บ มี ล็อบ')          # taught positive under จิ๊บ
hear('จั๊บ มี ล็อบ')          # taught under จั๊บ then retract -> explicit neg
hear('จั๊บ ไม่มี ล็อบ')
hear('จิ๊บ กับ จั๊บ คือคำเดียวกัน')
r = hear('จิ๊บ มี ล็อบ ไหม')
check('C6', r['kind'] == 'yesno' and r['answer'] == 'conflict' and r['text'] == 'ไม่รู้', r)
# guard: question-stem word refused as synonym
r = hear('อะไร กับ ซวก คือคำเดียวกัน')
check('C9-guard', r['kind'] == 'abstain', r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
