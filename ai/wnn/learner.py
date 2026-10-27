"""Finite arithmetic-expression induction. Grammar is designed; selected expression is learned.
No skill names or held-out labels enter search. Agreement is conditional on explored grammar,
not proof of the teacher's unrestricted intention. Integer domain, bounded runtime and magnitude.
"""
import time
GRAMMAR={'ops':['add','sub'],'constants':list(range(-3,4)),'max_nodes':7,'max_candidates':12000,'max_seconds':.15,'max_abs':10**12}
def evaluate(e,x):
 if e=='x':return x
 if isinstance(e,int):return e
 if not isinstance(e,(list,tuple))or len(e)!=3 or e[0]not in GRAMMAR['ops']:raise ValueError('forbidden expression')
 a=evaluate(e[1],x);b=evaluate(e[2],x);v=a+b if e[0]=='add'else a-b
 if abs(v)>GRAMMAR['max_abs']:raise ValueError('magnitude bound')
 return v

def coefficients(e):
 if e=='x':return (1,0)
 if isinstance(e,int):return (0,e)
 if not isinstance(e,(list,tuple))or len(e)!=3 or e[0]not in GRAMMAR['ops']:raise ValueError('forbidden expression')
 a,b=coefficients(e[1]),coefficients(e[2]);sign=1 if e[0]=='add'else -1
 return (a[0]+sign*b[0],a[1]+sign*b[1])

def infer(pairs):
 if len(pairs)>256:return {'status':'example_quota','candidates':[],'complete':False,'tried':0}
 if not pairs:return {'status':'needs_examples','candidates':[],'complete':False,'tried':0}
 seen={}
 for x,y in pairs:
  if x in seen and seen[x]!=y:return {'status':'conflicting_examples','candidates':[],'complete':True,'tried':0}
  seen[x]=y
 if any(abs(x)>10**9 or abs(y)>10**12 for x,y in pairs):return {'status':'outside_domain','candidates':[],'complete':False,'tried':0}
 xs=list(seen)+[0,1,-1,3,11,41,103];target=tuple(seen.values());n=len(seen);start=time.perf_counter();layers={1:[]};signatures=set();matches=[];tried=0;stopped=False
 def add(e,size):
  nonlocal tried
  tried+=1
  try:sig=tuple(evaluate(e,x)for x in xs)
  except(ValueError,OverflowError):return
  key=coefficients(e)
  if key in signatures:return
  signatures.add(key);layers.setdefault(size,[]).append((e,sig))
  if sig[:n]==target:matches.append(e)
 for e in ['x']+GRAMMAR['constants']:add(e,1)
 for size in range(3,8,2):
  for left in range(1,size-1,2):
   right=size-1-left
   for a,av in list(layers.get(left,[])):
    for b,bv in list(layers.get(right,[])):
     for op in GRAMMAR['ops']:
      if tried>=GRAMMAR['max_candidates']or time.perf_counter()-start>=GRAMMAR['max_seconds']:stopped=True;break
      add([op,a,b],size)
     if stopped:break
    if stopped:break
   if stopped:break
  if stopped:break
 return {'status':'candidates'if matches else'no_candidate_within_budget','candidates':matches,'complete':not stopped,'tried':tried,'seconds':time.perf_counter()-start,'grammar':GRAMMAR}

def answer(result,x):
 vals={}
 for e in result['candidates']:
  try:v=evaluate(e,x)
  except(ValueError,OverflowError):return {'status':'outside_domain'}
  vals.setdefault(v,e)
 if not vals:return {'status':result['status']}
 if len(vals)==1:return {'status':'conditional_prediction','value':next(iter(vals)),'explored_complete':result['complete']}
 for q in [0,1,-1,3,11,41,103]:
  try:ys=sorted(set(evaluate(e,q)for e in result['candidates']))
  except ValueError:continue
  if len(ys)>1:return {'status':'ambiguous','ask_input':q,'candidate_values':ys[:8]}
 return {'status':'ambiguous'}
