#!/usr/bin/env python3
"""Bounded cold Int30 modulo, bitwise and shift operators with reference semantics."""
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
      'print 7 % 3\nprint -7 % 3\nprint 7 % -3\nprint -7 % -3\nprint 0 % 5\nprint 1000000 % 7\nprint 5 % 5\n',
      'print 6 & 3\nprint -1 & 255\nprint 0 & 999\nprint 12 | 10\nprint -1 | 0\nprint 0 | 0\n',
      'print 5 ^ 3\nprint -1 ^ 0\nprint 7 ^ 7\nprint 123 ^ 456 ^ 456\n',
      'print 1 << 4\nprint 3 << 0\nprint -1 << 1\nprint 16 >> 2\nprint -16 >> 2\nprint 7 >> 1\nprint 1 >> 0\n',
      'print ~0\nprint ~5\nprint ~-1\nprint ~536870911\nx = 0 - 536870911 - 1\nprint ~x\nprint ~~42\n',
      'a = 6\nb = 3\nprint a & b | 8\nprint a ^ b << 1\nx = (a + b) % 4\nprint x\nprint a >> 1 & b\n',
      'def mask(x, m):\n  return x & m\nprint mask(255, 15)\nprint mask(~0, 7)\ni = 0\nacc = 0\nwhile i < 5:\n  acc = acc | 1 << i\n  i = i + 1\nprint acc\nprint acc % 8\n',
      'xs = [6, 3, 12, 10]\nprint xs[0] & xs[1]\nprint xs[2] | xs[3]\nd = {"m": 255}\nprint d["m"] & 15\nprint d["m"] >> 4\n',
    ]
    source=d/'source.holy'
    for body in cases:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('print 7 % 0\n','division by zero',b''),
      ('print 1 << 64\n','shift count',b''),
      ('print 1 >> -1\n','shift count',b''),
      ('x = (1 << 28) << 2\nprint x\n','signed30-bit',b''),
      ('print "a" % 2\n','text operands',b''),
      ('print true % 2\n','signed30-bit',b''),
      ('print ~true\n','signed30-bit',b''),
      ('print ~"a"\n','signed30-bit',b''),
      ('print [1] & [2]\n','unsupported value',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold Int30 modulo/bitwise/shift gates (no floats/division or shared native values)')
