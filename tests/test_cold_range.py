#!/usr/bin/env python3
"""Bounded cold range Lists with existing creation/slot budgets."""
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
      'for i in range(4):\n  print i\nprint len(range(0))\nprint len(range(-3))\n',
      'print len(range(2, 6))\nfor i in range(2, 6):\n  print i\nprint len(range(5, 2))\n',
      'xs = range(3)\nprint xs[0]\nprint xs[2]\nxs[1] = 99\nprint xs[1]\nappend(xs, 7)\nprint len(xs)\n',
      'total = 0\nfor i in range(10):\n  total = total + i\nprint total\ni = 0\nfor x in range(3):\n  for y in range(2):\n    i = i + 1\nprint i\n',
      'def count(n):\n  return len(range(n))\nprint count(7)\ndef upto(n):\n  return range(n)\nxs = upto(3)\nprint xs[2]\nprint 2 in range(4)\nprint 5 not in range(4)\n',
      'for i in range(3):\n  if i == 1:\n    continue\n  print i\nfor i in range(10):\n  if i == 2:\n    break\n  print i\nprint str(len(range(2)))\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print range("a")\n','signed30-bit',b''),
      ('print range(true)\n','signed30-bit',b''),
      ('print range(1, 2, 3)\n','range wants range(n) or range(a, b)',b''),
      ('print range()\n','range wants range(n) or range(a, b)',b''),
      ('print range(4097)\n','list exceeds4096 elements',b''),
      ('print range(536870912)\n','signed30-bit',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
    body='print len(range(4096))\nxs = range(16)\nprint len(range(16))\n'
    source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
    assert not r.returncode and r.stdout==b'4096\n16\n' and not r.stderr,(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold range gates (no shared native values or hot tier)')
