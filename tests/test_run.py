#!/usr/bin/env python3
"""`hs run` backend selection: x64 by default, automatic fallback, overrides."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HS = os.path.join(ROOT, "hs.py")
total = fails = 0


def run(src, env=None, args=()):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "p.hs")
        open(p, "w").write(src)
        e = dict(os.environ)
        e.pop("HS_BACKEND", None)
        e.update(env or {})
        r = subprocess.run([sys.executable, HS, "run", p] + list(args),
                           capture_output=True, text=True, env=e)
        return r.returncode, r.stdout, r.stderr


def check(name, cond, detail=""):
    global total, fails
    total += 1
    if cond:
        print("ok  ", name)
    else:
        fails += 1
        print("FAIL", name, detail)


BIG = "x = 2305843009213693951\nprint x + 10\n"      # needs 62+ bits
BIG_OUT = "2305843009213693961\n"

rc, out, err = run("print 6 * 7\n")
check("default run works", rc == 0 and out == "42\n", (rc, out, err))
rc, out, err = run("print 6 * 7\n", {"HS_BACKEND": "x64"})
check("HS_BACKEND=x64", rc == 0 and out == "42\n", (rc, out, err))
rc, out, err = run("print 6 * 7\n", {"HS_BACKEND": "interp"})
check("HS_BACKEND=interp", rc == 0 and out == "42\n", (rc, out, err))
rc, out, err = run("print 6 * 7\n", args=["--backend", "interp"])
check("--backend flag", rc == 0 and out == "42\n", (rc, out, err))
rc, out, err = run("print 1\n", {"HS_BACKEND": "bogus"})
check("bad backend name", rc == 2, (rc, out, err))
rc, out, err = run(BIG, {"HS_BACKEND": "x64"})
check("x64 traps instead of wrapping", rc == 97 and "62-bit" in err
      and out == "", (rc, out, err))
rc, out, err = run(BIG, {"HS_BACKEND": "interp"})
check("interp keeps 64-bit Int", out == BIG_OUT, (rc, out, err))
rc, out, err = run(BIG)
check("auto falls back before any output", out == BIG_OUT and rc == 0,
      (rc, out, err))
rc, out, err = run("print 1\n" + BIG)
check("trap after output is loud, not silent",
      rc == 97 and out == "1\n" and "62-bit" in err and "hint" in err,
      (rc, out, err))
rc, out, err = run("x = 4294967296\nprint x * x\n", {"HS_BACKEND": "x64"})
check("multiply overflow traps", rc == 97, (rc, out, err))
rc, out, err = run("x = 0xFFFFFFFFFFFFFFF0\nprint x & 255\n")
check("big literal falls back", out == "240\n" and rc == 0, (rc, out, err))
rc, out, err = run("print true == 1, 1 == true, false == 0, true == 2\n")
check("Bool == Int like interp", out == "true true true false\n",
      (rc, out, err))
REC = "def f(n):\n  return f(n + 1) + 1\nprint f(0)\n"
for be in ("interp", "native", "x64"):
    rc, out, err = run(REC, {"HS_BACKEND": be})
    check(f"runaway recursion is a clean error ({be})",
          rc == 1 and "stack overflow" in err and out == "", (rc, out, err))
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
