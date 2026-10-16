#!/usr/bin/env python3
"""Repeated exact-key scalar calls keep one target alive, errors return to host."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/jit_dispatch_probe.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_dispatch_probe.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-250:];passed+=1
    cases=[
      ('def make(base):\n  def inner(n):\n    return base + n\n  return inner\nf = make(19)\n','f',[[1],[3]],[[0,20],[0,22]]),
      ('def next(n):\n  return n + 100\ndef start(n):\n  global f\n  f = next\n  return n\nf = start\n','f',[[1],[3],[4]],[[0,1],[0,103],[0,104]]),
      ('def make(base):\n  def inner(n):\n    items = []\n    for i in range(30000):\n      append(items, str(i))\n    return base[0] + n\n  return inner\nf = make([19])\n','f',[[1],[2],[3]],[[0,20],[0,21],[0,22]]),
      ('def f(n):\n  try:\n    if n == 0:\n      raise "zero"\n    return n + 1\n  finally:\n    print "finally", n\n','f',[[0],[8],[0],[2]],[[1,['zero',4]],[0,9],[1,['zero',4]],[0,3]]),
      ('def f(a,b,c,d,e,g):\n  return a + b * 2 + c * 3 + d * 4 + e * 5 + g * 6\n','f',[[1,2,3,4,5,6]],[[0,91]]),
      ('def f():\n  return 17\n','f',[[],[]],[[0,17],[0,17]]),
    ]
    for index,(body,key,sets,want)in enumerate(cases):
        source=d/'source.holy';source.write_text(body)
        r=subprocess.run([str(driver),str(source),key,json.dumps(sets)],env=env,capture_output=True,text=True,timeout=90)
        assert not r.returncode and not r.stderr,(index,r.returncode,r.stdout[-200:],r.stderr)
        before,marker,tail=r.stdout.partition('JIT DISPATCH INITIAL ');assert marker
        init,line,release=tail.strip().split('\n');assert json.loads(init)==[0,None]
        assert json.loads(line[len('JIT DISPATCH RESULTS '):])==want,(index,line,want)
        assert release.startswith('JIT DISPATCH RELEASED ')and release.endswith(' false')
        # Independent reference invokes the normal name in the same module/state.
        for args in sets:
            body+='try:\n  print "REF VALUE", f('+', '.join(map(str,args))+')\nexcept as e:\n  print "REF ERROR", e\n'
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,text=True,timeout=60)
        assert not ref.returncode and not ref.stderr,(index,ref.stderr)
        target=ref.stdout
        for status,value in want:
            text='REF VALUE '+str(value)+'\n'if not status else 'REF ERROR '+value[0]+' at line '+str(value[1])+'\n'
            assert text in target,(index,text,target);target=target.replace(text,'',1)
        assert before==target,(index,before,target);passed+=1
    # Call-site errors report synthetic wrapper line2, before any invalid jump.
    for body,sets,expected,ln in [
      ('f = 9\n',[[1]],'not callable: Int',2),
      ('def f(a,b):\n  return a + b\n',[[1]],'f wants 2 args, got 1',2),
      ('f = len\n',[[1]],'len of Int',0),
    ]:
        source=d/'call-error.holy';source.write_text(body)
        r=subprocess.run([str(driver),str(source),'f',json.dumps(sets)],env=env,capture_output=True,text=True,timeout=60)
        assert not r.returncode and not r.stderr,(r.stdout,r.stderr)
        line=next(x for x in r.stdout.splitlines()if x.startswith('JIT DISPATCH RESULTS '))
        value=json.loads(line[len('JIT DISPATCH RESULTS '):]);assert value[0][0]==1 and value[0][1][1]==ln and expected in value[0][1][0],value;passed+=1
    source=d/'bad.holy';source.write_text('def f(n):\n  return n\n')
    for name,sets in [('a.b',[[1]]),('1bad',[[1]]),('f',[[]]),('f',[[True]]),('f',[[536870912]]),('f',[]),('f',[[1]]*33)]:
        # Arity mismatch is a captured target error, not preparation rejection.
        if sets==[[]]:continue
        r=subprocess.run([str(driver),str(source),name,json.dumps(sets)],env=env,capture_output=True,text=True,timeout=60)
        assert r.returncode and 'JIT DISPATCH RESULTS'not in r.stdout,(name,sets,r.stdout,r.stderr);passed+=1
mode='Python-built native driver'if '--python-bootstrap'in sys.argv else 'seed-built native driver'
print(f'{passed}/{passed} dynamic global/closure scalar native-call gates ({mode}; not a shared-tier ABI)')
