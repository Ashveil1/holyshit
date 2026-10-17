#!/usr/bin/env python3
"""Bounded cold iteration over text and flat Lists via iterseq pass-through."""
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
      's = "hey"\nfor ch in s:\n  print ch\nt = ""\nfor ch in "abc":\n  t = t + ch + "."\nprint t\n',
      'for x in [10, 20, 30]:\n  print x\ntotal = 0\nfor x in [1, 2, 3]:\n  total = total + x\nprint total\n',
      'for ch in "":\n  print "never"\nfor x in []:\n  print "never"\nprint "done"\n',
      'for ch in "abcd":\n  if ch == "c":\n    break\n  print ch\nfor x in [1, 2, 3, 4]:\n  if x == 2:\n    continue\n  print x\n',
      'for ch in "hi"[0:1]:\n  print ch\nfor ch in "a" + "b":\n  print ch\nxs = ["a", "b"]\nfor x in xs:\n  print x + "!"\n',
      'def shout(s):\n  out = ""\n  for ch in s:\n    out = out + ch + "!"\n  return out\nprint shout("hey")\ndef total(xs):\n  t = 0\n  for x in xs:\n    t = t + x\n  return t\nprint total([4, 5, 6])\n',
      'for x in "ab"[0:0] + "":\n  print x\nprint "ok"\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('for x in 5:\n  print x\n','not iterable',b''),
      ('for x in true:\n  print x\n','not iterable',b''),
      ('s = '+json.dumps('x'*1024)+'\ni = 0\nwhile i < 62:\n  u = s[0:1024]\n  i = i + 1\nfor ch in s:\n  t = ch\nfor ch in s:\n  t = ch\nprint "done"\n','text byte budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold iteration gates (no shared native values or hot tier)')
