"""B-554 harness: is-a with yes/no inheritance (pre-registered in LEDGER
2026-10-25). Nonce words; transitive BFS cap; cycle-safe; conflict -> ไม่รู้."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, detail, flush=True)
    if not cond: FAILS.append((cid, detail))

h = HSML(seed=0)
def hear(s): return h.hear(s)

# C3: no link -> ไม่รู้
hear('บร็อค มี สเฟน')
r = hear('โกลบ มี สเฟน ไหม')
check('C3', r['answer'] == 'unknown', r)
# C1: one level
r = hear('โกลบ เป็น บร็อค')
check('C1-link', r['kind'] == 'isa_stored', r)
r = hear('โกลบ มี สเฟน ไหม')
check('C1', r['answer'] == 'yes', r)
# C2: transitive two levels
hear('เทรน เป็น โกลบ')
r = hear('เทรน มี สเฟน ไหม')
check('C2', r['answer'] == 'yes', r)
# C5: uncertain is-a stores nothing
r = hear('อาจจะ มิ๊บ เป็น บร็อค')
check('C5a', r['kind'] == 'uncertain_not_stored', r)
r = hear('มิ๊บ มี สเฟน ไหม')
check('C5b', r['answer'] == 'unknown', r)
# C6: own explicit neg (via designed teach-then-correct path) + inherited positive -> conflict ไม่รู้
hear('ควิ๊บ เป็น บร็อค')
hear('ควิ๊บ มี สเฟน')
hear('ไม่ใช่ ควิ๊บ มี สเฟน')  # explicit neg recorded (B-542 path)
r = hear('ควิ๊บ มี สเฟน ไหม')
check('C6', r['answer'] == 'conflict' and r['text'] == 'ไม่รู้', r)
# C8: cycle terminates
hear('ลิ๊ก เป็น มิ๊ก'); hear('มิ๊ก เป็น ลิ๊ก')
hear('ลิ๊ก มี จ็อบ')
r = hear('มิ๊ก มี จ็อบ ไหม')
check('C8', r['answer'] == 'yes', r)
# C4: retraction
r = hear('ไม่ใช่ โกลบ เป็น บร็อค')
check('C4a', r['kind'] == 'isa_retracted', r)
r = hear('โกลบ มี สเฟน ไหม')
check('C4b', r['answer'] == 'unknown', r)
r = hear('ไม่ใช่ โกลบ เป็น บร็อค')
check('C4c', r['kind'] == 'nothing_to_retract', r)
# เทรน still inherits via โกลบ? No: เทรน->โกลบ->บร็อค; โกลบ->บร็อค removed -> เทรน loses it too
r = hear('เทรน มี สเฟน ไหม')
check('C4d', r['answer'] == 'unknown', r)
# C7: guard
r = hear('อะไร เป็น บร็อค')
check('C7', r['kind'] == 'abstain', r)
# reverse query unchanged (own attrs only, no inherited listing)
r = hear('เทรน มี อะไรบ้าง')
check('C9-reverse-bound', r['kind'] == 'abstain', r)  # nothing taught on เทรน itself

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
