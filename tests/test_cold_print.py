#!/usr/bin/env python3
"""Bounded cold multi-value print with scalar display forms."""
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
      'print 1, "a", true, null\nprint\nprint "x"\n',
      'print 1 + 2, "sum"\nx = 5\nprint "x is", x\nprint str(9), int("3")\n',
      'a = 1\nb = 2\nprint a, b, a + b\nprint a\nprint "one", "two", "three"\n',
      'def show(label, n):\n  print label, n\nshow("count", 3)\nshow("total", 10 + 2)\nfor i in range(3):\n  print "i", i\n',
      'xs = [7, 8]\nprint "first", xs[0]\nprint "last", xs[1]\ns = "a,b"\nprint "parts", len(split(s, ","))\nprint find("abc", "b"), "idx"\n',
      'print true, false, null\nprint 1 == 1, "eq"\nprint "n", 0 - 5\nprint len("abc"), len([1, 2])\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print [1], 2\n','unsupported value',b''),
      ('print 1, [2]\n','unsupported value',b''),
      ('print [1]\n','unsupported value',b''),
      ('print "ok"\nprint [1]\n','unsupported value',b'ok\n'),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold print gates (no shared native values or hot tier)')
