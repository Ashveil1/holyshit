#!/usr/bin/env python3
"""Every example in examples/ must actually run: python3 tests/test_examples.py

Each `examples/<name>.holy` has an `examples/<name>.expected` (stdout). This
suite runs the interpreter (and the gcc backend for examples that do not need
extern/unsafe), so a broken example fails CI instead of rotting silently.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EX = os.path.join(ROOT, "examples")

fails = 0
total = 0


def check(name, cond, detail=""):
    global fails, total
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        fails += 1


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kw)


names = sorted(f[:-5] for f in os.listdir(EX) if f.endswith(".holy"))
assert names, "no canonical .holy examples found"
env = dict(os.environ)
env["HSPATH"] = ROOT + (":" + env["HSPATH"] if env.get("HSPATH") else "")

for name in names:
    src = os.path.join(EX, name + ".holy")
    exp_path = os.path.join(EX, name + ".expected")
    if not os.path.exists(exp_path):
        check(f"{name}: has .expected", False, "missing expected output")
        continue
    with open(exp_path, encoding="utf-8") as f:
        want = f.read()
    r = run([sys.executable, os.path.join(ROOT, "interp.py"),
             name + ".holy"], cwd=EX, env=env)
    check(f"{name}: interp", r.returncode == 0 and r.stdout == want,
          f"rc={r.returncode} err={r.stderr.strip()[:200]}")

print()
# legacy examples are kept as-is; only the tour is checked against native
for name in names:
    if not name[:2].isdigit():
        continue
    src = os.path.join(EX, name + ".holy")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    if "extern" in text or "unsafe:" in text or "std." in text:
        continue  # hosted-only features: native parity already covered elsewhere
    with open(os.path.join(EX, name + ".expected"), encoding="utf-8") as f:
        want = f.read()
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, name)
        b = run([sys.executable, os.path.join(ROOT, "hs.py"), "build",
                 name + ".holy", "-o", out], cwd=EX, env=env)
        if b.returncode != 0:
            check(f"{name}: native build", False, b.stderr.strip()[:200])
            continue
        r2 = run([out], cwd=EX)
    check(f"{name}: native parity", r2.stdout == want,
          f"differs from .expected (rc={r2.returncode})")

print(f"\n{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
