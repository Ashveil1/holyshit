#!/usr/bin/env python3
"""Bounded cold List/Dict equality: value semantics for ==/!=, ordering stays refused."""
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
      'print [1, 2, 3] == [1, 2, 3]\nprint [1, 2, 3] != [1, 2, 3]\nprint [1, 2] == [2, 1]\nprint [1, 2] == [1, 2, 3]\nprint [1, 2, 3] != [1, 9, 3]\n',
      'print [] == []\nprint [] == [1]\nprint [1] != []\n',
      'print [1, true, null, "ab"] == [1, true, null, "ab"]\nprint [1, true, null, "ab"] == [1, false, null, "ab"]\nprint ["a", "b"] == ["a", "c"]\n',
      'xs = [1, 2]\nys = xs\nprint xs == ys\nys[0] = 9\nprint xs == ys\nprint xs == [9, 2]\n',
      'xs = [1, 2, 3]\nprint xs[0:2] == [1, 2]\nprint xs[:] == xs\nprint xs[0:0] == []\n',
      'd = {"a": 1, "b": 2}\ne = {"b": 2, "a": 1}\nprint d == e\nprint d != e\ne["b"] = 3\nprint d == e\nprint d != e\n',
      'print {"a": 1} == {"a": 1, "b": 2}\nprint {"a": 1} == {"c": 1}\nprint {1: "x", 2: "y"} == {2: "y", 1: "x"}\nprint {} == {}\nprint {} == {"a": 1}\n',
      'print [1] == 1\nprint [1] == {"a": 1}\nprint {"a": 1} == [1]\nprint {"a": 1} != null\nprint null == {}\n',
      'def same(a, b):\n  return a == b\nprint same([1, 2], [1, 2])\nprint same({"k": true}, {"k": true})\nprint same([1], [2])\n',
      'xs = [1, 2]\nif xs == [1, 2]:\n  print "same"\nif xs != [1, 2]:\n  print "bad"\nd = {"a": 1}\nwhile d != {"a": 2}:\n  d["a"] = d["a"] + 1\nprint d["a"]\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('xs = [1]\nprint xs < [2]\n','unsupported value',b''),
      ('xs = [1]\nprint xs + [2]\n','unsupported value',b''),
      ('d = {"a": 1}\nprint d < d\n','unsupported value',b''),
      ('d = {"a": 1}\nprint d + d\n','unsupported value',b''),
      ('xs = [1]\nprint xs == "a"\n','text operands',b''),
      ('xs = [1]\nprint "a" == xs\n','text operands',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold container equality gates (no shared native values or hot tier)')
