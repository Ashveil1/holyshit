from pathlib import Path
import tempfile,subprocess,sys,time,threading,json,pickle
import hsml,learner
from hsml import HSML
P=Path(__file__).resolve().parent;checks=[]
def ck(n,v):
 if not v:raise AssertionError(n)
 checks.append(n)
# B2 no thread signal crash, old data remains.
h=HSML();p,fn,_=h.mem.skills['sumto'];h.mem.skills['old']=(p,fn,{'source':'dialog'});h.hear('วิธีนี้ชื่อ old')
for x,y in [(1,2),(2,4),(3,6),(4,8)]:h.hear(f'ถ้า n เป็น {x} ตอบ {y}')
out=[];t=threading.Thread(target=lambda:out.append(h.hear('ถ้า n เป็น 5 ตอบ 10')));t.start();t.join(2);ck('thread graceful',out and out[0]['source']=='embedded_search_guard'and len(h.ctx['pairs'])==5)
# N1 old candidate cannot bypass grammar.
try:learner.evaluate(['mul','x','x'],97)
except ValueError:ck('forbidden op rejected',True)
else:ck('forbidden op rejected',False)
with tempfile.TemporaryDirectory()as d:
 h=HSML();h.hear('วิธีนี้ชื่อ raw');h.hear('ถ้า n เป็น 2 ตอบ 4');h.save(d+'/m')
 q=pickle.load(open(d+'/m','rb'));q['full_state']['learning']['raw']['result']={'status':'candidates','candidates':[['mul','x','x']],'complete':True};pickle.dump(q,open(d+'/m','wb'));r=HSML.load(d+'/m').hear('raw ของ 97 คืออะไร');ck('loaded cache regenerated',r.get('prediction',{}).get('value')!=9409)
# N3 clarification reply accepted and persistent
h=HSML();h.hear('วิธีนี้ชื่อ maybe');h.hear('ถ้า n เป็น 2 ตอบ 4');r=h.hear('maybe ของ 97 คืออะไร');q=r['prediction']['ask_input'];r=h.hear('ตอบ 7');ck('clarification reply routed',[q,7]in h.learning['maybe']['pairs'])
# N5 pure read query works but mutation refused at quota.
h=HSML();h.hear('นก มี ปีก');h.turn_provenance=[{}]*10000;ck('quota read allowed',h.hear('นก มี ปีก ไหม')['text']=='ใช่');ck('quota write refused',h.hear('นก มี ฟัน')['kind']=='memory_quota')
# N6 precise too many examples message
h=HSML();h.hear('วิธีนี้ชื่อ excess');h.learning['excess']['pairs']=[[x,x]for x in range(257)];r=h.hear('excess ของ 97 คืออะไร');ck('quota text accurate',r['kind']=='example_quota'and'256'in r['text'])
# N2/N7 integrity anchors and missing pack fail-loud, restore files.
for file,change in [('logs/baselib_pin.json',b'{}'),('logs/seed_programs.json',None)]:
 p=P/file;raw=p.read_bytes()
 try:
  if change is None:p.rename(str(p)+'.testbak')
  else:p.write_bytes(change)
  t=time.perf_counter()
  try:HSML()
  except RuntimeError:ck('startup fails fast '+file,time.perf_counter()-t<.2)
  else:ck('startup fails fast '+file,False)
 finally:
  if change is None:Path(str(p)+'.testbak').rename(p)
  else:p.write_bytes(raw)
# N4 fresh recursive acquisition actually enters original search, teacher never supplies query97.
h=HSML();h.hear('วิธีนี้ชื่อ rec')
for x,y in [(1,1),(2,3),(3,6),(4,10),(5,15)]:r=h.hear(f'ถ้า n เป็น {x} ตอบ {y}')
ck('fresh recursive route reachable',r['kind']in {'confirmation_question','search_budget'})
if r['kind']=='confirmation_question':
 for _ in range(3):
  x=h.pending['checks'][h.pending['passed']];r=h.hear(f'ตอบ {x*(x+1)//2}')
 ck('fresh recursive confirmed',r['kind']=='skill_stored'and'rec'in h.mem.skills and'rec'not in h.learning)
 ck('fresh recursive heldout',h.hear('rec ของ 97 คืออะไร')['result']==4753)
report={'checks':checks,'count':len(checks),'fresh_recursive_final':r,'limits':'thread embedded guard does not execute unbounded search; no stronger success claim'};(P/'review_findings_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
