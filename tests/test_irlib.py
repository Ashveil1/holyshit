#!/usr/bin/env python3
"""selfhost/irlib.hs (IR text loader written in hs) must produce exactly the
module ir.parse_module builds, for the IR of every repo program that lowers."""
import glob
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import ir  # noqa: E402

HS = [sys.executable, os.path.join(ROOT, "hs.py")]
files = sorted(glob.glob(os.path.join(ROOT, "tests", "*.hs")) +
               glob.glob(os.path.join(ROOT, "examples", "*.hs")) +
               glob.glob(os.path.join(ROOT, "selfhost", "*.hs")))
total = bad = skipped = 0
with tempfile.TemporaryDirectory() as d:
    for f in files:
        r = subprocess.run(HS + ["ir", f], capture_output=True, text=True)
        if r.returncode != 0:
            skipped += 1
            continue
        p = os.path.join(d, "m.ir")
        open(p, "w").write(r.stdout)
        try:
            want = json.dumps(ir.parse_module(r.stdout), allow_nan=False)
        except Exception:
            skipped += 1  # IR text that ir.py itself cannot read back
            continue
        g = subprocess.run(HS + ["run", os.path.join(ROOT, "selfhost", "ir_dump.hs"),
                                 "--backend", "interp", p], capture_output=True, text=True)
        total += 1
        if g.stdout.strip() != want:
            bad += 1
            print("FAIL irlib", os.path.relpath(f, ROOT), g.stderr[-200:])
print(f"{'ok  ' if not bad else 'FAIL'} irlib.hs == ir.parse_module on {total} programs ({skipped} not lowerable)")
print(f"{total - bad}/{total} passed")
sys.exit(1 if bad or total == 0 else 0)
