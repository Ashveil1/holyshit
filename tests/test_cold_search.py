#!/usr/bin/env python3
"""Bounded cold text find and contains over text and flat Lists: scalar results."""
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
      's = "hello world"\nprint find(s, "world")\nprint find(s, "z")\nprint s.find("o")\nprint find("", "")\nprint find(s, "")\n',
      's = "hello world"\nprint "ell" in s\nprint "z" in s\nprint "z" not in s\nprint contains(s, "hello")\nprint "" in s\n',
      'print 2 in [1, 2, 3]\nprint 5 in [1, 2, 3]\nprint "a" in [1, "a"]\nprint 1 in ["a", "b"]\nprint null in [1, null]\nprint true in [true]\n',
      'xs = [7, 8]\nneedle = 8\nprint needle in xs\nprint 9 not in xs\nprint true in [1]\nprint 1 in [true]\nprint 0 in [false]\n',
      'def locate(s, sub):\n  return find(s, sub)\nprint locate("banana", "nan")\ndef member(xs, x):\n  return x in xs\nprint member(["a", "b"], "b")\nprint member(["a", "b"], "c")\n',
      's = "a.b.c"\ni = find(s, ".")\nprint s[0:i]\nprint s[i + 1:]\nif "b" in s:\n  print "has b"\nfor ch in "ab":\n  if ch in "bcd":\n    print ch\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print find("a", 1)\n','find wants find(s, sub)',b''),
      ('print find([1], "a")\n','find wants find(s, sub)',b''),
      ('print find("a")\n','find wants find(s, sub)',b''),
      ('print 1 in "abc"\n','in Str wants a Str',b''),
      ('print 1 in 5\n','not a search container',b''),
      ('print 1 in true\n','not a search container',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold search gates (no shared native values or hot tier)')
