#!/usr/bin/env python3
"""Raw-ABI direct-call gate: module-level Int-shaped functions gain a second
raw-ABI body (untagged params/results, direct call, no fn-object protocol).
Provable direct call sites must behave byte-identically to the tagged
semantics - outputs, error messages, and exit codes - including the cases
that disqualify a function or a call site (bare return, param rebinding,
non-Int arguments, global rebinding). Each program is compiled with the
hosted seed compiler (which contains the GenIR backend under test) and run
natively."""
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
 ('recursion', '''def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)
print fib(20)
print fib(0)
print fib(1)
''', '6765\n0\n1\n', 0, None),
 ('mutual', '''def even(n):
  if n == 0:
    return 1
  return odd(n - 1)
def odd(n):
  if n == 0:
    return 0
  return even(n - 1)
print even(10)
print odd(7)
''', '1\n1\n', 0, None),
 ('paramreassign', '''def g(n):
  n = n + 1
  return n * 10
print g(5)
''', '60\n', 0, None),
 ('nonintarg', '''def g(n):
  n = n + 1
  return n * 10
print g(5)
print g("7")
''', '60\n', 1, 'error: cannot add Str and Int at line 2\n'),
 ('barereturn', '''def f(n):
  if n < 0:
    return
  return n * 2
print f(5)
print f(0 - 1)
''', '10\nnull\n', 0, None),
 ('printparam', '''def h(n):
  print n
  return n + 1
print h(3)
print h("x")
''', '3\n4\nx\n', 1, 'error: cannot add Str and Int at line 3\n'),
 ('rebind', '''def k(n):
  return n + 1
k = 5
print k
''', '5\n', 0, None),
 ('deeprec', '''def sumto(n, acc):
  if n == 0:
    return acc
  return sumto(n - 1, acc + n)
print sumto(1000, 0)
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
''', '500500\n111\n', 0, None),
 ('overflowinraw', '''def sq(n):
  return n * n
print sq(2147483648)
''', '', 97, 'error: Int outside the 62-bit range of the x64 backend (HS_BACKEND=native or interp has 64-bit Int)\n'),
 ('mixedret', '''def pick(n):
  if n > 0:
    return n
  return "neg"
print pick(5)
print pick(0 - 2)
''', '5\nneg\n', 0, None),
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
