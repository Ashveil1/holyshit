#!/usr/bin/env python3
"""Opt-in hot pure leaves: threshold, guards, effects and native teardown."""
from pathlib import Path
import json
import os
import platform
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
if platform.machine() not in ('x86_64','amd64'):
    print('skip hotleaf: experimental emitter is x86-64 only')
    sys.exit(0)
ENV=dict(os.environ,HSPATH=f'{ROOT}/selfhost:{ROOT}/selfhost/be',HSROOT=str(ROOT))
def run(args):
    return subprocess.run([str(x) for x in args],env=ENV,capture_output=True,timeout=120)
cases=[
('threshold','def f(n):\n  return n * 2 + 1\nprint f(10)\nprint f(20)\nprint f(30)\n',2,1,2,0),
('cold','def f(n):\n  return n + 1\nprint f(1)\n',2,0,0,0),
('zero','def f():\n  return 7\nprint f()\nprint f()\n',1,1,2,0),
('negative','def f(n):\n  return -n\nprint f(-10)\nprint f(22)\n',1,1,2,0),
('width','def f(n):\n  return n * n\nprint f(3)\nprint f(536870911)\nprint f(4)\n',1,1,2,1),
('intermediate','def f(n):\n  return (n * n) - (n * n)\nprint f(536870911)\nprint f(2)\n',1,1,1,1),
('types','def f(n):\n  return n + n\nprint f(2)\nprint f("x")\nprint f([1])\nprint f(3)\n',1,1,2,2),
('rebind','def f(n):\n  return n + 1\ng = f\nprint f(3)\ndef f(n):\n  return n + 2\nprint f(3)\nprint g(3)\n',1,2,3,0),
('closure','def outer(x):\n  def f(n):\n    return x + n\n  return f\nf = outer(3)\nprint f(4)\n',1,0,0,0),
('effects','def f(n):\n  print "effect"\n  return n + 1\nprint f(2)\nprint f(3)\n',1,0,0,0),
('error','def f(n):\n  return n / 0\ntry:\n  print f(1)\nexcept:\n  print "caught"\nprint "done"\n',1,0,0,0),
('finally','def f(n):\n  return n + 1\ntry:\n  print f(2)\n  raise "x"\nexcept:\n  print f(3)\nfinally:\n  print f(4)\n',1,1,3,0),
('six','def f(a,b,c,d,e,f):\n  return a+b+c+d+e+f\nprint f(1,2,3,4,5,6)\n',1,1,1,0),
('uncaught','def f(n):\n  return n + 1\nprint f(2)\nraise "after native"\n',1,1,1,0),
]
cases.extend([
 ('absolute','def f(n):\n  if n < 0:\n    return -n\n  return n\nprint f(-3)\nprint f(0)\nprint f(5)\n',1,1,3,0),
 ('nested','def f(a,b):\n  if a < b:\n    if a == 0:\n      return b + 1\n    return b - a\n  return a * 2\nprint f(0,3)\nprint f(2,4)\nprint f(5,1)\n',1,1,3,0),
 ('truth','def f(n):\n  if n:\n    return n + 1\n  return 7\nprint f(0)\nprint f(-2)\n',1,1,2,0),
 ('branch-overflow','def f(n):\n  if n < 0:\n    return -n\n  return n * n\nprint f(536870911)\nprint f(-536870912)\nprint f(3)\n',1,1,1,2),
 ('bool-return','def f(n):\n  return n < 3\nprint f(2)\nprint f(4)\n',1,1,2,0),
 ('bool-arithmetic','def f(n):\n  return (n < 3) + 1\ntry:\n  print f(2)\nexcept:\n  print "caught"\n',1,0,0,0),
 ('loop-admitted','def f(n):\n  while n > 0:\n    n = n - 1\n  return n\nprint f(3)\n',1,1,1,0),
 ('branch-effects','def f(n):\n  if n < 0:\n    print "effect"\n    return -n\n  return n\nprint f(-3)\nprint f(4)\n',1,0,0,0),
])
cases.extend([
 ('bool-observable','def f(n):\n  return n < 3\na = f(2)\nb = f(4)\nprint a, b\nprint json_str([a,b])\ntry:\n  print a + 1\nexcept as e:\n  print e\nprint f(-1)\n',1,1,3,0),
 ('bool-branches','def f(a,b):\n  if a < 0:\n    return a < b\n  return a == b\nprint f(-2,3)\nprint f(2,2)\nprint f(2,3)\n',1,1,3,0),
 ('mixed-results','def f(n):\n  if n < 0:\n    return n < 3\n  return n\nprint f(-2)\nprint f(2)\n',1,0,0,0),
 ('bool-type-fallback','def f(n):\n  return n < 3\nprint f(2)\ntry:\n  print f(true)\nexcept:\n  print "caught"\nprint f(5)\n',1,1,2,1),
])
cases.extend([
 ('bool-literal-true','def f():\n  return true\nprint f()\nprint json_str(f())\n',1,1,2,0),
 ('bool-literal-false','def f():\n  return false\nprint f()\nprint json_str(f())\n',1,1,2,0),
 ('bool-predicate','def f(n):\n  if n < 0:\n    return true\n  return false\nprint f(-2)\nprint f(0)\nprint f(3)\n',1,1,3,0),
 ('bool-mixed-predicate','def f(n):\n  if n < 0:\n    return false\n  return n < 3\nprint f(-2)\nprint f(0)\nprint f(3)\n',1,1,3,0),
 ('bool-literal-arithmetic','def f(n):\n  return n + true\ntry:\n  print f(2)\nexcept:\n  print "caught"\n',1,0,0,0),
 ('bool-literal-mixed-return','def f(n):\n  if n < 0:\n    return false\n  return 0\nprint f(-1)\nprint f(1)\n',1,0,0,0),
])
cases.extend([
 ('not-int','def f(n):\n  return not n\nprint f(0)\nprint f(1)\nprint f(-2)\nprint f(-536870912)\n',1,1,4,0),
 ('not-comparison','def f(n):\n  return not (n < 3)\nprint f(2)\nprint f(3)\n',1,1,2,0),
 ('not-double','def f(n):\n  return not not n\nprint json_str([f(0), f(-2)])\n',1,1,2,0),
 ('not-constant','def f():\n  return not true\nprint f()\n',1,1,1,0),
 ('not-branch','def f(n):\n  if not n:\n    return 7\n  return n\nprint f(0)\nprint f(2)\n',1,1,2,0),
 ('not-type-fallback','def f(n):\n  return not n\nprint f(0)\nprint f("")\nprint f([])\nprint f(true)\nprint f(2)\n',1,1,2,3),
 ('not-arithmetic-rejected','def f(n):\n  return (not n) + 1\ntry:\n  print f(0)\nexcept:\n  print "caught"\n',1,0,0,0),
])
for op in ('&', '|', '^'):
 source=f'def f(a,b):\n  return a {op} b\n'
 source+=''.join(f'print f({a},{b})\n' for a,b in [(0,0),(-1,7),(-536870912,536870911),(536870911,-536870912)])
 cases.append(('bitwise-'+op,source,1,1,4,0))
cases.extend([
 ('bitwise-not','def f(n):\n  return ~n\nprint f(0)\nprint f(-1)\nprint f(536870911)\nprint f(-536870912)\n',1,1,4,0),
 ('bitwise-bool-rejected','def f(n):\n  return n & true\ntry:\n  print f(2)\nexcept as e:\n  print e\n',1,0,0,0),
 ('bitwise-type-fallback','def f(n):\n  return ~n\nprint f(1)\ntry:\n  print f(true)\nexcept as e:\n  print e\nprint f(536870912)\n',1,1,1,2),
 ('bitwise-guard-replay','def f(n):\n  return (n * n) & 7\nprint f(3)\nprint f(536870911)\nprint f(4)\n',1,1,2,1),
 ('bitwise-predicate','def f(n):\n  return (n & 1) == 0\nprint json_str([f(2), f(3)])\n',1,1,2,0),
])
cases.extend([
 ('shift-left','def f(n,k):\n  return n << k\nprint f(1,0)\nprint f(1,28)\nprint f(-1,29)\n',1,1,3,0),
 ('shift-right','def f(n,k):\n  return n >> k\nprint f(-7,1)\nprint f(-536870912,29)\nprint f(536870911,29)\n',1,1,3,0),
 ('shift-overflow','def f(n,k):\n  return n << k\nprint f(1,29)\nprint f(-2,29)\nprint f(2,2)\n',1,1,1,2),
 ('shift-large-count','def f(n,k):\n  return n >> k\nprint f(-1,30)\nprint f(-1,63)\ntry:\n  print f(1,64)\nexcept as e:\n  print e\nprint f(8,1)\n',1,1,1,3),
 ('shift-negative-count','def f(n,k):\n  return n << k\ntry:\n  print f(1,-1)\nexcept as e:\n  print e\nprint f(1,2)\n',1,1,1,1),
 ('shift-bool-refused','def f(n):\n  return n << true\ntry:\n  print f(1)\nexcept as e:\n  print e\n',1,0,0,0),
 ('shift-bool-fallback','def f(n,k):\n  return n >> k\nprint f(8,1)\ntry:\n  print f(1,true)\nexcept as e:\n  print e\n',1,1,1,1),
 ('shift-intermediate','def f(n):\n  return (n << 29) >> 29\nprint f(2)\nprint f(-2)\nprint f(-1)\n',1,1,1,2),
])
cases.extend([
 ('mod-signs','def f(a,b):\n  return a % b\nprint f(7,3)\nprint f(-7,3)\nprint f(7,-3)\nprint f(-7,-3)\n',1,1,4,0),
 ('mod-zero-remainder','def f(a,b):\n  return a % b\nprint f(0,3)\nprint f(6,-3)\nprint f(-6,3)\n',1,1,3,0),
 ('mod-boundaries','def f(a,b):\n  return a % b\nprint f(-536870912,-1)\nprint f(536870911,-536870912)\nprint f(-536870912,536870911)\n',1,1,3,0),
 ('mod-zero-divisor','def f(a,b):\n  return a % b\nprint f(7,3)\ntry:\n  print f(1,0)\nexcept as e:\n  print e\nprint f(-7,3)\n',1,1,2,1),
 ('mod-type-fallback','def f(a,b):\n  return a % b\nprint f(7,3)\nprint f(7.5,3)\nprint f(536870912,3)\n',1,1,1,2),
 ('mod-bool-refused','def f(n):\n  return n % true\ntry:\n  print f(1)\nexcept as e:\n  print e\n',1,0,0,0),
 ('mod-multiple','def f(n):\n  return (n % 7) + (n % -3)\nprint f(20)\nprint f(-20)\n',1,1,2,0),
 ('mod-overflow-replay','def f(n):\n  return (n * n) % 3\nprint f(2)\nprint f(536870911)\n',1,1,1,1),
])
cases.extend([
 ('bool-equality','def f(a,b):\n  return (a < 0) == (b < 0)\nprint json_str([f(-1,-2), f(-1,2), f(1,2)])\n',1,1,3,0),
 ('bool-inequality','def f(a,b):\n  return (a < 0) != (b < 0)\nprint json_str([f(-1,-2), f(-1,2), f(1,2)])\n',1,1,3,0),
 ('bool-eq-literal','def f(n):\n  return (n < 3) == false\nprint f(2)\nprint f(4)\n',1,1,2,0),
 ('bool-eq-branch','def f(n):\n  if (n < 3) != true:\n    return 7\n  return 2\nprint f(1)\nprint f(4)\n',1,1,2,0),
 ('bool-mixed-eq-refused','def f(n):\n  return (n < 3) == 1\nprint f(1)\nprint f(4)\n',1,0,0,0),
 ('bool-mixed-ne-refused','def f(n):\n  return 0 != (n < 3)\nprint f(1)\nprint f(4)\n',1,0,0,0),
 ('bool-order-refused','def f(n):\n  return (n < 3) < false\ntry:\n  print f(1)\nexcept as e:\n  print e\n',1,0,0,0),
 ('bool-eq-type-fallback','def f(n):\n  return (n < 3) == true\nprint f(1)\nprint f(1.5)\nprint f(4)\n',1,1,2,1),
])
cases.extend([
 ('phi-int-and','def f(a,b):\n  return a and b\nprint f(0,7)\nprint f(2,7)\nprint f(-2,-7)\n',1,1,3,0),
 ('phi-int-or','def f(a,b):\n  return a or b\nprint f(0,7)\nprint f(2,7)\nprint f(0,0)\n',1,1,3,0),
 ('phi-bool-and','def f(a,b):\n  return (a < 3) and (b < 3)\nprint json_str([f(1,2), f(1,4), f(4,1)])\n',1,1,3,0),
 ('phi-bool-or','def f(a,b):\n  return (a < 3) or (b < 3)\nprint json_str([f(1,4), f(4,1), f(4,4)])\n',1,1,3,0),
 ('phi-nested','def f(a,b,c):\n  return (a and b) or c\nprint f(0,2,3)\nprint f(1,2,3)\nprint f(1,0,3)\n',1,1,3,0),
 ('phi-result-use','def f(a,b):\n  return (a or b) * 2\nprint f(0,3)\nprint f(2,3)\n',1,1,2,0),
 ('phi-short-guard','def f(a,b):\n  return a or (b * b)\nprint f(2,536870911)\nprint f(0,536870911)\nprint f(0,3)\n',1,1,2,1),
 ('phi-mixed-refused','def f(n):\n  return n or false\nprint f(0)\nprint f(2)\n',1,0,0,0),
 ('phi-type-fallback','def f(a,b):\n  return a or b\nprint f(0,3)\nprint f("", "x")\nprint f(2,3)\n',1,1,2,1),
])
cases.extend([
 ('local-int','def f(n):\n  x = n + 1\n  return x * 2\nprint f(2)\nprint f(-3)\n',1,1,2,0),
 ('local-chain','def f(n):\n  x = n + 1\n  y = x * 2\n  return x + y\nprint f(2)\nprint f(-3)\n',1,1,2,0),
 ('local-bool','def f(n):\n  x = n < 3\n  y = not x\n  return x != y\nprint json_str([f(1), f(4)])\n',1,1,2,0),
 ('local-overflow','def f(n):\n  x = n * n\n  return x - x\nprint f(536870911)\nprint f(2)\n',1,1,1,1),
 ('local-type-fallback','def f(n):\n  x = n + n\n  return x\nprint f(2)\nprint f("a")\n',1,1,1,1),
 ('local-reassign','def f(n):\n  x = n + 1\n  x = x + 2\n  return x\nprint f(2)\n',1,1,1,0),
 ('local-param-write','def f(n):\n  n = n + 1\n  return n\nprint f(2)\n',1,1,1,0),
 ('local-param-diamond','def f(n):\n  if n < 0:\n    n = 0 - n\n  return n\nprint f(-3)\nprint f(5)\n',1,1,2,0),
 ('local-param-chain','def f(n):\n  n = n + 1\n  n = n * 2\n  return n\nprint f(3)\n',1,1,1,0),
 ('local-param-overflow','def f(n):\n  n = n * n\n  return n\nprint f(536870911)\nprint f(3)\n',1,1,1,1),
 ('local-param-type-fallback','def f(n):\n  n = n + n\n  return n\nprint f(2)\nprint f("a")\n',1,1,1,1),
 ('local-param-two','def f(a,b):\n  a = a + b\n  b = b * 2\n  return a + b\nprint f(2,3)\n',1,1,1,0),
 ('local-branch','def f(n):\n  x = n + 1\n  if n < 0:\n    return x\n  return x * 2\nprint f(-2)\nprint f(2)\n',1,1,2,0),
 ('local-join','def f(a,b):\n  x = a + b\n  c = a and b\n  return x + c\nprint f(0,7)\nprint f(2,7)\nprint f(-2,-7)\n',1,1,3,0),
 ('local-nested-branch','def f(a,b):\n  x = a * 2\n  if a < b:\n    if a == 0:\n      return x + b\n    return x - a\n  return x\nprint f(0,3)\nprint f(2,4)\nprint f(5,1)\n',1,1,3,0),
 ('local-bool-branch','def f(n):\n  x = n < 3\n  if x:\n    return x\n  return false\nprint json_str([f(1), f(4)])\n',1,1,2,0),
 ('local-cross-overflow','def f(n):\n  x = n * n\n  if n < 0:\n    return x\n  return x + 1\nprint f(536870911)\nprint f(-2)\n',1,1,1,1),
 ('local-cross-type-fallback','def f(n):\n  x = n + n\n  if n:\n    return x\n  return x\nprint f(2)\nprint f("a")\n',1,1,1,1),
 ('local-branch-store-refused','def f(n):\n  if n < 0:\n    x = n + 1\n  return x\ntry:\n  print f(-2)\n  print f(2)\nexcept:\n  print "caught"\nprint "done"\n',1,0,0,0),
 ('local-diamond','def f(n):\n  if n < 0:\n    x = 0 - n\n  else:\n    x = n\n  return x * 2\nprint f(-2)\nprint f(2)\n',1,1,2,0),
 ('local-diamond-bool','def f(n):\n  if n < 0:\n    x = n < -1\n  else:\n    x = n > 1\n  return x\nprint json_str([f(-2), f(0), f(3)])\n',1,1,3,0),
 ('local-diamond-chain','def f(a,b):\n  if a < b:\n    x = a\n  else:\n    x = b\n  y = x * 2\n  return y\nprint f(2,5)\nprint f(7,3)\n',1,1,2,0),
 ('local-diamond-overflow','def f(n):\n  x = n * n\n  if n < 0:\n    y = 0 - n\n  else:\n    y = n\n  return x + y\nprint f(536870911)\nprint f(-2)\nprint f(3)\n',1,1,2,1),
 ('local-diamond-type-fallback','def f(n):\n  if n:\n    x = 1\n  else:\n    x = 2\n  return x\nprint f(2)\nprint f("a")\n',1,1,1,1),
 ('local-diamond-mixed-refused','def f(n):\n  if n < 0:\n    x = n < 0\n  else:\n    x = n\n  return x\nprint f(-2)\nprint f(2)\n',1,0,0,0),
 ('local-outer-then-inner','def f(n):\n  x = n + 1\n  if n < 0:\n    x = 0 - x\n  return x\nprint f(-2)\nprint f(2)\n',1,1,2,0),
 ('local-mutable-chain','def f(n):\n  x = n\n  x = x + 1\n  x = x * 2\n  x = x - 3\n  return x\nprint f(5)\nprint f(-2)\n',1,1,2,0),
 ('local-mutable-diamond-rebind','def f(n):\n  x = n\n  if n < 0:\n    x = x + 10\n  else:\n    x = x * 3\n  return x\nprint f(-1)\nprint f(2)\n',1,1,2,0),
 ('local-mutable-kind-change','def f(n):\n  x = n + 1\n  x = x < 3\n  return x\nprint json_str([f(1), f(4)])\n',1,1,2,0),
 ('local-mutable-overflow','def f(n):\n  x = n * n\n  x = x + 1\n  return x\nprint f(536870911)\nprint f(2)\n',1,1,1,1),
 ('local-mutable-after-join','def f(n):\n  if n < 0:\n    x = 1\n  else:\n    x = 2\n  x = x + 10\n  return x\nprint f(-1)\nprint f(2)\n',1,1,2,0),
 ('local-mutable-type-fallback','def f(n):\n  x = n + n\n  x = x + x\n  return x\nprint f(2)\nprint f("a")\n',1,1,1,1),
 ('local-before-bind-refused','x = 7\ndef f(n):\n  y = x + n\n  x = n + 1\n  return y + x\nprint f(2)\n',1,0,0,0),
 ('local-effect-refused','def f(n):\n  x = n + 1\n  print x\n  return x\nprint f(2)\n',1,0,0,0),
])
cases.extend([
 ('loop-countdown-sum','def f(n):\n  s = 0\n  while n > 0:\n    s = s + n\n    n = n - 1\n  return s\nprint f(5)\nprint f(10)\n',1,1,2,0),
 ('loop-zero-iterations','def f(n):\n  s = 0\n  while n > 0:\n    s = s + n\n    n = n - 1\n  return s\nprint f(0)\nprint f(-3)\n',1,1,2,0),
 ('loop-carried-bool','def f(n):\n  ok = false\n  while n > 0:\n    ok = true\n    n = n - 1\n  return ok\nprint f(3)\nprint f(0)\n',1,1,2,0),
 ('loop-overflow-fallback','def f(n):\n  s = 1\n  while n > 0:\n    s = s * 536870911\n    n = n - 1\n  return s\nprint f(2)\n',1,1,0,1),
 ('loop-type-fallback','def f(n):\n  while n > 0:\n    n = n - 1\n  return n\nprint f(3)\ntry:\n  print f("x")\nexcept:\n  print "caught"\nprint f(2)\n',1,1,2,1),
 ('loop-break','def f(n):\n  while n > 0:\n    if n < 3:\n      break\n    n = n - 1\n  return n\nprint f(5)\nprint f(2)\n',1,1,2,0),
 ('loop-nested-refused','def f(n):\n  while n > 0:\n    m = 2\n    while m > 0:\n      m = m - 1\n    n = n - 1\n  return n\nprint f(3)\n',1,0,0,0),
 ('loop-two-admitted','def f(n):\n  while n > 0:\n    n = n - 1\n  m = 2\n  while m > 0:\n    m = m - 1\n  return n\nprint f(3)\n',1,1,1,0),
])
cases.extend([
 ('loop-continue','def f(n):\n  s = 0\n  while n > 0:\n    n = n - 1\n    if n % 2 == 0:\n      continue\n    s = s + n\n  return s\nprint f(6)\nprint f(1)\n',1,1,2,0),
 ('loop-continue-bool','def f(n):\n  ok = false\n  while n > 0:\n    n = n - 1\n    if n % 2 != 0:\n      continue\n    ok = true\n  return ok\nprint f(3)\nprint f(2)\nprint f(1)\n',1,1,3,0),
 ('loop-two-independent','def f(n):\n  a = 0\n  while n > 0:\n    a = a + n\n    n = n - 1\n  b = 1\n  m = 3\n  while m > 0:\n    b = b * 2\n    m = m - 1\n  return a + b\nprint f(3)\nprint f(0)\n',1,1,2,0),
 ('loop-three-sequential','def f(n):\n  a = 0\n  while a < n:\n    a = a + 1\n  b = 0\n  while b < n:\n    b = b + 2\n  c = 0\n  while c < n:\n    c = c + 3\n  return a + b + c\nprint f(6)\n',1,1,1,0),
 ('loop-inside-branch','def f(n):\n  if n < 0:\n    m = 0 - n\n  else:\n    m = n\n  s = 0\n  while m > 0:\n    s = s + m\n    m = m - 1\n  return s\nprint f(-3)\nprint f(2)\n',1,1,2,0),
 ('loop-latch-mixed-kind-refused','def f(n):\n  x = 0\n  while n > 0:\n    x = n < 2\n    n = n - 1\n  return x\nprint f(3)\n',1,0,0,0),
])
for op in ('<','<=','>','>=','==','!='):
 cases.append(('bool-compare-'+op,f'def f(a,b):\n  return a {op} b\nprint f(-2,3)\nprint f(3,-2)\nprint f(4,4)\n',1,1,3,0))
 source=f'def f(a,b):\n  if a {op} b:\n    return a + 1\n  return b - 1\n'
 source+=''.join(f'print f({a},{b})\n' for a,b in [(-2,3),(3,-2),(4,4)])
 cases.append(('compare-'+op,source,1,1,3,0))
# Eligible IR can exceed the native code-page budget. Optimization refusal
# must preserve execution and release the partially allocated mapping.
long_expr = ' + '.join(['n'] * 50)
cases.append(('code-budget', f'def f(n):\n  return {long_expr}\nprint f(1)\nprint f(2)\n',1,0,0,0))
with tempfile.TemporaryDirectory(prefix='hs-hotleaf.') as d:
 d=Path(d);exe=d/'runner'
 r=run([ROOT/'bootstrap/hs-hosted-x86_64',ROOT/'selfhost/be/hotleaf_run.holy',exe]);assert r.returncode==0,r.stderr
 for name,source,threshold,compiled,calls,fallbacks in cases:
  src=d/'case.holy';dest=d/'stats.json';src.write_text(source)
  ref=run([sys.executable,ROOT/'interp.py',src]);got=run([exe,src,threshold,dest])
  assert (got.returncode,got.stdout)==(ref.returncode,ref.stdout),(name,got.stdout,got.stderr,ref.stdout)
  if ref.returncode==0:assert got.stderr==ref.stderr,(name,got.stderr)
  else:assert b'after native' in got.stderr
  stats=json.loads(dest.read_text())
  assert stats['compiled']==compiled,(name,stats)
  assert stats['calls']==calls,(name,stats)
  assert stats['fallbacks']==fallbacks,(name,stats)
  assert stats['live'] is False,(name,stats)
 unit=d/'ownership.holy'
 unit.write_text('import hotleaf\nimport normalize\nimport irbuild\nm = irbuild.build_module(normalize.parse("def f(n):\\n  return n + 1\\n"), "")\nkey = m["order"][0]\nfn = m["funcs"][key]\nc = hotleaf.create(1, 1, 1)\nassert hotleaf.dispatch(c, key, fn, [2]) == [true, 3]\nassert hotleaf.dispatch(c, "other", fn, [3]) == [false, null]\nassert c["dropped"] == 1\nptr = c["images"][0]["ptr"]\nfound = false\nfor row in split(read_text("/proc/self/maps"), "\\n"):\n  words = split(row)\n  if len(words) > 1:\n    bounds = split(words[0], "-")\n    if len(bounds[0]) <= 12 and len(bounds[1]) <= 12:\n      if int("0x" + bounds[0]) <= ptr and int("0x" + bounds[1]) > ptr:\n        assert words[1] == "r-xp"\n        found = true\nassert found\nhotleaf.release(c)\nassert not c["images"][0]["live"]\nrejected = false\ntry:\n  hotleaf.dispatch(c, key, fn, [3])\nexcept:\n  rejected = true\nassert rejected\nc = hotleaf.create(1, 4, 1)\nhotleaf.dispatch(c, key, fn, [2])\nassert hotleaf.dispatch(c, "other", fn, [2]) == [false, null]\nassert c["compiled"] == 1 and c["rejected"] == 1\nhotleaf.release(c)\nprint "ok"\n')
 r=run([ROOT/'bootstrap/hs-hosted-x86_64',unit,d/'ownership']);assert r.returncode==0,r.stderr
 r=run([d/'ownership']);assert r.returncode==0 and r.stdout==b'ok\n',(r.stdout,r.stderr)
 print(f'{len(cases)+1}/{len(cases)+1} hot pure-leaf parity/guard/teardown cases')
