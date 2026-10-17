#!/usr/bin/env python3
"""Bounded cold flat Dicts: interpreter-owned records with creation/slot budgets."""
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
      'd = {"a": 1, "b": 2}\nprint len(d)\nprint d["a"]\nd["c"] = 3\nprint len(d)\nd["a"] = 10\nprint d["a"]\nprint d["c"]\n',
      'e = {1: "one", 2: "two", 10: 5}\nprint e[1]\nprint e[10]\ne[3] = "three"\nprint e[3]\nprint len(e)\n',
      'd = {"a": 1, "b": 2}\nprint has(d, "b")\nprint has(d, "z")\nprint "b" in d\nprint "z" not in d\nprint 1 in {1: "x"}\n',
      'd = {"x": 7, "y": 8}\nks = keys(d)\nprint len(ks)\nprint ks[0]\nprint ks[1]\nvs = values(d)\nprint vs[0]\nprint vs[1]\n',
      'd = {"a": 1, "b": 2, "c": 3}\ntotal = 0\nfor k in d:\n  total = total + d[k]\nprint total\nfor k in d:\n  print k, d[k]\ne = {1: "one", 2: "two"}\nfor k in e:\n  print k, e[k]\n',
      'empty = {}\nprint len(empty)\nif empty:\n  print "never"\nif not empty:\n  print "empty"\nd = {"a": 1}\nif d:\n  print "nonempty"\ndef get(d, k):\n  return d[k]\nprint get(d, "a")\ndef put(d, k, v):\n  d[k] = v\nput(d, "b", 5)\nprint d["b"]\nd2 = d\nd2["w"] = 99\nprint d["w"]\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('d = {"a": 1}\nprint d["z"]\n','key not found',b''),
      ('d = {"a": 1}\nd[true] = 2\n','dict key must be Str or Int',b''),
      ('d = {}\nd[[1]] = 2\n','dict key must be Str or Int',b''),
      ('d = {"a": 1}\nprint d[true]\n','dict key must be Str or Int',b''),
      ('print true in {"a": 1}\n','dict key must be Str or Int',b''),
      ('print has([1], "a")\n','wants flat scalar Dict',b''),
      ('print keys([1])\n','wants flat scalar Dict',b''),
      ('print values("ab")\n','wants flat scalar Dict',b''),
      ('print {"a": 1} + {"b": 2}\n','unsupported value',b''),
      ('print str({"a": 1})\n','str conversion wants scalar',b''),
      ('print {"a": 1}\n','unsupported value',b''),
      ('d = {"a": [1]}\n','unsupported value',b''),
      ('d = {"a": 1}\nprint d["a"][0:1]\n','cannot slice scalar',b''),
      ('d = {}\ni = 0\nwhile i < 4097:\n  d[str(i)] = i\n  i = i + 1\nprint "done"\n','dict exceeds4096 pairs',b''),
      ('i = 0\nwhile i < 1025:\n  d = {"a": i}\n  i = i + 1\nprint "done"\n','dict allocation budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=60)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
    body='d = {"a": 1}\nd["a"] = 2\nd["a"] = 3\nprint d["a"]\nprint len(d)\n'
    source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
    assert not r.returncode and r.stdout==b'3\n1\n' and not r.stderr,(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold flat Dict gates (no shared native values or hot tier)')
