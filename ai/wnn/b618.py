"""Repeated query current-answer and persistence checks."""
import json
from hsml_chat import fresh_chat

def ask(c,s):
 r=c.user_turn(s)
 if c.pending and c.pending.get('kind')=='confirm':r=c.user_turn('ใช่')
 return r

def case(intent):
 c=fresh_chat();s='มิโล เป็น แมว ไหม' if intent=='is_a_q' else 'บัว มี กลีบ ไหม'
 slots=('มิโล','แมว') if intent=='is_a_q' else ('บัว','กลีบ')
 store=c.isa if intent=='is_a_q' else c.attr
 # Seed an actual prior executed query, not a synthetic answer cache.
 c._commit(s,intent,slots,'diagnostic')
 r0=ask(c,s);unknown=r0.startswith('ไม่รู้ว่า')
 store[slots[0]].add(slots[1]);w=c.writes;a=c.write_attempts
 r1=ask(c,s);known=r1.startswith('ใช่')
 snap=c.snapshot();d=fresh_chat();d.restore(snap)
 r2=ask(d,s);restart=r2.startswith('ใช่')
 (d.isa if intent=='is_a_q' else d.attr)[slots[0]].discard(slots[1])
 r3=ask(d,s);retracted=r3.startswith('ไม่รู้ว่า')
 return {'intent':intent,'replies':[r0,r1,r2,r3],'unknown':unknown,'known':known,
         'restart':restart,'retracted':retracted,'no_write':c.writes==w and c.write_attempts==a and d.writes==d.write_attempts==0}
if __name__=='__main__':
 rows=[case(d) for d in ['is_a_q','ask_attr']]
 print('RESULTS '+json.dumps(rows,ensure_ascii=False))
 print('CHECK PASS' if all(all(r[k] for k in ['unknown','known','restart','retracted','no_write']) for r in rows) else 'CHECK FAIL')
