"""B-609: guard coverage on every mutating path; UNK spans block; repeat-path
truth. Pre-registered in LEDGER.md B-609. Executable negative controls with
store + write-counter assertions. Usage: python3 b609.py"""
import json, sys, os
from hsml_chat import fresh_chat

def teach(c, line):
    c.user_turn(line); c.user_turn('ใช่')

def fresh():
    c = fresh_chat()
    teach(c, 'วัวเป็นสัตว์เลี้ยง')
    return c

results = {}
c = fresh()
# N1: quoted high-margin unassisted write attempt -> blocked, counter unchanged
w0 = c.writes
c.user_turn('วัวเป็นสัตว์เลี้ยง'); c.user_turn('วัวเป็นสัตว์เลี้ยง'); c.user_turn('วัวเป็นสัตว์เลี้ยง')
r = c.user_turn('เขาบอกว่าวัวเป็นสัตว์เลี้ยง')
results['N1_reply'] = r
results['N1_quoted_high_margin_blocked'] = (c.writes == w0 and 'เขา' in r)

# N2: quoted surface with UNK span -> blocked AND reply names a span
c2 = fresh()
w0 = c2.writes
r = c2.user_turn('เขาพูดเรื่องวัวเป็นสัตว์เลี้ยงเมื่อวาน')
results['N2_reply'] = r
results['N2_blocked'] = c2.writes == w0 and 'ยังไม่เข้าใจ' in r

# N3: repeat of a DECLINED turn -> not 'รู้อยู่แล้ว'
c3 = fresh()
r1 = c3.user_turn('เป็ดเป็นนกมาก')
r2 = c3.user_turn('เป็ดเป็นนกมาก')
results['N3_first'] = r1
results['N3_repeat'] = r2
results['N3_not_known_already'] = 'รู้อยู่แล้ว' not in r2

# N4: post-RESTORE quoted write attempt -> blocked
c4 = fresh()
c4.user_turn('วัวเป็นสัตว์เลี้ยง'); c4.user_turn('วัวเป็นสัตว์เลี้ยง')
snap = c4.snapshot()
c5 = fresh_chat(); c5.restore(snap)
w0 = c5.writes
r = c5.user_turn('เขาบอกว่าวัวเป็นสัตว์เลี้ยง')
results['N4_post_restore_blocked'] = c5.writes == w0 and 'เขา' in r

# N5: unmarked question -> no mutating write
c7 = fresh()
w0 = c7.writes
r = c7.user_turn('มิโลเป็นแมวไหม')
results['N5_reply'] = r
results['N5_unmarked_q_no_write'] = c7.writes == w0

# P1: ordinary confirmed teach still writes
c8 = fresh()
w0 = c8.writes
teach(c8, 'มิโลเป็นแมว')
results['P1_confirm_teach_writes'] = c8.writes == w0 + 1 and 'แมว' in c8.isa.get('มิโล', set())

# P2: repeat of a committed teach -> literal repeat (seen semantics preserved)
c10 = fresh()
teach(c10, 'มิโลเป็นแมว')
r = c10.user_turn('มิโลเป็นแมว')
results['P2_repeat_committed'] = r
results['P2_repeat_known'] = 'รู้อยู่แล้ว' in r

print('RESULTS ' + json.dumps(results, ensure_ascii=False, default=str))
ok = (results['N1_quoted_high_margin_blocked'] and results['N2_blocked']
      and results['N3_not_known_already'] and results['N4_post_restore_blocked']
      and results['N5_unmarked_q_no_write'] and results['P1_confirm_teach_writes']
      and results['P2_repeat_known'])
print('CHECK PASS' if ok else 'CHECK FAIL')
