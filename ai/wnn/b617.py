"""Exact antecedent resolution diagnostic. Authored defect tests."""
import json
from hsml_chat import fresh_chat
from b611 import stores,force

def case(reply,restore=False):
 c=fresh_chat();c.attr['มิโล'].add('ปีก');c.attr['มิโลน้อย'].add('หาง')
 c.subjects=['มิโลน้อย','มิโล']
 force(c,'มิโลน้อย มี หาง ไหม','ask_attr')
 if restore:
  snap=c.snapshot();c=fresh_chat();c.restore(snap)
 first=c.user_turn('มัน มี หาง ไหม')
 before=stores(c);w=c.writes;a=c.write_attempts;counts=dict(c.m.tot)
 r=c.user_turn(reply)
 if c.pending and c.pending.get('kind')=='confirm':r=c.user_turn('ใช่')
 valid=reply in ['มิโล','มิโลน้อย']
 if valid:correct=('ใช่ มิโลน้อย มี หาง' in r) if reply=='มิโลน้อย' else ('ไม่รู้ว่า มิโล มี หาง' in r)
 else:correct=c.pending is not None and c.pending.get('kind')=='clarify' and dict(c.m.tot)==counts
 return {'selection':reply,'restore':restore,'first':first,'reply':r,'correct':correct,
         'unchanged':stores(c)==before and c.writes==w and c.write_attempts==a}
if __name__=='__main__':
 rows=[case(s,r) for s in ['มิโลน้อย','มิโล','มิโล และ มิโลน้อย','ไม่แน่ใจ'] for r in [False,True]]
 print('RESULTS '+json.dumps(rows,ensure_ascii=False))
 print('CHECK PASS' if all(r['correct'] and r['unchanged'] for r in rows) else 'CHECK FAIL')
