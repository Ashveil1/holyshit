import os,sys,time,json,statistics,tempfile,subprocess,threading
from pathlib import Path
P=Path(__file__).resolve().parent
if len(sys.argv)>1:
 from hsml import HSML
 rows=[]
 def measure(k,fn):
  t=time.perf_counter();v=fn();rows.append({'operation':k,'seconds':time.perf_counter()-t});return v
 h=measure('init',HSML)
 with tempfile.TemporaryDirectory()as d:
  f=d+'/m.pkl'
  for word,pairs in [('พรอม',[(7,14),(2,4),(10,20)]),('ครอม',[(0,3),(1,5),(4,11)]),('กลอม',[(0,0),(2,4),(3,9)])]:
   measure('naming',lambda:h.hear('วิธีนี้ชื่อ '+word))
   for x,y in pairs:measure('teaching',lambda:h.hear(f'ถ้า n เป็น {x} ตอบ {y}'))
   measure('query_cold_search',lambda:h.hear(f'{word} ของ 97 คืออะไร'))
   for _ in range(10):measure('query_warm',lambda:h.hear(f'{word} ของ 123456 คืออะไร'))
   measure('save',lambda:h.save(f));h=measure('reload',lambda:HSML.load(f))
 print(json.dumps(rows));sys.exit()
def rss_tree(root):
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   d={l.split(':',1)[0]:l.split(':',1)[1].strip()for l in(p/'status').read_text().splitlines()if ':'in l};out[int(p.name)]=(int(d['PPid']),int(d.get('VmRSS','0 kB').split()[0])*1024)
  except(OSError,ValueError,KeyError):pass
 ids={root}
 while True:
  n={p for p,v in out.items()if v[0]in ids}
  if n<=ids:break
  ids|=n
 return sum(out[i][1]for i in ids if i in out)
allrows=[];peak=0;samples=0
for _ in range(5):
 p=subprocess.Popen([sys.executable,__file__,'worker'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 start=time.perf_counter()
 while p.poll()is None:
  r=rss_tree(os.getpid());peak=max(peak,r);samples+=1
  if r>900000000 or time.perf_counter()-start>5:p.kill();raise RuntimeError('resource guard')
  time.sleep(.005)
 out,err=p.communicate()
 if p.returncode:raise RuntimeError(err)
 allrows.extend(json.loads(out))
summary={}
for key in sorted(set(r['operation']for r in allrows)):
 v=sorted(r['seconds']for r in allrows if r['operation']==key);summary[key]={'n':len(v),'p50':statistics.median(v),'p95':v[min(len(v)-1,int(.95*len(v)))],'max':max(v)}
r={'summary':summary,'polled_tree_peak_bytes':peak,'poll_samples':samples,'poll_seconds':.005,'resource_scope':'profiler parent + worker descendants, production path no torch','wall_timeout':5,'rows':allrows};(P/'latency_resource.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k!='rows'},indent=2))
