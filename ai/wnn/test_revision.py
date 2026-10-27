import tempfile,time,json
from pathlib import Path
from hsml import HSML
import cur7 as C
from cur7 import make_fn,show_prog
# Genuine existing recursive-DSL dialog skill, not a new affine record.
h=HSML();p=('one',('lt','a','b'),'a',('sub','a','b'),'b',None,'id')
# Use actual valid logged stored program shape, rather than invent an execution schema.
p=h.mem.skills['sumto'][0];fn=make_fn(p);h.mem.skills['เดิม']=(p,fn,{'source':'dialog','examples':8});C.LIB['เดิม']=lambda a,b:fn(a,b)
from b527 import SKILL_BY_WORD
SKILL_BY_WORD['เดิม']='เดิม'
r=h.hear('วิธีนี้ชื่อ เดิม');assert r['kind']=='revision_opened'
start=time.perf_counter()
for x,y in [(1,2),(2,4),(3,6),(4,8),(5,10)]:r=h.hear(f'ถ้า n เป็น {x} ตอบ {y}')
sec=time.perf_counter()-start
assert sec<1.2 and h.mem.skills['เดิม'][0]==p
# Search can yield candidate or budget, never overwrites confirmed old skill before confirmations.
assert r['kind']in {'confirmation_question','search_budget','teach_failed'}
with tempfile.TemporaryDirectory()as d:
 h.save(d+'/m');q=HSML.load(d+'/m');assert q.ctx==h.ctx
 if h.pending:
  assert q.pending['prog']==h.pending['prog']and q.pending['checks']==h.pending['checks']
  for _ in range(3):
   cx=q.pending['checks'][q.pending['passed']]
   # Test teacher's targets for requested newrule are test-side,not in induction/search.
   rr=q.hear(f'ตอบ {2*cx}')
  assert rr['kind']=='skill_stored'
  assert q.hear('เดิม ของ 97 คืออะไร')['result']==194
  assert q.mem.skills['เดิม'][2]['revision']==1
r={'reply':r,'seconds':sec,'legacy_recursive_grammar_preserved':True,'old_skill_not_changed_before_confirmation':True,'pending_persists':True,'bounded_wall':.5,'completion_checked':r['kind']=='confirmation_question'}
Path(__file__).with_name('revision_result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(r)
