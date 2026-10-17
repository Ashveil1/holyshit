#!/usr/bin/env python3
"""Cold text in flat Lists: aliases, immutable elements and lazy ternary lowering."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT));passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    def build(source,output):
        command=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(source),'-o',str(output)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(output)])
        r=subprocess.run(command,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-400:]
    build(ROOT/'selfhost/be/cold_scalar_run.holy',driver);passed+=1
    cases=[
      'a = ["old",1,true,null]\nb = a\nx = a[0]\nb[0] = "new"\nappend(a,"tail")\nprint x\nprint a[0]\nprint b[-1]\nprint len(b)\n',
      'def change(a):\n  a[0] = a[0] + "!"\n  return a\na = ["hello"]\nb = change(a)\nprint a[0]\nprint b[0]\n',
      'def side():\n  print "bad"\n  return "wrong"\nprint "yes" if true else side()\nprint side() if false else "no"\n',
      'def f(a=["start"]):\n  append(a,"end")\n  return a[-1]\nprint f()\nprint f()\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body in ['a = [["x"]]\n','a = []\nappend(a,a)\n','def f():\n  return 1\na = [f]\n','a = ["x"]\nb = a if true else a\n']:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and b'unsupported value'in r.stderr,(r.stdout,r.stderr);passed+=1
    harness=d/'alias.holy';harness.write_text('''import normalize
import irbuild
import coldscalar
m = irbuild.build_module(normalize.parse("a = [\\\"old\\\"]\\na[0] = []\\n"), "")
s = coldscalar.create(m,100)
try:
  coldscalar.run(s)
except:
  print s[2]["a"]["items"][0]
print s[5],s[8],s[9],s[10]
# Reference the same immutable text twice. List slots charge, text does not copy.
m = irbuild.build_module(normalize.parse("t = \\\"hello\\\"\\na = [t,t]\\nappend(a,t)\\na[0] = t\\n"), "")
s = coldscalar.create(m,100)
coldscalar.run(s)
print s[8],s[9],s[10]
''')
    exe=d/'alias';build(harness,exe);r=subprocess.run([str(exe)],env=env,capture_output=True,timeout=30)
    assert not r.returncode and r.stdout==b'old\n0 2 1 3\n1 3 5\n',(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} cold text/flat-List alias and ternary gates (not shared native objects)')
