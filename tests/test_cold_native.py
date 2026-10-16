#!/usr/bin/env python3
"""Explicit cold->isolated-native->cold scalar calls, never a tiered JIT."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/cold_native_run.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/cold_native_run.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-400:];passed+=1
    native=d/'native.holy';cold=d/'cold.holy'
    cases=[
      ('def f(n):\n  if n < 2:\n    return n\n  return f(n-1) + f(n-2)\n','a = native(10)\nprint a\nprint native(a - 40)\n',1),
      ('count = 0\ndef f(a,b):\n  global count\n  count = count + 1\n  return a + b + count\n','a = [3,4]\nx = native(a[0],a[1])\nappend(a,x)\nprint a[2]\nprint native(x,10)\nprint a[0]\n',2),
      ('def make(x):\n  def inner(n):\n    for i in range(30000):\n      junk = str(i)\n    return x[0] + n\n  return inner\nf = make([19])\n','i = 0\nwhile i < 3:\n  print native(i)\n  i = i + 1\n',1),
      ('def later(n):\n  return n + 100\ndef f(n):\n  global f\n  f = later\n  return n\n','print native(1)\nprint native(3)\ndef other(n):\n  return n * 2\nnative = other\nprint native(5)\n',1),
      ('def f():\n  return 19\n','print native()\nprint native()\n',0),
    ]
    for body,program,arity in cases:
        native.write_text(body);cold.write_text(program)
        r=subprocess.run([str(driver),str(cold),'native',str(native),'f',str(arity)],env=env,capture_output=True,timeout=90)
        ref=d/'reference.holy';params=', '.join('p'+str(i)for i in range(arity))
        ref.write_text(body+'def native('+params+'):\n  return f('+params+')\n'+program)
        expected=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(ref)],env=env,capture_output=True,timeout=60)
        assert not r.returncode and not expected.returncode and not r.stderr and r.stdout==expected.stdout,(r.stdout,r.stderr,expected.stdout,expected.stderr);passed+=1
    native.write_text('def f(n):\n  if n == 0:\n    raise "zero"\n  return n\n')
    for program,reason in [('native(true)\n','signed30-bit'),('native([])\n','signed30-bit'),('native(0)\n','cold native: zero'),('i = 0\nwhile i < 4097:\n  native(1)\n  i = i + 1\n','bridge call budget')]:
        cold.write_text(program);r=subprocess.run([str(driver),str(cold),'native',str(native),'f','1'],env=env,capture_output=True,timeout=90)
        assert r.returncode and reason.encode()in r.stderr,(r.stdout,r.stderr);passed+=1
    for body,program,reason in [
      ('def f(n):\n  return true\n','native(1)\n','non-integer return'),
      ('def f(n):\n  return 536870912\n','native(1)\n','signed30-bit'),
      ('raise "init"\ndef f(n):\n  return n\n','native(1)\n','native initialization failed'),
    ]:
        native.write_text(body);cold.write_text(program)
        r=subprocess.run([str(driver),str(cold),'native',str(native),'f','1'],env=env,capture_output=True,timeout=90)
        assert r.returncode and reason.encode()in r.stderr,(r.stdout,r.stderr);passed+=1
    native.write_text('print 999\ndef f(n):\n  return n\n');cold.write_text('print "unsupported"\n')
    r=subprocess.run([str(driver),str(cold),'native',str(native),'f','1'],env=env,capture_output=True,timeout=90)
    assert r.returncode and not r.stdout,(r.stdout,r.stderr);passed+=1
    native.write_text('count = 0\ndef f(n):\n  global count\n  count = count + 1\n  if n == 0:\n    raise "zero"\n  return count + n\n')
    harness=d/'library.holy';harness.write_text('''import normalize
import irbuild
import coldscalar
import coldnative
import jitboundary
import jitmem
n = jitboundary.prepare_dynamic(argv()[0],"f",1)
print jitboundary.scalar_outcome(n,n[1],false)
for program in ["native(0)\\n", "print native(10)\\n"]:
  c = coldscalar.create(irbuild.build_module(normalize.parse(program),""),100)
  coldnative.bind(c,"native",n)
  try:
    coldscalar.run(c)
  except:
    print "caught", c[5]
  try:
    coldnative.bind(c,"native",n)
  except:
    print "late rejected"
# Rejected transport doesn't invoke the target; then a new cold state continues.
c = coldscalar.create(irbuild.build_module(normalize.parse("native(true)\\n"),""),100)
coldnative.bind(c,"native",n)
try:
  coldscalar.run(c)
except:
  print "transport rejected",c[5]
print jitboundary.dynamic_outcome(n,[10])
jitboundary.release_heap(n,false)
jitmem.release(n[0])
print n[0]["live"]
''')
    exe=d/'library';build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(harness),'-o',str(exe)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(harness),str(exe)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-400:]
    r=subprocess.run([str(exe),str(native)],env=env,capture_output=True,timeout=90)
    assert not r.returncode and r.stdout==b'[0, null]\ncaught 0\nlate rejected\n12\nlate rejected\ntransport rejected 0\n[0, 13]\nfalse\n',(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} explicit cold/native scalar bridge gates (no shared objects or hot tier)')
