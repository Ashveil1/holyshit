#!/usr/bin/env python3
"""holyshit formatter tests: python3 tests/test_fmt.py
Each tests/fmt/<name>.hs must format to tests/fmt/<name>.expected,
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
for prog in sorted(glob.glob(os.path.join(HERE, "fmt", "*.hs"))):
    name = os.path.splitext(os.path.basename(prog))[0]
    total += 1
    with open(prog, encoding="utf-8") as f:
        src = f.read()
    try:
        interp.reset_parse_state()
        once = _fmt.fmt_program(interp.parse_program(src))
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
        twice = _fmt.fmt_program(interp.parse_program(once))
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
    with open(os.path.join(HERE, "fmt", name + ".formatted.hs"), "w", encoding="utf-8") as f:
        f.write(once)
    r2 = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                         os.path.join(HERE, "fmt", name + ".formatted.hs")],
                        capture_output=True, timeout=60)
    os.remove(os.path.join(HERE, "fmt", name + ".formatted.hs"))
    if (r1.returncode, r1.stdout, r1.stderr) != (r2.returncode, r2.stdout, r2.stderr):
        print(f"FAIL {name}: exec differs after fmt")
        fails += 1
        continue
    print(f"ok   {name}")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
