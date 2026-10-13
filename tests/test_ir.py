#!/usr/bin/env python3
"""holyshit IR tests: python3 tests/test_ir.py

Every CASE runs on both interp.py (reference) and ir.py and must agree
byte-for-byte on stdout, stderr and exit code. Plus verifier/builder
unit tests and a dump smoke test.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import interp
import ir as IR

CASES = [
    ("arith",
     "print 1 + 2 * 3\nprint 7 / 2\nprint 7 % 3\nprint 1.5e3\n",
     "7\n3.5\n1\n1500.0\n", "", 0),
    ("strings",
     'print "a" + "b"\nprint "x", "y"\n',
     "ab\nx y\n", "", 0),
    ("compare",
     "print 1 < 2 < 3\nprint 1 == 1\nprint 1 != 2\nprint \"a\" < \"b\"\n",
     "true\ntrue\ntrue\ntrue\n", "", 0),
    ("bitwise",
     "print 6 & 3, 6 | 3, 6 ^ 3\nprint 1 << 4, 16 >> 2\nprint ~5\n",
     "2 7 5\n16 4\n-6\n", "", 0),
    ("ifelse",
     "x = 2\nif x < 1:\n  print \"small\"\nelif x < 3:\n  print \"mid\"\nelse:\n  print \"big\"\n",
     "mid\n", "", 0),
    ("while",
     "i = 0\ns = 0\nwhile i < 5:\n  i = i + 1\n  if i == 3:\n    continue\n  if i == 5:\n    break\n  s = s + i\nprint s\n",
     "7\n", "", 0),
    ("fib",
     "def fib(n):\n  if n < 2:\n    return n\n  return fib(n - 1) + fib(n - 2)\nprint fib(10)\n",
     "55\n", "", 0),
    ("closure",
     "def o():\n  x = 1\n  def i():\n    return x\n  x = 2\n  return i()\nprint o()\n",
     None, "", 0),  # value pinned by interp below
    ("global",
     "g = 0\ndef bump():\n  global g\n  g = g + 1\nbump()\nbump()\nprint g\n",
     "2\n", "", 0),
    ("shortcircuit",
     "print true or 1 / 0\nprint 0 and 1 / 0\nprint not 0\nprint -3, -0.5\n",
     "true\n0\ntrue\n-3 -0.5\n", "", 0),
    ("builtins",
     "print len(\"abc\"), str(7), int(\"42\"), float(\"1e3\")\nprint 0.1, 1e16\n",
     "3 7 42 1000.0\n0.1 1e+16\n", "", 0),
    ("divzero", "print 1 / 0\n", "", "error: division by zero at line 1\n", 1),
    ("unknown", "print y\n", "", "error: unknown variable 'y' at line 1\n", 1),
    ("arity",
     "def f(a, b):\n  return a\nf(1)\n", "",
     "error: f wants 2 args, got 1 at line 3\n", 1),
    ("typeadd", "print 1 + \"a\"\n", "",
     "error: cannot add Int and Str at line 1\n", 1),
    ("condvar",
     "if true:\n  x = 1\nprint x\nif false:\n  y = 2\nprint y\n",
     "1\n", None, 1),  # trailing error text pinned by interp, not by hand
    ("listlit",
     "print [1, 2, 3]\nprint []\nprint [[1], [2, 3]]\nprint [1] + [2]\n",
     "[1, 2, 3]\n[]\n[[1], [2, 3]]\n[1, 2]\n", "", 0),
    ("index",
     'print [10, 20, 30][0], [10, 20, 30][-1]\nprint "abc"[1]\n'
     "l = [1, 2]\nl[0] = 9\nprint l\n",
     "10 30\nb\n[9, 2]\n", "", 0),
    ("dict",
     'd = {"a": 1}\nprint d["a"]\nd["b"] = 2\nprint d\n',
     '1\n{a: 1, b: 2}\n', "", 0),
    ("slice",
     'print [1, 2, 3, 4][1:3]\nprint [1, 2, 3][:2]\nprint "hello"[1:]\n'
     'print [1, 2][2:1]\n',
     "[2, 3]\n[1, 2]\nello\n[]\n", "", 0),
    ("forrange",
     "s = 0\nfor i in range(5):\n  s = s + i\nprint s\n",
     "10\n", "", 0),
    ("forlist",
     's = ""\nfor x in ["a", "b"]:\n  s = s + x\nprint s\n',
     "ab\n", "", 0),
    ("forstr",
     'n = 0\nfor ch in "hey":\n  n = n + 1\nprint n\n',
     "3\n", "", 0),
    ("fordict",
     'd = {"x": 1, "y": 2}\nfor k in d:\n  print k, d[k]\n',
     "x 1\ny 2\n", "", 0),
    ("forbreak",
     "s = 0\nfor i in range(10):\n  if i == 3:\n    break\n  s = s + i\nprint s\n",
     "3\n", "", 0),
    ("forcontinue",
     "s = 0\nfor i in range(10):\n  if i % 2 == 0:\n    continue\n  s = s + i\nprint s\n",
     "25\n", "", 0),
    ("fornested",
     "n = 0\nfor i in range(3):\n  for j in range(3):\n    n = n + 1\nprint n\n",
     "9\n", "", 0),
    ("append",
     "l = []\nappend(l, 1)\nappend(l, 2)\nprint l, len(l)\n",
     "[1, 2] 2\n", "", 0),
    ("idxrange", "print [1][5]\n", "",
     "error: index out of range at line 1\n", 1),
    ("keymissing", 'd = {}\nprint d["k"]\n', "",
     "error: key 'k' not found at line 2\n", 1),
    ("notiter", "for x in 5:\n  print x\n", "",
     "error: not iterable: Int at line 1\n", 1),
    ("idxfloat", 'print [1, 2][1.0]\n', "",
     "error: index must be Int at line 1\n", 1),
    ("trybasic",
     'try:\n  print 1 / 0\nexcept:\n  print "caught"\nprint "after"\n',
     "caught\nafter\n", "", 0),
    ("tryas",
     'try:\n  1 + "a"\nexcept as e:\n  print e\n',
     "cannot add Int and Str at line 2\n", "", 0),
    ("tryfin",
     'try:\n  print "b"\nfinally:\n  print "f"\nprint "e"\n',
     "b\nf\ne\n", "", 0),
    ("tryfinexc",
     'try:\n  print 1 / 0\nfinally:\n  print "f"\n',
     None, None, 1),
    ("tryret",
     'def f():\n  try:\n    return 1\n  finally:\n    print "f"\nprint f()\n',
     "f\n1\n", "", 0),
    ("tryreraise",
     'try:\n  try:\n    raise "in"\n  except:\n    raise\nexcept as e:\n  print e\n',
     "in at line 3\n", "", 0),
    ("tryshadow",
     'x = 1\ntry:\n  print 1 / 0\nexcept as x:\n  print x\nprint x\n',
     None, "", 0),
    ("tryuncaught",
     'try:\n  print undefined\nfinally:\n  print "f"\n',
     None, None, 1),
    ("raisestr", 'raise "boom"\n', "", "error: boom at line 1\n", 1),
    ("unsafebasic",
     "unsafe:\n  Ptr p = alloc(16)\n  *p = 4660\n  print *p\n"
     "  print load8(p)\n",
     "4660\n52\n", "", 0),
    ("unsafeint",
     "unsafe:\n  I64 n = 10\n  I64 total = 0\n  while n > 0:\n"
     "    total = total + n\n    n = n - 1\n  print total\n"
     "  print 7 / 2\n  print -7 / 2\n  print 7 % 3\n",
     "55\n3\n-3\n1\n", "", 0),
    ("unsafebits",
     "unsafe:\n  print (6 & 3)\n  print (1 << 4)\n  print ~5\n",
     "2\n16\n-6\n", "", 0),
    ("unsafestruct",
     "unsafe:\n  struct P:\n    I64 x\n    I64 y\n  P* p = alloc(sizeof(P))\n"
     "  p.x = 3\n  p.y = 4\n  print p.x + p.y\n  print sizeof(P)\n",
     "7\n16\n", "", 0),
    ("unsafeerr",
     "unsafe:\n  Ptr p = null\n  print load8(p)\n",
     None, None, 1),
    ("unsafemix",
     "unsafe:\n  I64 x = 5\n  U64 y = 6\n  print x + y\n",
     None, None, 1),
]

fails = 0
total = 0


def run(py, path):
    return subprocess.run([sys.executable, py, path], capture_output=True,
                          text=True, timeout=60)


with tempfile.TemporaryDirectory() as d:
    for name, src, want_out, want_err, want_rc in CASES:
        total += 1
        p = os.path.join(d, name + ".hs")
        with open(p, "w") as f:
            f.write(src)
        a = run(f"{ROOT}/interp.py", p)
        b = run(f"{ROOT}/ir.py", p)
        same = (a.stdout == b.stdout and a.stderr == b.stderr and
                a.returncode == b.returncode)
        pinned = (want_out is None or b.stdout == want_out) and \
                 (want_err is None or b.stderr == want_err)
        ok = same and pinned and b.returncode == want_rc
        print(("ok  " if ok else "FAIL") + f" {name}")
        if not ok:
            fails += 1
            print(f"  interp: rc={a.returncode} out={a.stdout!r} "
                  f"err={a.stderr!r}")
            print(f"  ir:     rc={b.returncode} out={b.stdout!r} "
                  f"err={b.stderr!r}")


def build_src(src):
    interp.reset_parse_state()
    m = IR.build_module(interp.parse_program(src))
    IR.verify_module(m)
    return m


# verifier rejects hand-built bad IR
total += 1
try:
    IR.verify_module({"entry": "<main>", "order": ["<main>"], "funcs": {
        "<main>": {"name": "<main>", "dispname": "<main>", "params": [],
                   "globals": [],
                   "blocks": [
                       {"label": "b0", "instrs": [], "term":
                        {"term": "jmp", "line": 1, "to": "nope"}}],
                   "entry": "b0"}}})
    print("FAIL bad-target accepted")
    fails += 1
except interp.HSErr as e:
    print(f"ok   bad-target rejected ({e.msg})")

total += 1
try:
    IR.verify_module({"entry": "<main>", "order": ["<main>"], "funcs": {
        "<main>": {"name": "<main>", "dispname": "<main>", "params": [],
                   "globals": [],
                   "blocks": [
                       {"label": "b0", "instrs": [
                           {"op": "bin", "line": 1, "dest": "%1",
                            "binop": "+", "l": "%9", "r": "%9"}],
                        "term": {"term": "ret", "line": 1, "val": None}}],
                   "entry": "b0"}}})
    print("FAIL undef-temp accepted")
    fails += 1
except interp.HSErr as e:
    print(f"ok   undef-temp rejected ({e.msg})")

total += 1
try:
    # %2 is defined only on the b1 path but used in the join: without a
    # phi nothing dominates the use, so this must be rejected
    IR.verify_module({"entry": "<main>", "order": ["<main>"], "funcs": {
        "<main>": {"name": "<main>", "dispname": "<main>", "params": [],
                   "globals": [],
                   "blocks": [
                       {"label": "b0", "instrs": [
                           {"op": "const", "line": 1, "dest": "%1",
                            "val": 1}],
                        "term": {"term": "br", "line": 1, "cond": "%1",
                                 "then": "b1", "els": "b2"}},
                       {"label": "b1", "instrs": [
                           {"op": "const", "line": 2, "dest": "%2",
                            "val": 2}],
                        "term": {"term": "jmp", "line": 2, "to": "b3"}},
                       {"label": "b2", "instrs": [],
                        "term": {"term": "jmp", "line": 3, "to": "b3"}},
                       {"label": "b3", "instrs": [
                           {"op": "bin", "line": 4, "dest": "%3",
                            "binop": "+", "l": "%2", "r": "%1"}],
                        "term": {"term": "ret", "line": 4, "val": "%3"}}],
                   "entry": "b0"}}})
    print("FAIL dominance violation accepted")
    fails += 1
except interp.HSErr as e:
    ok = "does not dominate" in e.msg
    print(("ok  " if ok else "FAIL") +
          f" dominance violation rejected ({e.msg})")
    fails += 0 if ok else 1

# builder rejects out-of-subset constructs with a clear message
for caps, src, want in [("raise-outside", "raise\n", "raise without active"),
                        ("extern-shadow", 'extern:\n  I64 len(Str s)\n',
                         "cannot shadow builtin")]:
    total += 1
    try:
        build_src(src)
        print(f"FAIL unsupported-{caps} accepted")
        fails += 1
    except interp.HSErr as e:
        ok = want in e.msg
        print(("ok  " if ok else "FAIL") +
              f" unsupported-{caps} rejected ({e.msg})")
        fails += 0 if ok else 1

# dump smoke: fib IR uses the canonical text format (keyed func header,
# @line suffixes) with a call and a ret
total += 1
m = build_src("def fib(n):\n  return fib(n)\nprint fib(1)\n")
dump = IR.dump_module(m)
ok = "func fib$L1(n):" in dump and "call" in dump and "ret" in dump \
    and "@2" in dump
print(("ok  " if ok else "FAIL") + " dump smoke")
fails += 0 if ok else 1

# ---------- text round-trip: build -> dump -> parse -> dump ----------
# Every inline CASE above plus a nasty-strings program must survive the
# trip with identical text AND identical execution.

import io
import contextlib


def _exec_capture(m):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            IR.run_module(m)
    except interp.HSErr as e:
        return buf.getvalue(), f"{e.msg}@{e.line}"
    return buf.getvalue(), None


_RT_EXTRA = [
    ("strings",
     'print "a\\"b\\\\c\\nd\\te\\rf\\0g"\nprint "caf\u00e9 \u0e01 \U0001F600"\n'
     'print "trailing @3"\nprint ""\ns = "x @9"\nprint s + "y"\n'),
]

for name, src, *_ in CASES + _RT_EXTRA:
    total += 1
    interp.reset_parse_state()
    m1 = IR.build_module(interp.parse_program(src))
    IR.verify_module(m1)
    t1 = IR.dump_module(m1)
    try:
        m2 = IR.parse_module(t1)
        IR.verify_module(m2)
    except interp.HSErr as e:
        print(f"FAIL roundtrip/{name}: reparse: {e}")
        fails += 1
        continue
    t2 = IR.dump_module(m2)
    if t1 != t2:
        print(f"FAIL roundtrip/{name}: dump differs")
        fails += 1
        continue
    if _exec_capture(m1) != _exec_capture(m2):
        print(f"FAIL roundtrip/{name}: exec differs")
        fails += 1
        continue
    print(f"ok   roundtrip/{name}")

# ---------- hs.py ir CLI: dump contract + --json error contract ----------

total += 1
r = subprocess.run([sys.executable, f"{ROOT}/hs.py", "ir",
                    os.path.join(HERE, "floatlit.hs")],
                   capture_output=True, text=True, timeout=60)
ok = r.returncode == 0 and "func <main>():" in r.stdout
print(("ok  " if ok else "FAIL") + " hs-ir dump")
fails += 0 if ok else 1

total += 1
with tempfile.NamedTemporaryFile("w", suffix=".hs", delete=False) as f:
    f.write("print 1 +\n")
    bad = f.name
try:
    r = subprocess.run([sys.executable, f"{ROOT}/hs.py", "--json", "ir", bad],
                       capture_output=True, text=True, timeout=60)
    import json as _json
    try:
        got = _json.loads(r.stderr)
        ok = (r.returncode == 1 and got["file"] == bad and
              got["line"] == 1 and "message" in got)
    except Exception:
        ok = False
    print(("ok  " if ok else "FAIL") + " hs-ir --json")
    fails += 0 if ok else 1
finally:
    os.unlink(bad)

# ---------- differential over the whole tests/*.hs corpus ----------
# Files outside the IR subset report SKIP (honest, counted separately).

import glob


def _suite_env(name):
    e = dict(os.environ)
    p = os.path.join(HERE, name + ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip()
    return e


nskipped = []
for prog in sorted(glob.glob(os.path.join(HERE, "*.hs"))):
    name = os.path.splitext(os.path.basename(prog))[0]
    if name.startswith("mod_"):
        continue
    if os.path.exists(os.path.join(HERE, name + ".nativeonly")):
        continue
    total += 1
    stdin = None
    sin_path = os.path.join(HERE, name + ".stdin")
    if os.path.exists(sin_path):
        with open(sin_path, "rb") as f:
            stdin = f.read()
    pargs = []
    args_path = os.path.join(HERE, name + ".args")
    if os.path.exists(args_path):
        with open(args_path, encoding="utf-8") as f:
            pargs = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
    env = _suite_env(name)
    text_in = stdin.decode("utf-8") if stdin is not None else None
    a = subprocess.run([sys.executable, f"{ROOT}/interp.py", prog] + pargs,
                       input=text_in, capture_output=True, timeout=120,
                       env=env, text=True)
    b = subprocess.run([sys.executable, f"{ROOT}/ir.py", prog] + pargs,
                       input=text_in, capture_output=True, timeout=120,
                       env=env, text=True)
    if "IR: unsupported" in b.stderr or "IR: builtin" in b.stderr or \
            "IR: not in subset" in b.stderr or \
            "not in x64 subset" in b.stderr:
        nskipped.append(name)
        total -= 1
        continue
    ok = (a.stdout == b.stdout and a.stderr == b.stderr and
          a.returncode == b.returncode)
    print(("ok  " if ok else "FAIL") + f" corpus/{name}")
    if not ok:
        fails += 1
        print(f"  interp: rc={a.returncode} out={a.stdout!r} "
              f"err={a.stderr[-200:]!r}")
        print(f"  ir:     rc={b.returncode} out={b.stdout!r} "
              f"err={b.stderr[-200:]!r}")

print(f"corpus skipped (outside IR subset): {len(nskipped)}")
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
