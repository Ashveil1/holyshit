#!/usr/bin/env python3
"""Bounded cold str/int conversions with cumulative byte accounting."""
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
      'print str(19)\nprint str(-3)\nprint str(true)\nprint str(false)\nprint str(null)\nprint str(19) + "!"\n',
      's = "keep"\nt = str(s)\nprint t\ns = s + "!"\nprint t\nprint len(str(s))\n',
      'print int("42")\nprint int("  -17  ")\nprint int("0x1A")\nprint int("0X2f")\nprint int(true)\nprint int(false)\nprint int(99)\n',
      'n = int("40") + 2\nprint n\nprint str(int("7") + 1)\nprint int(str(123))\nprint str(int("-8") * 2)\n',
      'def show(n):\n  return "n=" + str(n)\nprint show(5)\ndef parse(s):\n  return int(s) + 1\nprint parse("41")\ni = 0\nwhile i < 3:\n  print str(i)\n  i = i + 1\n',
      'parts = split("10,20,30", ",")\ntotal = 0\nfor p in parts:\n  total = total + int(p)\nprint str(total)\nprint join(";", [str(1), str(2)])\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print str([1])\n','str conversion wants scalar',b''),
      ('print int([1])\n','int conversion wants scalar',b''),
      ('print int("abc")\n','cannot convert',b''),
      ('print int("1.5")\n','cannot convert',b''),
      ('print int("")\n','cannot convert',b''),
      ('print int(null)\n','cannot convert',b''),
      ('print int("999999999")\n','signed30-bit',b''),
      ('print str()\n','str wants 1 arg',b''),
      ('s = '+json.dumps('x'*1024)+'\ni = 0\nwhile i < 62:\n  u = s[0:1024]\n  i = i + 1\nu = s[0:1024]\nprint str(19)\n','text byte budget',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
    body='s = '+json.dumps('x'*1000)+'\nt = str(s)\ns = s + "y"\nprint len(t)\nprint len(s)\n'
    source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
    assert not r.returncode and r.stdout==b'1000\n1001\n' and not r.stderr,(r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold conversion gates (no shared native values or hot tier)')
