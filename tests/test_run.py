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
TESTSRC = ("def test_ok():\n  assert 1 + 1 == 2\n"
           "def test_bad():\n  assert 1 == 2, \"nope\"\n"
           "def test_boom():\n  x = [1][3]\n"
           "def helper():\n  return 1\n")
with tempfile.TemporaryDirectory() as d:
    tp = os.path.join(d, "test_x.hs")
    open(tp, "w").write(TESTSRC)
    r = subprocess.run([sys.executable, HS, "test", d],
                       capture_output=True, text=True)
    check("hs test reports pass and fail, exit 1",
          r.returncode == 1 and "ok   " in r.stdout and "test_ok" in r.stdout
          and "FAIL" in r.stdout and "nope" in r.stdout
          and "1 passed, 2 failed" in r.stdout, (r.returncode, r.stdout))
    r = subprocess.run([sys.executable, HS, "--json", "test", tp],
                       capture_output=True, text=True)
    import json
    j = json.loads(r.stdout)
    check("hs test --json", j["passed"] == 1 and j["failed"] == 2
          and [x["test"] for x in j["results"]]
          == ["test_ok", "test_bad", "test_boom"]
          and "helper" not in r.stdout, r.stdout)
    open(tp, "w").write("def test_a():\n  assert true\n")
    r = subprocess.run([sys.executable, HS, "test", tp],
                       capture_output=True, text=True)
    check("hs test all green exits 0", r.returncode == 0
          and "1 passed, 0 failed" in r.stdout, (r.returncode, r.stdout))
    check("hs test leaves no temp file", os.listdir(d) == ["test_x.hs"],
          os.listdir(d))
r = subprocess.run([sys.executable, HS, "repl"], capture_output=True, text=True,
                   input="x = 5\nx * 2\ndef f(a):\n  return a + x\n\nf(1)\n"
                         "print \"hi\"\nnope\nf(2)\nnull\n")
check("hs repl keeps state, echoes values, survives errors",
      r.returncode == 0 and r.stdout.splitlines()
      == ["10", "6", "hi", "error: unknown variable 'nope' at line 1", "7"],
      (r.returncode, r.stdout, r.stderr))
WB = 'write_bytes("/tmp/_hs_wb.bin", [0, 1, 127, 128, 200, 255, 10])\nprint system("test $(wc -c < /tmp/_hs_wb.bin) -eq 7")\nprint system("test \\"$(od -An -tu1 /tmp/_hs_wb.bin | xargs)\\" = \\"0 1 127 128 200 255 10\\"")\nprint system("test -x /tmp/_hs_wb.bin")\ntry:\n  write_bytes("/tmp/_hs_wb.bin", [256])\nexcept as e:\n  print e\ntry:\n  write_bytes("/tmp/_hs_wb.bin", "x")\nexcept as e:\n  print e\nsystem("rm -f /tmp/_hs_wb.bin")\n'
WB_OUT = '0\n0\n0\nwrite_bytes wants a list of Ints 0..255 at line 6\nwrite_bytes wants write_bytes(path, [Int 0..255]) at line 10\n'
for be in ("interp", "native", "auto"):
    rc, out, err = run(WB, {"HS_BACKEND": be})
    check(f"write_bytes writes exact bytes, mode 755 ({be})",
          rc == 0 and out == WB_OUT, (rc, out, err))
with tempfile.TemporaryDirectory() as d:
    env = dict(os.environ, HS_CC_CACHE=os.path.join(d, "cache"))
    src = os.path.join(d, "p.hs")
    open(src, "w").write('def f(n):\n  if n < 2:\n    return n\n  return f(n - 1) + f(n - 2)\nprint f(20), "ok" + "!", [1, 2][1]\n')
    r = subprocess.run([sys.executable, HS, "cc", src, "-o", os.path.join(d, "p")],
                       capture_output=True, text=True, env=env)
    r2 = subprocess.run([os.path.join(d, "p")], capture_output=True, text=True)
    check("hs cc compiles with the compiler written in hs",
          r.returncode == 0 and r2.stdout == "6765 ok! 2\n", (r.stdout, r.stderr, r2.stdout))
    check("hs cc caches its own compiler ELF", len(os.listdir(os.path.join(d, "cache"))) == 1,
          os.listdir(os.path.join(d, "cache")))
    open(src, "w").write("print 1.5\n")
    r = subprocess.run([sys.executable, HS, "cc", src, "-o", os.path.join(d, "q")],
                       capture_output=True, text=True, env=env)
    check("hs cc rejects what the cc subset cannot do",
          r.returncode != 0 and "error:" in r.stdout + r.stderr and not os.path.exists(os.path.join(d, "q")),
          (r.returncode, r.stdout, r.stderr))
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
