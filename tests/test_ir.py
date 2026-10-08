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
                   "blocks": [
                       {"label": "b0", "instrs": [
                           {"op": "bin", "line": 1, "dest": "%1",
                            "op2": "+", "l": "%9", "r": "%9"}],
                        "term": {"term": "ret", "line": 1, "val": None}}],
                   "entry": "b0"}}})
    print("FAIL undef-temp accepted")
    fails += 1
except interp.HSErr as e:
    print(f"ok   undef-temp rejected ({e.msg})")

# builder rejects out-of-subset constructs with a clear message
for caps, src in [("for", "for i in range(3):\n  print i\n"),
                  ("import", "import std.str\n"),
                  ("try", "try:\n  pass\nexcept:\n  pass\n"),
                  ("list", "print [1, 2]\n")]:
    total += 1
    try:
        build_src(src)
        print(f"FAIL unsupported-{caps} accepted")
        fails += 1
    except interp.HSErr as e:
        ok = "IR: unsupported" in e.msg
        print(("ok  " if ok else "FAIL") +
              f" unsupported-{caps} rejected ({e.msg})")
        fails += 0 if ok else 1

# dump smoke: fib IR contains a call and a ret
total += 1
m = build_src("def fib(n):\n  return fib(n)\nprint fib(1)\n")
dump = IR.dump_module(m)
ok = "func fib(n):" in dump and "call" in dump and "ret" in dump
print(("ok  " if ok else "FAIL") + " dump smoke")
fails += 0 if ok else 1

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
