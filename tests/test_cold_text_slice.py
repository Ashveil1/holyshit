#!/usr/bin/env python3
"""Bounded cold ASCII text slices: clamped bounds and cumulative byte accounting."""
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
      's = "hello world"\nprint s[0:5]\nprint s[6:]\nprint s[:5]\nprint s[:]\nprint s[-5:]\nprint s[:-6]\nprint len(s[:])\n',
      's = "hello world"\nprint s[3:3]\nprint s[9:2]\nprint s[2:100]\nprint s[-100:2]\nprint s[0:0]\nprint "x" + s[4:4] + "y"\n',
      's = "abcdef"\ni = 1\nj = 4\nprint s[i:j]\nprint s[i + 1:j + 1]\nprint s[len(s) - 2:len(s)]\n',
      'def mid(s, a, b):\n  return s[a:b]\nprint mid("hello world", 0, 5)\nprint mid("hello world", 6, 11)\nprint mid("abc", 1, 1)\n',
      's = "hello world"\nt = s[0:5]\nu = t[1:3]\nprint t\nprint u\nprint s\nprint t + s[5:]\n',
      's = ""\nprint s[:]\nprint s[0:0]\ni = 0\nwhile i < 3:\n  s = s + "ab"[0:1]\n  i = i + 1\nprint s\nif s[0:2] == "aa":\n  print "match"\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('xs = [1, 2, 3]\nprint xs[0:1]\n','List slices unsupported',b''),
      ('print 1[0:1]\n','cannot slice scalar',b''),
      ('print true[0:1]\n','cannot slice scalar',b''),
      ('print "abc"[true:]\n','signed30-bit',b''),
      ('print "abc"[:1.5]\n','unsupported value',b''),
      ('s = '+json.dumps('x'*1024)+'\ni = 0\nwhile i < 64:\n  t = s[0:1024]\n  i = i + 1\nprint "done"\n','text byte budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
    body='s = '+json.dumps('x'*1024)+'\ni = 0\nwhile i < 64:\n  t = s[0:0]\n  i = i + 1\nprint s[0:1024]\n'
    source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
    assert not r.returncode and r.stdout==b'x'*1024+b'\n' and not r.stderr,(r.stdout[-80:],r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold text slice gates (no List slices or shared native values)')
