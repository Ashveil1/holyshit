import tempfile,json
from pathlib import Path
import hsml
h=hsml.HSML();h.hear('วิธีนี้ชื่อ resumable')
for x,y in [(0,0),(1,1),(2,4),(3,9)]:h.hear(f'ถ้า n เป็น {x} ตอบ {y}')
original=hsml.induce
try:
 hsml.induce=lambda *a,**k:(None,123)
 r=h.hear('ถ้า n เป็น 4 ตอบ 16');assert r['kind']=='teach_failed'and r['text']and len(h.ctx['pairs'])==5
 with tempfile.TemporaryDirectory()as d:
  h.save(d+'/m');h=hsml.HSML.load(d+'/m');r=h.hear('ถ้า n เป็น 5 ตอบ 25');assert r['kind']=='teach_failed'and len(h.ctx['pairs'])==6 and len(h.learning['resumable']['pairs'])==6
finally:hsml.induce=original
Path(__file__).with_name('failed_resume_result.json').write_text(json.dumps({'reply':r,'accepted_pairs':6,'restart_resumes_without_rename':True},ensure_ascii=False,indent=2))
print('failed-search resume pass')
