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

# ---- fmt keeps comments (nothing is lost, structure unchanged, idempotent) ----
sys.path.insert(0, ROOT)
import fmt as _fmt  # noqa: E402
import interp as _interp  # noqa: E402
_CM = open(os.path.join(ROOT, "tests", "fmt_comments.hs.txt")).read()
with tempfile.TemporaryDirectory() as d:
    cp = os.path.join(d, "c.hs")
    open(cp, "w").write(_CM)
    r1 = subprocess.run([sys.executable, HS, "fmt", cp], capture_output=True, text=True)
    open(cp, "w").write(r1.stdout)
    r2 = subprocess.run([sys.executable, HS, "fmt", cp], capture_output=True, text=True)
    r3 = subprocess.run([sys.executable, HS, "fmt", "--check", cp], capture_output=True, text=True)
    nc = len(_fmt.extract_comments(_CM)[0]) + len(_fmt.extract_comments(_CM)[1])
    no = len(_fmt.extract_comments(r1.stdout)[0]) + len(_fmt.extract_comments(r1.stdout)[1])
    check("fmt keeps every comment", r1.returncode == 0 and nc == no and nc >= 8, (nc, no, r1.stderr))
    check("fmt with comments is idempotent", r2.stdout == r1.stdout, (r1.stdout, r2.stdout))
    check("fmt --check passes on formatted commented file", r3.returncode == 0, r3.stderr)
bad = []
nfiles = 0
for sub in ("tests", "selfhost", "kernel", "bench", "examples"):
    dd = os.path.join(ROOT, sub)
    if not os.path.isdir(dd):
        continue
    for fn in sorted(os.listdir(dd)):
        if not fn.endswith(".hs"):
            continue
        src = open(os.path.join(dd, fn), encoding="utf-8").read()
        try:
            _interp.reset_parse_state()
            plain = _fmt.fmt_program(_interp.parse_program(src, raw=True))
            _interp.reset_parse_state()
            withc = _fmt.fmt_program_c(_interp.parse_program(src, raw=True), src)
        except Exception:
            continue
        nfiles += 1
        a = _fmt.extract_comments(src)
        b = _fmt.extract_comments(withc)
        if len(a[0]) + len(a[1]) != len(b[0]) + len(b[1]) or \
                _fmt.squash(_fmt.strip_comments(withc)) != _fmt.squash(plain):
            bad.append(fn)
check("fmt with comments: all repo .hs keep comments and structure", not bad and nfiles > 50, (bad[:5], nfiles))

# ---- hs explain: error message -> meaning + fix from docs/errors.md ----
def explain(msg, js=False):
    cmd = [sys.executable, HS] + (["--json"] if js else []) + ["explain", msg]
    return subprocess.run(cmd, capture_output=True, text=True)


import json as _json  # noqa: E402
r = explain("error: cannot add Int and Str at line 4")
check("explain curated error (strips error: / at line)", r.returncode == 0 and "str(x) + str(y)" in r.stdout, r.stdout)
r = explain("key 'zz' not found at line 9")
check("explain matches <placeholder> patterns", r.returncode == 0 and "Dict" in r.stdout, r.stdout)
r = explain("alloc of negative size -3", js=True)
j = _json.loads(r.stdout)
check("explain --json lists catalog matches", r.returncode == 0 and j["matches"] and j["matches"][0]["pattern"].startswith("alloc of negative"), r.stdout)
r = explain("zzz nonsense")
check("explain unknown message exits 1", r.returncode == 1 and "no catalog entry" in r.stdout, (r.returncode, r.stdout))

# ---- evals/: programming-task checker (no model calls) ----
EV = os.path.join(ROOT, "evals", "run.py")
r = subprocess.run([sys.executable, EV, "--reference", "--json"], capture_output=True, text=True)
j = _json.loads(r.stdout) if r.stdout.startswith("{") else {}
check("evals: every reference solution passes its task", r.returncode == 0 and j.get("passed") == j.get("total") and j.get("total", 0) >= 24, r.stdout[:300])
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "gcd.hs"), "w").write("print 1\n")
    r = subprocess.run([sys.executable, EV, "--solutions", d, "--task", "gcd", "--json"], capture_output=True, text=True)
    j = _json.loads(r.stdout)
    check("evals: a wrong solution fails", r.returncode == 1 and j["passed"] == 0 and j["tasks"][0]["failed"], r.stdout[:300])
    r = subprocess.run([sys.executable, EV, "--solutions", d, "--task", "fizzbuzz", "--json"], capture_output=True, text=True)
    j = _json.loads(r.stdout)
    check("evals: a missing solution fails", r.returncode == 1 and j["tasks"][0]["failed"] == ["missing solution"], r.stdout[:300])
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
