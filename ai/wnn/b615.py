"""B615 fixed development relation contrasts. Original lotus unchanged."""
import json
from hsml_chat import fresh_chat,PART1,PART2
from b611 import stores,force

def unchanged(c,line):
 b=stores(c);w=c.writes;a=c.write_attempts;r=c.user_turn(line)
 return r,stores(c)==b and c.writes==w and c.write_attempts==a

def lotus(disable=False):
 c=fresh_chat()
 if disable:c._relation_compatible=lambda s,d:True
 for s in PART1+PART2[:PART2.index('บัวมีกลีบไหม')]:c.user_turn(s)
 r=c.user_turn('บัวมีกลีบไหม')
 if c.pending:r=c.user_turn('ใช่')
 return r

if __name__=='__main__':
 rows=[]
 for x in ['Q0','Q1','Q2','Q3']:
  for verb,other,d in [('เป็น','แมว','is_a_q'),('มี','หาง','ask_attr')]:
   c=fresh_chat();c.isa[x].add('แมว');c.attr[x].add('หาง')
   for line,want in [(f'{x} {verb} {other} ไหม',d)]:
    r,safe=unchanged(c,line);p=c.pending
    correct=bool(p and p['intent']==want)
    if p:r=c.user_turn('ใช่')
    rows.append({'case':line,'correct_intent':correct,'safe':safe,'answer':r,'answer_correct':r.startswith('ใช่')})
   c=fresh_chat();c.isa[x].add('แมว');c.attr[x].add('หาง')
   crossed='หาง' if verb=='เป็น' else 'แมว'
   r,safe=unchanged(c,f'{x} {verb} {crossed} ไหม');p=c.pending
   correct=bool(p and p['intent']==d)
   if p:r=c.user_turn('ใช่')
   rows.append({'case':'crossed '+x+verb,'correct_intent':correct,'safe':safe,'answer':r,'answer_correct':r.startswith('ไม่รู้ว่า')})
  for line,d in [(f'{x} เป็น แมว','teach_isa'),(f'{x} มี หาง','teach_attr')]:
   c=fresh_chat();r,safe=unchanged(c,line)
   rows.append({'case':line,'correct_intent':bool(c.pending and c.pending['intent']==d),'safe':safe,'answer_correct':True})
 c=fresh_chat();force(c,'Q9 มี หาง ไหม',d='is_a_q')
 r,safe=unchanged(c,'Q9 มี หาง ไหม');wrong_pressure=bool(c.pending and c.pending['intent']=='ask_attr') and safe
 c=fresh_chat();force(c,'Q9 มี หาง ไหม',d='is_a_q');snap=c.snapshot();c=fresh_chat();c.restore(snap)
 r,safe=unchanged(c,'Q9 มี หาง ไหม');restore_ok=bool(c.pending and c.pending['intent']=='ask_attr') and safe
 c=fresh_chat();r,safe=unchanged(c,'Q9 เป็น แมว มี หาง ไหม');mixed=safe and c.pending is None
 original=lotus();control=lotus(True)
 result={'rows':rows,'lotus':original,'original_expectation':original=='ใช่ บัว มี กลีบ',
         'disabled_control':control,'control_reproduces':control=='ไม่รู้ว่า บัว เป็น กลีบ ยังไม่เคยถูกสอน',
         'forced_wrong_family':wrong_pressure,'restored_wrong_family':restore_ok,'mixed_clarifies':mixed}
 print('RESULTS '+json.dumps(result,ensure_ascii=False))
 ok=all(r['correct_intent'] and r['safe'] and r['answer_correct'] for r in rows) and all(result[k] for k in ['original_expectation','control_reproduces','forced_wrong_family','restored_wrong_family','mixed_clarifies'])
 print('CHECK PASS' if ok else 'CHECK FAIL')
