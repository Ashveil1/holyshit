#!/usr/bin/env python3
"""Raw-Int unboxing gate: programs whose hot arithmetic lowers to raw (untagged)
Int code in the IR x64 backend must behave byte-identically to the tagged
semantics - outputs, error messages, and exit codes. Each program is compiled
with the hosted seed compiler (which contains the GenIR backend under test)
and run natively."""
from pathlib import Path
import subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
SEED=ROOT/'bootstrap'/'hs-hosted-x86_64'
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL',label,flush=True)
# (name, source, expected stdout, expected rc, expected stderr or None)
CASES=[
 ('arith', '''a = 7
b = 0 - 3
m1 = a % b
print m1
c = 0 - 7
m2 = c % 3
print m2
m4 = c % b
print m4
s1 = 1 << 40
print s1
d = 0 - 5
s2 = d >> 1
print s2
m5 = 10 % 3
print m5
i = 5
s = 1
while i > 0:
  s = s * i
  i = i - 1
print s
n = 1073741824
print n
n2 = n * n
print n2
''', '-2\n2\n-1\n1099511627776\n-3\n1\n120\n1073741824\n1152921504606846976\n', 0, None),
 ('funcs', '''def sumsq(n):
  s = 0
  i = 1
  while i <= n:
    s = s + i * i
    i = i + 1
  return s
print sumsq(100)
def collatz(n):
  c = 0
  while n != 1:
    if n % 2 == 0:
      n = n / 2
    else:
      n = 3 * n + 1
    c = c + 1
  return c
print collatz(27)
def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)
print fib(20)
''', '338350\n111\n6765\n', 0, None),
 ('closures', '''def make_adder(x):
  def add(y):
    return x + y
  return add
a = make_adder(10)
print a(5)
xs = [1, 2, 3, 4]
t = 0
for v in xs:
  t = t + v * v
print t
d = {"a": 1, "b": 2}
for k in keys(d):
  t = t + d[k]
print t
s = "hi"
print len(s) + t
''', '15\n30\n33\n35\n', 0, None),
 ('exceptions', '''def risky(n):
  if n < 0:
    raise "negative"
  return 10 % n
try:
  print risky(3)
  print risky(0)
except as e:
  print "caught: " + e
i = 2
j = 0
try:
  z = i % j
except as e:
  print "mod zero caught"
print "after"
''', '1\ncaught: division by zero at line 4\nmod zero caught\nafter\n', 0, None),
 ('unsafe', '''unsafe:
  p = alloc(64)
  store8(p, 41)
  store8(p + 1, 1)
  v1 = load8(p)
  v2 = load8(p + 1)
  q = v1 + v2
print q
x = 100
unsafe:
  r = as_int(as_ptr(x))
print r
y = 7
z = y & 3
print z
w = y | 8
print w
u = y ^ 5
print u
n = 0 - 8
print n >> 1
print n << 2
''', '42\n100\n3\n15\n2\n-4\n-32\n', 0, None),
 ('divzero', 'x = 10\ny = 0\nz = x % y\nprint z\n', '', 1, 'error: division by zero at line 3\n'),
 ('shiftrange', 'x = 1\ny = 64\nz = x << y\nprint z\n', '', 1, 'error: shift count 64 out of range (0..63) at line 3\n'),
 ('mixedtype', 'x = 5\ny = "a"\nz = x + y\nprint z\n', '', 1, 'error: cannot add Int and Str at line 3\n'),
 ('overflow', 'a = 2147483648\nb = a * a\nprint b\n', '', 97, 'error: Int outside the 62-bit range of the x64 backend (HS_BACKEND=native or interp has 64-bit Int)\n'),
]
with tempfile.TemporaryDirectory() as d:
    d=Path(d)
    for name,source,want_out,want_rc,want_err in CASES:
        src=d/f'{name}.holy';exe=d/f'{name}.exe'
        src.write_text(source)
        r=subprocess.run([str(SEED),str(src),str(exe)],capture_output=True,text=True,timeout=120)
        check(r.returncode==0,f'{name} compile: '+r.stderr[-150:])
        if r.returncode:continue
        r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        check(r.returncode==want_rc,f'{name} rc {r.returncode} != {want_rc}: '+r.stderr[-150:])
        check(r.stdout==want_out,f'{name} stdout: '+repr(r.stdout))
        if want_err is not None:check(r.stderr==want_err,f'{name} stderr: '+repr(r.stderr))
print(f'{passed}/{passed+failed} passed')
sys.exit(1 if failed else 0)
