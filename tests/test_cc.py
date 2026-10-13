#!/usr/bin/env python3
"""selfhost/cc.hs: the compiler written in hs emits a static x86-64 ELF.
Each program is run through the reference interpreter and through the
compiled ELF; stdout must match. Programs outside the subset must be a
compile error (never silently different output)."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HS = os.path.join(ROOT, "hs.py")
CC = os.path.join(ROOT, "selfhost", "cc.hs")
total = fails = 0

PROGS = {
    "fib": "def fib(n):\n  if n < 2:\n    return n\n  return fib(n - 1) + fib(n - 2)\nprint fib(22)\n",
    "arith": "a = 17\nb = 5\nprint a + b, a - b, a * b, a % b, -a % b, a % -b, -a % -b\n"
             "print 0, -1, 4611686018427387903, -4611686018427387903\n",
    "bits": "x = 0xF0F0\nprint x & 255, x | 15, x ^ 255, x << 4, x >> 4, -256 >> 4\n",
    "loop": "i = 0\nt = 0\nwhile i < 1000:\n  t = t + i * i % 7\n  i = i + 1\nprint t\n",
    "breakcont": "i = 0\nt = 0\nwhile 1 == 1:\n  i = i + 1\n  if i % 2 == 0:\n    continue\n"
                 "  if i > 21:\n    break\n  t = t + i\nprint t, i\n",
    "elif": "def sign(n):\n  if n < 0:\n    return -1\n  elif n == 0:\n    return 0\n  else:\n    return 1\n"
            "print sign(-5), sign(0), sign(9)\n",
    "args": "def f(a, b, c, d):\n  return a * 1000 + b * 100 + c * 10 + d\nprint f(1, 2, 3, 4)\n",
    "globals": "k = 10\ndef add(x):\n  return x + k\nk = 32\nprint add(1)\n",
    "locals": "def g(n):\n  s = 0\n  i = 0\n  while i < n:\n    s = s + i\n    i = i + 1\n  return s\n"
              "i = 99\nprint g(10), i\n",
    "strings": 'print "hello, world"\nprint "a", 1, "b"\nprint ""\nprint "tab\\there"\n',
    "andor": "a = 3\nb = 4\nif a < b and b < 10 or a == 0:\n  print 1\nif not (a < b):\n  print 2\n"
             "else:\n  print 3\n",
    "deep": "def s(n):\n  if n == 0:\n    return 0\n  return n + s(n - 1)\nprint s(1000)\n",
    "mutual": "def ev(n):\n  if n == 0:\n    return 1\n  return od(n - 1)\ndef od(n):\n  if n == 0:\n    return 0\n"
              "  return ev(n - 1)\nprint ev(10), od(7), ev(7)\n",
    "bools": "x = 1 < 2\nprint x, 1 > 2, true, false, null, not x, not 0, not 5\nprint true == 1, 1 == true, null == false, 3 != 4\n",
    "andor_val": "x = 5 and 7\nprint x, 0 or 9, null or 3, 1 and null, false or false\n",
    "truthy": "if 0:\n  print 1\nelse:\n  print 2\nif null:\n  print 3\nif -1:\n  print 4\nif false or 0:\n  print 5\nelse:\n  print 6\n",
    "boolarg": "def f(a, b):\n  if a:\n    return b\n  return a\nprint f(1 < 2, 5), f(2 < 1, 5), f(null, 1)\n",
    "bigint": "x = 4611686018427387903\nprint x, -x, x - 1, -x - 1\n",
    "str_basic": 's = "hello" + " " + "world"\nprint s, len(s), s[0], s[-1], s[4]\nprint s == "hello world", s != "x", "a" < "b", "ab" < "a", "b" >= "b", "" == ""\nprint "" or "dflt", "x" and "y", not ""\ndef rep(a, n):\n  r = ""\n  i = 0\n  while i < n:\n    r = r + a\n    i = i + 1\n  return r\nt = rep("ab", 50)\nprint len(t), t[99], t == rep("ab", 50), rep("x", 3) + "!"\n',
    "str_eq": "a = \"x\" + \"y\"\nprint a == \"xy\", \"xy\" == a, a == 1, 1 == a, a == null, a != \"xz\"\nprint \"abc\" < \"abd\", \"abc\" <= \"abc\", \"b\" > \"abc\", \"\" < \"a\"\n",
    "str_fn": "def f(s, n):\n  if n == 0:\n    return s\n  return f(s + s, n - 1)\nx = f(\"ab\", 10)\nprint len(x), x[1023], x[-1], len(f(\"\", 5))\n",
    "str_print": "print \"a\", \"b\" + \"c\", 1, \"d\"\nx = \"q\"\nprint x, true\n",
    'list_basic': 'x = [1, "a", true, null, [2, 3], ""]\nprint x\nprint len(x), x[1], x[-1]\nx[0] = 9\nappend(x, 7)\nprint x == [9, "a", true, null, [2, 3], "", 7], [] == [], [1] == [2], x[4][1]\nprint not [], [] or 5\nfor v in [1, 2]:\n  print v\nfor i in range(3):\n  print i\n',
    'list_grow': 'xs = []\nfor i in range(1000):\n  append(xs, i * i)\nt = 0\nfor v in xs:\n  t = t + v\nprint len(xs), t, xs[999], xs[-1], xs[500]\nys = [xs[3], xs[4]]\nprint ys\n',
    'sieve': 'def sieve(n):\n  p = []\n  i = 0\n  while i <= n:\n    append(p, true)\n    i = i + 1\n  p[0] = false\n  p[1] = false\n  for i in range(2, n + 1):\n    if p[i]:\n      j = i * i\n      while j <= n:\n        p[j] = false\n        j = j + i\n  out = []\n  for i in range(n + 1):\n    if p[i]:\n      append(out, i)\n  return out\nprint sieve(100)\nprint len(sieve(5000))\n',
    'for_ctl': 'for i in range(10):\n  if i == 2:\n    continue\n  if i == 6:\n    break\n  for j in range(i, 3):\n    print i, j\nprint "done"\nfor i in range(5, 3):\n  print "never"\n',
    'list_eq': 'a = [1, [2, "x"], [], "s"]\nb = [1, [2, "x"], [], "s"]\nprint a == b, a != b, a == [1], [1, 2] == [1, 3], [[1]] == [[1]], [1] == 1, "a" == ["a"]\nb[1][1] = "y"\nprint a == b, b\n',
    'list_fn': 'def mk(n):\n  r = []\n  for i in range(n):\n    append(r, [i, "v" + "x"])\n  return r\ndef total(xs):\n  t = 0\n  for p in xs:\n    t = t + p[0]\n  return t\nq = mk(20)\nprint total(q), len(q), q[19], q[-20]\n',
    "noreturn": "def p(n):\n  print n\np(5)\np(6)\n",
}

ERRS = {
    'list_oob': 'x = [1]\nprint 1\nprint x[1]\n',
    'list_set_oob': 'x = [1]\nx[1] = 2\n',
    'list_idx_type': 'x = [1]\nprint x[true]\n',
    'for_int': 'for v in 5:\n  print v\n',
    'append_int': 'append(3, 4)\n',
    'range_type': 'for i in range("a"):\n  print i\n',
    "str_plus_int": "print 1\nprint \"a\" + 1\n",
    "str_cmp_int": "print 2\nprint \"a\" < 1\n",
    "str_idx_oob": "s = \"abc\"\nprint 3\nprint s[3]\n",
    "str_idx_neg_oob": "s = \"abc\"\nprint s[-3]\nprint s[-4]\n",
    "str_idx_type": "s = \"abc\"\nprint s[\"a\"]\n",
    "len_int": "print len(5)\n",
}

BAD = {
    "float": "print 1.5\n",
    "div": "print 7 / 2\n",
    "unknown": "print y\n",
    "bigliteral": "print 4611686018427387904\n",
    "arity": "def f(a):\n  return a\nprint f(1, 2)\n",
    "range3": "for i in range(0, 5, 2):\n  print i\n",
}


def interp(path):
    r = subprocess.run([sys.executable, HS, "run", path, "--backend", "interp"],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def compile_prog(path, out, backend="interp"):
    return subprocess.run([sys.executable, HS, "run", CC, "--backend", backend,
                           path, out], capture_output=True, text=True)


def check(name, cond, detail=""):
    global total, fails
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        fails += 1
        print(f"FAIL {name}", detail)


with tempfile.TemporaryDirectory() as d:
    for name, src in PROGS.items():
        p = os.path.join(d, name + ".hs")
        out = os.path.join(d, name + ".bin")
        open(p, "w").write(src)
        rc, want = interp(p)
        c = compile_prog(p, out)
        if c.returncode != 0:
            check(f"cc {name}", False, c.stderr + c.stdout)
            continue
        r = subprocess.run([out], capture_output=True, text=True)
        check(f"cc {name}", rc == 0 and r.returncode == 0 and r.stdout == want,
              (rc, want, r.returncode, r.stdout, r.stderr))
    for name, src in ERRS.items():
        p = os.path.join(d, "err_" + name + ".hs")
        out = os.path.join(d, "err_" + name + ".bin")
        open(p, "w").write(src)
        rc, want = interp(p)
        c = compile_prog(p, out)
        if c.returncode != 0:
            check(f"cc err {name}", False, c.stderr + c.stdout)
            continue
        r = subprocess.run([out], capture_output=True, text=True)
        check(f"cc err {name}", rc != 0 and r.returncode != 0 and r.stdout == want,
              (rc, want, r.returncode, r.stdout, r.stderr))
    for name, src in BAD.items():
        p = os.path.join(d, "bad_" + name + ".hs")
        out = os.path.join(d, "bad_" + name + ".bin")
        open(p, "w").write(src)
        c = compile_prog(p, out)
        check(f"cc rejects {name}", c.returncode != 0 and "error:" in c.stdout
              and not os.path.exists(out), (c.returncode, c.stdout, c.stderr))
    # the same compiler run natively (gcc) emits identical bytes
    p = os.path.join(d, "fib.hs")
    o1, o2 = os.path.join(d, "fib.i"), os.path.join(d, "fib.n")
    compile_prog(p, o1, "interp")
    c = compile_prog(p, o2, "native")
    same = c.returncode == 0 and open(o1, "rb").read() == open(o2, "rb").read()
    check("cc.hs: interp and native emit identical ELF", same, c.stderr[-300:])
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
