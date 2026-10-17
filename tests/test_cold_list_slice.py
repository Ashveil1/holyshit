#!/usr/bin/env python3
"""Bounded cold flat List slices: clamped bounds, copy semantics and slot/creation accounting."""
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
      'xs = [1, 2, 3, 4]\nys = xs[0:2]\nprint len(ys)\nprint ys[0]\nprint ys[1]\nprint xs[1:][0]\nprint xs[:2][1]\nprint xs[-2:][0]\nprint xs[:-1][2]\nprint len(xs[:])\n',
      'xs = [1, 2, 3, 4]\nprint len(xs[3:3])\nprint len(xs[9:2])\nprint len(xs[2:100])\nprint len(xs[-100:2])\nprint len(xs[0:0])\n',
      'xs = [10, 20, 30, 40, 50]\ni = 1\nj = 4\nprint xs[i:j][0]\nprint xs[i:j][2]\nprint xs[i + 1:j + 1][0]\nprint xs[len(xs) - 2:len(xs)][1]\n',
      'def mid(xs, a, b):\n  return xs[a:b]\nys = mid([1, 2, 3, 4], 1, 3)\nprint len(ys)\nprint ys[0]\nprint ys[1]\nprint len(mid([1, 2, 3], 1, 1))\n',
      'xs = [1, 2, 3, 4]\nt = xs[0:3]\nu = t[1:3]\nprint len(u)\nprint u[0]\nprint u[1]\nprint len(t)\nprint t[0]\nprint xs[0]\nprint xs[3]\n',
      'xs = [1, 2, 3]\nys = xs[0:2]\nys[0] = 99\nprint xs[0]\nprint ys[0]\nprint ys[1]\n',
      'xs = [1, true, null, "ab"]\nys = xs[1:3]\nprint ys[0]\nprint ys[1] == null\nzs = xs[3:]\nprint zs[0]\nprint len(zs)\n',
      'xs = [1, 2, 3, 4]\nif xs[0:0]:\n  print "bad"\nelse:\n  print "empty"\nif xs[0:2]:\n  print "nonempty"\nfor x in xs[1:3]:\n  print x\n',
      'xs = [1, 2]\ni = 0\nacc = []\nwhile i < 3:\n  ys = xs[:]\n  append(acc, ys[0] + ys[1])\n  i = i + 1\nprint acc[0]\nprint acc[1]\nprint acc[2]\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    big='[' + ','.join(['1']*1024) + ']'
    for body,reason,before in [
      ('d = {"a": 1}\nys = d[0:1]\n','cannot slice scalar',b''),
      ('xs = [1, 2]\nys = xs[true:]\n','signed30-bit',b''),
      ('xs = [1, 2]\nys = xs[:1.5]\n','unsupported value',b''),
      ('xs = [1, 2]\ni = 0\nwhile i < 1025:\n  ys = xs[:]\n  i = i + 1\n','allocation budget',b''),
      ('xs = '+big+'\ni = 0\nwhile i < 65:\n  ys = xs[:]\n  i = i + 1\nprint "done"\n','allocation budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
    body='xs = [1, 2]\ni = 0\nwhile i < 1023:\n  ys = xs[0:0]\n  i = i + 1\nprint "ok"\n'
    source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
    assert not r.returncode and r.stdout==b'ok\n' and not r.stderr,(r.stdout[-80:],r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold flat List slice gates (no shared native values or hot tier)')
