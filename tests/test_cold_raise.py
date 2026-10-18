#!/usr/bin/env python3
"""Bounded cold raise/assert: abort-only string raises, no exception objects or try/except."""
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
    source=d/'source.holy'
    for body in [
      'assert 1 == 1\nprint "ok"\nassert true\nprint "done"\n',
      'x = 5\nassert x > 1\nassert x == 5, "unreachable"\nprint x\n',
      'def check(n):\n  assert n > 0, "want positive"\n  return n * 2\nprint check(3)\nprint check(1)\n',
      'i = 0\nwhile i < 3:\n  assert i < 3\n  i = i + 1\nprint i\nxs = [1, 2]\nassert len(xs) == 2\nprint xs[1]\n',
    ]:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,reason,before in [
      ('assert 1 == 2\n','assertion failed',b''),
      ('x = 3\nassert x > 5\nprint "never"\n','assertion failed',b''),
      ('assert false, "boom"\n','boom',b''),
      ('assert 1 == 2, "bad: " + str(7)\n','bad: 7',b''),
      ('print "before"\nassert 1 != 1, "halt"\n','halt',b'before\n'),
      ('raise "custom"\n','custom',b''),
      ('print "a"\nraise "stop here"\nprint "b"\n','stop here',b'a\n'),
      ('def f():\n  raise "from f"\nf()\n','from f',b''),
      ('raise 42\n','raise wants Str',b''),
      ('raise [1]\n','raise wants Str',b''),
      ('raise\n','raise without active exception',b''),
      ('try:\n  pass\nexcept:\n  pass\n','unsupported instruction',b''),
      ('try:\n  raise "x"\nexcept:\n  print "caught"\n','unsupported instruction',b''),
    ]:
        source.write_text(body);r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert r.returncode and reason.encode()in r.stderr and r.stdout==before,(body[:100],r.stdout,r.stderr);passed+=1
print(f'{passed}/{passed} bounded cold raise/assert gates (no exception objects, try/except or finally)')
