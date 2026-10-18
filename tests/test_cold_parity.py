#!/usr/bin/env python3
"""Cold/reference parity audit: identical behavior across the supported subset,
clean refusals for the documented exclusions, never silent divergence."""
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
    parity=[
      'x = 7\ny = x * 6 % 5\nprint y\nz = (x | 3) ^ 2\nprint z\nprint ~y\nprint x >> 1 << 2\n',
      's = "hello world"\nprint len(s)\nprint s[0]\nprint s[6:]\nprint s + "!"\nprint find(s, "o")\nprint s < "zebra"\n',
      'parts = split("a,b,c", ",")\nprint len(parts)\nprint join("-", parts)\nprint join("=", ["x"])\n',
      'xs = [1, 2, 3]\nappend(xs, 4)\nxs[0] = 9\nprint len(xs)\nprint xs[0] + xs[3]\nprint xs[-1]\nys = xs[1:3]\nprint ys == [2, 3]\n',
      'd = {"a": 1, 2: "two"}\nd["b"] = true\nprint len(d)\nprint d[2]\nprint has(d, "a")\nprint d == {"a": 1, 2: "two", "b": true}\nfor k in d:\n  print k\n',
      'def fib(n):\n  if n < 2:\n    return n\n  return fib(n - 1) + fib(n - 2)\nprint fib(10)\n',
      'g = 1\ndef bump():\n  global g\n  g = g + 1\nbump()\nbump()\nprint g\n',
      'xs = [i * i for i in [1, 2, 3]]\nprint len(xs)\nprint xs[2]\nys = [x for x in [1, 2, 3, 4] if x % 2 == 0]\nprint ys == [2, 4]\n',
      'i = 0\nwhile i < 10:\n  i = i + 1\n  if i == 3:\n    continue\n  if i == 6:\n    break\n  print i\n',
      'for x in [10, 20]:\n  for y in [1, 2]:\n    print x + y\n',
      'print 1 < 2 < 3\nprint 3 > 2 > 1\nprint 1 == 1 != false\n',
      'x = 2\ny = x == 2 and "a" or "b"\nprint y\nz = "p" if x > 5 else "q"\nprint z\nxs = [] or [7]\nprint xs[0]\n',
      'print int("42")\nprint int("-3")\nprint str(99)\nprint str(true)\nprint str(null)\nprint int("12") + 1\n',
      'r = range(3)\nprint len(r)\nprint r[0]\nr = range(2, 10)\nprint r[2]\nfor v in range(2):\n  print v\n',
      'print 1, "two", true, null, 3\nprint\nprint "end"\n',
      'assert 1 == 1\nassert "a" in "abc"\nprint "asserts ok"\n',
      'def check(n):\n  assert n > 0, "want positive"\n  return n\nprint check(9)\n',
      'def mid(xs, a, b):\n  return xs[a:b]\nprint mid([1, 2, 3, 4], 1, 3) == [2, 3]\ndef rev3(xs):\n  return [xs[2], xs[1], xs[0]]\nprint rev3([1, 2, 3])[0]\n',
      'd = {"n": 0}\ndef inc(dd):\n  dd["n"] = dd["n"] + 1\ninc(d)\ninc(d)\nprint d["n"]\n',
      'print abs(0 - 5)\nprint min(3, 7)\nprint max(3, 7)\nprint min(-1, 1)\n',
      's = "a\\tb\\\\c"\nprint len(s)\nprint s[1]\nprint "x\\ny"\n',
      'xs = [1, 2]\nprint 1 in xs\nprint 9 not in xs\nprint "ell" in "hello"\nprint "a" in {"a": 1}\n',
      'n = 0\nwhile true:\n  n = n + 1\n  if n >= 4:\n    break\nprint n\n',
      'xs = [1, 2]\nxs.append(3)\nprint len(xs)\n',
      'f = lambda x: x + 1\nprint f(1)\ng = lambda a, b: a * b\nprint g(3, 4)\n',
      'class P:\n  def __init__(self, x):\n    self.x = x\np = P(5)\nprint p.x\np.x = 7\nprint p.x\nq = P(1)\nprint q.x\nprint p.x\n',
    ]
    source=d/'source.holy'
    for body in parity:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode and not got.returncode and got.stdout==ref.stdout and not got.stderr,(body,got.stdout,got.stderr,ref.stdout,ref.stderr);passed+=1
    for body,why in [
      ('print 1.5\n','floats'),
      ('print 4 / 2\n','division'),
      ('def outer():\n  def inner():\n    return 1\n  return inner()\nprint outer()\n','nested functions'),
      ('def f(n):\n  return [i for i in range(n)]\nprint f(2)[1]\n','function-level comprehensions'),
      ('try:\n  print "a"\nexcept:\n  print "b"\n','try/except'),
      ('print [1, 2]\n','container printing'),
      ('print {"a": 1}\n','container printing'),
      ('xs = [1] + [2]\nprint xs[0]\n','container arithmetic'),
      ('xs = [[1]]\nprint xs[0][0]\n','nested containers'),
      ('xs = [1] if true else [2]\nprint xs[0]\n','List-arm ternary'),
      ('d = {"a": 1} if true else {"b": 2}\nprint d["a"]\n','Dict-arm ternary'),
      ('print 1 == "a"\n','mixed-text comparison'),
      ('print float("1.5")\n','float conversion'),
      ('def f():\n  y = 2\n  g = lambda x: x + y\n  return g(1)\nprint f()\n','capturing lambdas'),
      ('class P:\n  def __init__(self, x):\n    self.x = x\n  def get(self):\n    return self.x\np = P(5)\nprint p.get()\n','class methods'),
    ]:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert not ref.returncode,("reference no longer supports the documented exclusion",why,body,ref.stderr[-120:])
        assert got.returncode,("cold silently accepts the documented exclusion",why,body)
        passed+=1
    for body in [
      'print "ab" * 3\n',
      'print 1[0]\n',
      'raise 42\n',
      's = "abc"\nprint s.upper()\n',
      'print [1] < [2]\n',
      'print {"a": 1} < {"b": 2}\n',
    ]:
        source.write_text(body);ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30);got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=30)
        assert ref.returncode and got.returncode,(body,ref.stdout,got.stdout);passed+=1
print(f'{passed}/{passed} cold/reference parity audit gates (subset identical, exclusions refuse cleanly)')
