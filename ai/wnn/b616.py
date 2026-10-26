"""Clarification relation fast-path audit, authored diagnostic only."""
import json
from hsml_chat import fresh_chat,PART1,PART2
from b611 import force,stores

def case(kind='has',restore=False):
 c=fresh_chat()
 if kind=='has':
  for line in PART1+PART2[:PART2.index('บัวมีกลีบไหม')]:c.user_turn(line)
 c.isa['แมว'].add('สัตว์');c.isa['หมา'].add('สัตว์')
 c.attr['แมว'].add('หาง');c.attr['หมา'].add('หาง')
 subject='บัว' if kind=='has' else 'แมว'
 c.subjects=[subject,'หมา']
 if kind=='has':c.attr['บัว'].add('กลีบ')
 line='มัน มี กลีบ ไหม' if kind=='has' else 'มัน เป็น สัตว์ ไหม'
 resolved='บัว มี กลีบ ไหม' if kind=='has' else 'แมว เป็น สัตว์ ไหม'
 force(c,resolved,'is_a_q')
 if restore:
  snap=c.snapshot();c=fresh_chat();c.restore(snap)
 b=stores(c);w=c.writes;a=c.write_attempts
 first=c.user_turn(line);pending=c.pending.copy() if c.pending else None
 reply=c.user_turn(subject)
 if c.pending and c.pending.get('kind')=='confirm':reply=c.user_turn('ใช่')
 expect='ใช่ บัว มี กลีบ' if kind=='has' else 'ใช่ แมว เป็น สัตว์'
 return {'kind':kind,'restore':restore,'first':first,'pending':pending,'reply':reply,
         'correct':reply.startswith(expect),'stores_equal':stores(c)==b,
         'writes':c.writes-w,'attempts':c.write_attempts-a}
if __name__=='__main__':
 rows=[case(k,r) for k in ['has','isa'] for r in [False,True]]
 print('RESULTS '+json.dumps(rows,ensure_ascii=False))
 print('CHECK PASS' if all(r['correct'] and r['stores_equal'] and r['writes']==r['attempts']==0 for r in rows) else 'CHECK FAIL')
