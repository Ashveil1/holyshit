import os,sys,time,json,tempfile,statistics,subprocess
from pathlib import Path
from hsml import HSML
P=Path(__file__).resolve().parent;report={'checks':[]};times=[]
def ck(name,ok):
 if not ok:raise AssertionError(name)
 report['checks'].append(name)
def test_rule(pairs,targets,name):
 h=HSML();h.hear('วิธีนี้ชื่อ '+name)
 for x,y in pairs:
  t=time.perf_counter();h.hear(f'ถ้า n เป็น {x} ตอบ {y}');times.append(time.perf_counter()-t)
 for x,y in targets:
  t=time.perf_counter();r=h.hear(f'{name} ของ {x} คืออะไร');times.append(time.perf_counter()-t)
  ck(name+str(x),r.get('prediction',{}).get('value')==y and r['kind']=='conditional_prediction')
 return h
h=test_rule([(7,14),(2,4),(10,20)],[(97,194),(123456,246912)],'วิธีฟลอม')
r=h.hear('วิธีฟลอม ของ สิบสอง คืออะไร');ck('Thai12',r['prediction']['value']==24)
test_rule([(0,3),(1,5),(4,11)],[(97,197)],'วิธีกริม')
sq=HSML();sq.hear('วิธีนี้ชื่อ วิธีแว็ก')
for x,y in [(0,0),(2,4),(3,9)]:sq.hear(f'ถ้า n เป็น {x} ตอบ {y}')
ck('quadratic not in addsub grammar',sq.hear('วิธีแว็ก ของ 11 คืออะไร')['kind']=='no_candidate_within_budget')
test_rule([(0,5),(3,5),(10,5)],[(97,5)],'วิธีทิบ')
h2=HSML();h2.hear('วิธีนี้ชื่อ ลูม');h2.hear('ถ้า n เป็น 2 ตอบ 4');r=h2.hear('ลูม ของ 97 คืออะไร');ck('ambiguous1pair',r['kind']=='ambiguous');h2.hear('ถ้า n เป็น 2 ตอบ 5');ck('contradiction',h2.hear('ลูม ของ 97 คืออะไร')['kind']=='conflicting_examples')
# Persist after EACH accepted input, including an incomplete learner and graph/negative/synonym facts.
with tempfile.TemporaryDirectory()as d:
 f=d+'/state.pkl';q=HSML()
 for sentence in ['วิธีนี้ชื่อ ปลอม','ถ้า n เป็น 7 ตอบ 14','ถ้า n เป็น 2 ตอบ 4','ถ้า n เป็น 10 ตอบ 20','เหยี่ยว เป็น นก','นก มี ปีก','เหยี่ยว มี ฟัน','เหยี่ยว ไม่มี ฟัน','เหยี่ยว กับ hawk คือคำเดียวกัน']:
  q.hear(sentence);q.save(f);q=HSML.load(f)
 ck('3pairs durable',len(q.learning['ปลอม']['pairs'])==3)
 ck('isa durable',q.hear('เหยี่ยว มี ปีก ไหม')['text']=='ใช่')
 ck('negative durable',q.hear('เหยี่ยว มี ฟัน ไหม')['text']=='ไม่')
 ck('syn durable',q._synonyms('เหยี่ยว')=={'เหยี่ยว','hawk'})
 ck('missing not false',q.hear('ปลา มี ปีก ไหม')['text']=='ไม่รู้')
 ck('postrestart unseen',q.hear('ปลอม ของ 97 คืออะไร')['prediction']['value']==194)
 q.save(f);before=Path(f).read_bytes();q.hear('ถ้า n เป็น 2 ตอบ 99');ck('new evidence invalidates',q.hear('ปลอม ของ 97 คืออะไร')['kind']=='conflicting_examples');q.save(f)
 Path(f).write_bytes(b'broken')
 try:HSML.load(f)
 except RuntimeError:ck('corrupt fails loud',True)
 else:ck('corrupt fails loud',False)
# Fresh process coldpacked/no pickle startup. Timings include import/init/output/save.
lat=[]
for i in range(5):
 with tempfile.TemporaryDirectory()as d:
  t=time.perf_counter();p=subprocess.run([sys.executable,str(P/'chat.py'),'--memory',d+'/m.pkl'],input='2 ? 3 = 6\nquit\n',text=True,capture_output=True,timeout=3);lat.append(time.perf_counter()-t);ck('CLIexit'+str(i),p.returncode==0)
report.update(grammar='finite designed +/- expression grammar; multiplication primitive removed max7nodes, not learned language/unique intention',all_predictions_conditional=True,search_max_seconds=.15,perturn_p50=statistics.median(times),perturn_max=max(times),coldprocess_samples=lat,coldprocess_max=max(lat),test_gold_not_given_to_learner=True,limitations=['no parity/general Thai claim','exact affine coefficient semantic dedup, bounded grammar not unrestricted rules','multiplication primitive removed; add/sub are GIVEN arithmetic','seeded library from verified committed logs, not fresh learning'])
(P/'test_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
