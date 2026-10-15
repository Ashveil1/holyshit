#!/usr/bin/env python3
"""holyshit formatter tests: python3 tests/test_fmt.py
Each tests/fmt/<name>.holy must format to tests/fmt/<name>.expected,
be idempotent, and execute identically (interp) before/after.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import fmt as _fmt
import interp

fails = 0
total = 0
for prog in sorted(glob.glob(os.path.join(HERE, "fmt", "*.holy"))):
    name = os.path.splitext(os.path.basename(prog))[0]
    total += 1
    with open(prog, encoding="utf-8") as f:
        src = f.read()
    try:
        interp.reset_parse_state()
        once = _fmt.fmt_program(interp.parse_program(src, raw=True))
    except interp.HSErr as e:
        print(f"FAIL {name}: fmt crashed: {e}")
        fails += 1
        continue
    with open(os.path.join(HERE, "fmt", name + ".expected"), encoding="utf-8") as f:
        want = f.read()
    if once != want:
        print(f"FAIL {name}: canonical mismatch")
        fails += 1
        continue
    try:
        interp.reset_parse_state()
        twice = _fmt.fmt_program(interp.parse_program(once, raw=True))
    except interp.HSErr as e:
        print(f"FAIL {name}: refmt crashed: {e}")
        fails += 1
        continue
    if twice != once:
        print(f"FAIL {name}: not idempotent")
        fails += 1
        continue
    r1 = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"), prog],
                        capture_output=True, timeout=60)
    with open(os.path.join(HERE, "fmt", name + ".formatted.holy"), "w", encoding="utf-8") as f:
        f.write(once)
    r2 = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                         os.path.join(HERE, "fmt", name + ".formatted.holy")],
                        capture_output=True, timeout=60)
    os.remove(os.path.join(HERE, "fmt", name + ".formatted.holy"))
    if (r1.returncode, r1.stdout, r1.stderr) != (r2.returncode, r2.stdout, r2.stderr):
        print(f"FAIL {name}: exec differs after fmt")
        fails += 1
        continue
    print(f"ok   {name}")

# every .holy in the repo must already be canonical (comments and blank lines
# do not count — the printer cannot reproduce them)
total += 1
bad = []
# tests/fmt/*.holy are deliberately unformatted fixtures
for sub in ("examples", "std", "tests", "tests/x64", "kernel"):
    d = os.path.join(ROOT, sub)
    if not os.path.isdir(d):
        continue
    for path in sorted(glob.glob(os.path.join(d, "*.holy"))):
        if path.endswith(".formatted.holy"):
            continue
        with open(path, encoding="utf-8") as f:
            src = f.read()
        try:
            interp.reset_parse_state()
            out = _fmt.fmt_program(interp.parse_program(src, raw=True))
        except interp.HSErr:
            continue  # syntax-error fixtures are exempt
        if not _fmt.is_canonical(src, out):
            bad.append(os.path.relpath(path, ROOT))
if bad:
    print(f"FAIL repo canonical form: {', '.join(bad)}")
    fails += 1
else:
    print("ok   repo canonical form")

# --check must agree with is_canonical, including odd argument order
total += 1
import tempfile
with tempfile.TemporaryDirectory() as d:
    good = os.path.join(d, "good.holy")
    with open(good, "w", encoding="utf-8") as f:
        f.write('# comment kept\n\ndef f(a, b):\n  return a + b\n')
    r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "fmt",
                        good, "--check"], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL fmt --check false positive: {r.stderr.strip()}")
        fails += 1
    else:
        with open(good, "w", encoding="utf-8") as f:
            f.write("def  f( a,b ):\n    return a  +  b\n")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "fmt",
                            "--check", good], capture_output=True, text=True)
        if r.returncode != 0:
            print("ok   fmt --check flags bad spacing")
        else:
            print("FAIL fmt --check missed bad spacing")
            fails += 1

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
