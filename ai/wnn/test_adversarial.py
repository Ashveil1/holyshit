import sys,json,tempfile,time
from pathlib import Path
import learner
from hsml import HSML
P=Path(__file__).resolve().parent;rows=[]
def test(k,ok):
 if not ok:raise AssertionError(k)
 rows.append(k)
def learned(name,pairs):
 h=HSML();h.hear('วิธีนี้ชื่อ '+name)
 for x,y in pairs:h.hear(f'ถ้า n เป็น {x} ตอบ {y}')
 return h
pairs=[(7,14),(2,4),(10,20)]
for name,pp in [('รัน',pairs),('สองเท่า',pairs),('ไม่ใช่คูณสอง',list(reversed(pairs)))]:
 h=learned(name,pp)
 for x in [0,1,-1,97,123456]:
  r=h.hear(f'{name} ของ {x} คืออะไร');test(name+str(x),r['kind']=='conditional_prediction'and r['prediction']['value']==2*x)
 test('bounded'+name,h.hear(f'{name} ของ 10000000000 คืออะไร')['kind']=='outside_domain')
 test('fraction'+name,h.hear(f'{name} ของ 1.5 คืออะไร')['kind']=='outside_domain')
# Arbitrary counterexample rule 2x+(x-7)(x-2)(x-10) agrees allthree but not97.
# It must NOT be given to learner or misrepresented as eliminated by limitedgrammar.
h=learned('กรอบ',pairs);r=h.hear('กรอบ ของ 97 คืออะไร');test('conditional not universal',r['kind']=='conditional_prediction'and'ยังไม่ยืนยันเจตนา'in r['text']);test('no hidden target fed',h.learning['กรอบ']['pairs']==[[7,14],[2,4],[10,20]])
q=learned('คลุม',[(2,4)]);r=q.hear('คลุม ของ 97 คืออะไร');test('separating request',r['kind']=='ambiguous'and'ask_input'in r['prediction'])
# Unsupported samples differ from grammar, must not fit lookup mapping to answer query.
q=learned('นอก',[(0,0),(1,1),(2,4),(3,9)]);test('unsupported abstains',q.hear('นอก ของ 97 คืออะไร')['kind']=='no_candidate_within_budget')
# Evidence duplicate contradiction regardless order
for pp in [[(2,4),(2,5)],[(2,5),(2,4)]]:
 q=learned('ชน',pp);test('conflict order',q.hear('ชน ของ 97 คืออะไร')['kind']=='conflicting_examples')
# Save/reload candidate cache with trace and graph positive-negative conflict
with tempfile.TemporaryDirectory()as d:
 q=learned('เริ่ม',pairs);a=q.hear('เริ่ม ของ 97 คืออะไร');q.save(d+'/m');q=HSML.load(d+'/m');b=q.hear('เริ่ม ของ 97 คืออะไร');test('candidate survives',a['prediction']==b['prediction'])
 for s in ['นก มี ปีก','เหยี่ยว เป็น นก','เหยี่ยว มี ปีก','เหยี่ยว ไม่มี ปีก']:q.hear(s)
 q.save(d+'/m');q=HSML.load(d+'/m');test('ancestor conflict unknown',q.hear('เหยี่ยว มี ปีก ไหม')['answer']=='conflict')
test('semantic dedup exact',learner.coefficients(['add','x','x'])==(2,0))
h=learned('ซ้ำ',pairs);h.hear('วิธีนี้ชื่อ ซ้ำ');test('rename resumes not erases',h.learning['ซ้ำ']['pairs']==[[7,14],[2,4],[10,20]])
r={'pass':rows,'count':len(rows),'generalization_scope':'designed add/sub7node expression search; conditional underexplored grammar, not unrestricted intent','no_source_training':True};(P/'adversarial_result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False))
