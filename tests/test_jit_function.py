#!/usr/bin/env python3
"""Repeated exact-key scalar calls keep one target alive, errors return to host."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/jit_function_probe.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_function_probe.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-250:];passed+=1
    cases=[
      ('def f(n):\n  if n < 2:\n    return n\n  return f(n - 1) + f(n - 2)\n','f$L1',[[10],[15],[-3]],[[0,55],[0,610],[0,-3]]),
      ('counter = 0\ndef f(n):\n  global counter\n  counter = counter + n\n  return counter\n','f$L2',[[3],[4],[-1]],[[0,3],[0,7],[0,6]]),
      ('def f(n):\n  try:\n    if n == 0:\n      raise "zero"\n    return n + 1\n  finally:\n    print "finally", n\n','f$L1',[[0],[8],[0],[2]],[[1,['zero',4]],[0,9],[1,['zero',4]],[0,3]]),
      ('def f(a,b,c,d,e,g):\n  return a + b * 2 + c * 3 + d * 4 + e * 5 + g * 6\n','f$L1',[[1,2,3,4,5,6],[-1,-2,-3,-4,-5,-6]],[[0,91],[0,-91]]),
      ('def f():\n  return 17\n','f$L1',[[],[]],[[0,17],[0,17]]),
      ('def f(n):\n  items = []\n  for i in range(30000):\n    append(items, str(i))\n  return len(items) + n\n','f$L1',[[1],[2],[3]],[[0,30001],[0,30002],[0,30003]]),
      ('keep = ["rooted"]\ndef f(n):\n  items = []\n  for i in range(30000):\n    append(items, str(i))\n  append(keep, str(n))\n  return len(keep)\n','f$L2',[[1],[2],[3]],[[0,2],[0,3],[0,4]]),
    ]
    for index,(body,key,sets,want)in enumerate(cases):
        source=d/'source.holy';source.write_text(body)
        r=subprocess.run([str(driver),str(source),key,json.dumps(sets)],env=env,capture_output=True,text=True,timeout=90)
        assert not r.returncode and not r.stderr,(index,r.returncode,r.stdout[-200:],r.stderr)
        before,marker,tail=r.stdout.partition('JIT FUNCTION INITIAL ');assert marker
        init,line,release=tail.strip().split('\n');assert json.loads(init)==[0,None]
        assert json.loads(line[len('JIT FUNCTION RESULTS '):])==want,(index,line,want)
        assert release.startswith('JIT FUNCTION RELEASED ')and release.endswith(' false')
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
    body='def f(n):\n  return n\n';source=d/'bad.holy';source.write_text(body)
    for key,sets in [('missing',[[1]]),('<main>',[[1]]),('f$L1',[[]]),('f$L1',[[True]]),('f$L1',[[536870912]]),('f$L1',[]),('f$L1',[[1]]*33)]:
        r=subprocess.run([str(driver),str(source),key,json.dumps(sets)],env=env,capture_output=True,text=True,timeout=60)
        assert r.returncode and 'JIT FUNCTION RESULTS'not in r.stdout,(key,sets,r.stdout,r.stderr);passed+=1
    source.write_text('def f():\n  return "no heap export"\n')
    r=subprocess.run([str(driver),str(source),'f$L1','[[]]'],env=env,capture_output=True,text=True,timeout=60)
    assert r.returncode and 'non-integer return'in r.stderr,r.stderr;passed+=1
mode='Python-built native driver'if '--python-bootstrap'in sys.argv else 'seed-built native driver'
print(f'{passed}/{passed} exact-key repeated scalar native-call gates ({mode}; not a shared-tier ABI)')
