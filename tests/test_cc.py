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
             "print 0, -1, 9223372036854775807, -9223372036854775807\n",
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
    "noreturn": "def p(n):\n  print n\np(5)\np(6)\n",
}

BAD = {
    "float": "print 1.5\n",
    "list": "x = [1]\nprint x\n",
    "div": "print 7 / 2\n",
    "boolprint": "print 1 < 2\n",
    "boolstore": "x = 1 < 2\nprint x\n",
    "unknown": "print y\n",
    "arity": "def f(a):\n  return a\nprint f(1, 2)\n",
    "boollit": "x = true\nprint x\n",
    "for": "for i in range(3):\n  print i\n",
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
