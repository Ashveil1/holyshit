#!/usr/bin/env python3
"""Direct valid-arity IR text calls keep source locations and eager arguments.
Aliases/invalid arity remain pinned; Python and native hs direct calls agree.
"""
from pathlib import Path
import sys,os,subprocess,tempfile,io,contextlib,re
R=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(R))
from x64gen import build_x64_ast
from irx64 import build_irx64
E=dict(os.environ,HSPATH=str(R/'selfhost')+':'+str(R/'selfhost/be'),HSROOT=str(R))
cases=[]
args={'split':[('1', '","'),('"a"','1')],'find':[('1','"a"'),('"a"','1')],'join':[('1','["a"]'),('"-"','1')]}
def add(name,body,group):cases.append((name,'# location padding\n'*5+body,group))
for name in args:
 for alias in [False,True]:
  for caught in [False,True]:
   for pos,(a,b) in enumerate(args[name],1):
    pre='f = '+name+'\n' if alias else 'marker = 1\n'
    call=('f' if alias else name)+'('+a+', '+b+')'
    body=pre+('try:\n  print '+call+'\nexcept as e:\n  print e\nprint "after"\n' if caught else 'print '+call+'\nprint "unreachable"\n')
    add(f'{name}_alias{alias}_caught{caught}_pos{pos}',body,'types')
 good={'split':'"a,b", ","','find':'"abc", "b"','join':'"-", ["a", "b"]'}[name]
 add(name+'_success','print '+name+'('+good+')\n','success')
 add(name+'_shadow','def '+name+'(a, b):\n  return 42\nprint '+name+'(1, 2)\n','shadow')
 valid={'split':('"a,b"','","'),'find':('"abc"','"b"'),'join':('"-"','["a", "b"]')}[name]
 for invalid in [False,True]:
  a,b=valid
  if invalid:a='1'
  add(name+'_eval_invalid'+str(invalid),'def a():\n  print "arg1"\n  return '+a+'\ndef b():\n  print "arg2"\n  return '+b+'\ntry:\n  print '+name+'(a(), b())\nexcept as e:\n  print e\nprint "after"\n','eval')
 for alias in [False,True]:
  for caught in [False,True]:
   call=('f' if alias else name)+'()'
   pre='f = '+name+'\n' if alias else 'marker = 1\n'
   add(name+'_arity_alias'+str(alias)+'_caught'+str(caught),pre+('try:\n  print '+call+'\nexcept as e:\n  print e\nprint "after"\n' if caught else 'print '+call+'\n'),'arity')
for name in args:
 add(name+'_function', 'def go():\n  return '+name+'(1, 1)\ntry:\n  print go()\nexcept as e:\n  print e\n', 'function')
add('split_one_success', 'print split("a b")\n', 'success')
passed=0
with tempfile.TemporaryDirectory(prefix='hs-split-parity-') as td:
 d=Path(td)
 for i,(name,src,group) in enumerate(cases):
  p=d/(name+'.holy');p.write_text(src);row={'name':name,'group':group,'source':src,'drivers':{}}
  for backend in ['interp','ast-x64','ir-x64','native-hs']:
   out=d/(name+'-'+backend);sio=io.StringIO();buildrc=0
   if backend=='interp':cmd=[sys.executable,str(R/'interp.py'),str(p)]
   elif backend=='native-hs':
    z=subprocess.run([str(R/'bootstrap/hs-hosted-x86_64'),str(p),str(out)],env=E,capture_output=True,timeout=90);buildrc=z.returncode;sio.write(z.stderr.decode());cmd=[str(out)]
   else:
    with contextlib.redirect_stderr(sio),contextlib.redirect_stdout(sio):buildrc=(build_x64_ast if backend=='ast-x64' else build_irx64)(str(p),str(out))
    cmd=[str(out)]
   if buildrc:got={'phase':'build','rc':buildrc,'stdout':'','stderr':sio.getvalue().replace(str(p),'SOURCE')}
   else:
    z=subprocess.run(cmd,env=E,capture_output=True,timeout=15);got={'phase':'run','rc':z.returncode,'stdout':z.stdout.decode(errors='replace'),'stderr':z.stderr.decode(errors='replace').replace(str(p),'SOURCE')}
   row['drivers'][backend]=got
  ref=row['drivers']['interp']; ast=row['drivers']['ast-x64']; ir=row['drivers']['ir-x64']; native=row['drivers']['native-hs']
  def no_location(result):
   return {k: re.sub(r" at line [0-9]+", "", v) if isinstance(v,str) else v for k,v in result.items()}
  if group in ('success', 'function') or group=='types' and '_aliasFalse_' in name:
   assert ir==ref, (name, 'IR direct parity', ir, ref)
  elif group=='shadow':
   assert ir==ref==native and ref['stdout']=='42\n', (name,row)
   assert ast['rc']==1 and ast['stdout']=='', (name,ast)
  elif group=='types':
   assert ir==native==ast==no_location(ref), (name,'alias unchanged',row)
  elif group=='eval':
   assert ir==ref, (name,'eager evaluation',row)
   assert ir['stdout'].startswith('arg1\narg2\n'), (name,row)
  elif group=='arity':
   # The zero-count suffix and runtime catchability remain existing contracts.
   field='stdout' if '_caughtTrue' in name else 'stderr'
   want=dict(ref);want[field]=want[field].replace(' at line ', ' 0 at line ')
   assert ir==native==want, (name,'arity unchanged',row)
   if '_aliasFalse_' in name:
    assert ast['phase']=='build' and ast['rc']==1, (name,ast)
   else:assert ast==want, (name,ast)
  if group in ('types','function'):
   expected_native = no_location(ref) if group=='types' and '_aliasTrue_' in name else ref
   assert native==expected_native, (name,'native-hs contract',native,expected_native)
  if group=='success':assert ast==ir==native==ref, (name,row)
  if group=='eval':assert native==ref, (name,row)
  if group=='types' and '_aliasFalse_' in name:assert ast==ref, (name,ast,ref)
  if group=='eval' and name=='split_eval_invalidTrue':
   want=dict(ref);want['stdout']=want['stdout'].replace('arg2\n','');assert ast==want, (name,ast,want)
  elif group=='eval':assert ast==ref, (name,ast,ref)
  passed+=1
print(f'{passed}/{len(cases)} text builtin error-location and preserved-contract cases (4 drivers; Python/native direct parity)')
