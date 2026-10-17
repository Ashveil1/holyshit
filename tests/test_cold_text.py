#!/usr/bin/env python3
"""Bounded ASCII cold strings: value semantics and cumulative byte accounting."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT));passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    def build(source,output):
        command=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(source),'-o',str(output)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(output)])
        r=subprocess.run(command,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-400:]
    build(ROOT/'selfhost/be/cold_scalar_run.holy',driver);passed+=1
    cases=[
      'x = "hello"\ny = x\nx = x + "!"\nprint y\nprint x\nprint len(x)\nprint x[0]\nprint x[-1]\n',
      'def greet(who):\n  return "hello " + who\nprint greet("Ash")\nprint greet("world")\n',
      'print "a" == "a"\nprint "a" != "b"\nprint "a" < "b"\nprint "a" <= "a"\nprint "b" > "a"\nprint "b" >= "b"\nprint not ""\nprint not "x"\n',
      's = ""\ni = 0\nwhile i < 50:\n  s = s + "a"\n  i = i + 1\nprint len(s)\nif s:\n  print "yes"\nif "":\n  print "no"\nprint "a\\nb\\tc\\r"\n',
      's = "abc"\nsize = len\nprint size(s)\nprint s[false or 1]\nprint "" or "fallback"\nprint "kept" and "next"\n',
      'def f(s):\n  if len(s) == 0:\n    return "end"\n  return s[0] + "!"\nprint f("")\nprint f("abc")\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print 19\nprint "é"\n','printable ASCII',b''),
      ('print 19\nprint '+json.dumps('x'*1025)+'\n','exceeds1024',b''),
      ('print "abc"[3]\n','index out of range',b''),
      ('print "abc"[-4]\n','index out of range',b''),
      ('print "abc"[true]\n','signed30-bit',b''),
      ('print "a" + 1\n','both be Str',b''),
      ('print "a" * "b"\n','unsupported text operator',b''),
      ('a = ["x"]\n','unsupported value',b''),
      ('s = "a"\ns[0] = "b"\n','flat scalar List',b''),
      ('i = 0\nwhile i < 65:\n  s = '+json.dumps('x'*1024)+'\n  i = i + 1\n','text byte budget',b''),
      ('s = '+json.dumps('x'*1024)+'\nprint s + "y"\n','text byte budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
    harness=d/'budget.holy';harness.write_text('''import normalize
import irbuild
import coldscalar
s = coldscalar.create(irbuild.build_module(normalize.parse("print 1\\n"),""),100)
coldscalar.text_charge(s,1024)
i = 0
while i < 63:
  coldscalar.text_charge(s,1024)
  i = i + 1
print s[10]
try:
  coldscalar.text_charge(s,1)
except:
  print s[10]
''')
    exe=d/'budget';build(harness,exe);r=subprocess.run([str(exe)],env=env,capture_output=True,timeout=30);assert not r.returncode and r.stdout==b'65536\n65536\n',(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold ASCII text gates (no shared native values or hot tier)')
