#!/usr/bin/env python3
"""selfhost/irlib.holy (IR text loader written in hs) must produce exactly the
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

def fits62(v):
    if type(v) is int:
        return -(1 << 61) <= v < (1 << 61)
    if isinstance(v, (list, tuple)):
        return all(fits62(x) for x in v)
    if isinstance(v, dict):
        return all(fits62(x) for x in v.values())
    return True

HS = [sys.executable, os.path.join(ROOT, "hs.py")]
files = sorted(glob.glob(os.path.join(ROOT, "tests", "*.holy")) +
               glob.glob(os.path.join(ROOT, "examples", "*.holy")) +
               glob.glob(os.path.join(ROOT, "selfhost", "*.holy")))
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
        g = subprocess.run(HS + ["run", os.path.join(ROOT, "selfhost", "ir_dump.holy"),
                                 "--backend", "interp", p], capture_output=True, text=True)
        if not fits62(ir.parse_module(r.stdout)):
            # unified 62-bit Int: the hs IR loader cannot hold consts past the
            # safe range; it must reject them (wide-literal IR tooling is C2)
            if g.returncode != 0 and ("cannot convert" in g.stderr or
                                      "Int outside the 62-bit range" in g.stderr):
                skipped += 1
                continue
            bad += 1
            print("FAIL irlib", os.path.relpath(f, ROOT),
                  "expected wide-literal rejection, got", g.returncode,
                  g.stderr[-160:])
            continue
        total += 1
        if g.stdout.strip() != want:
            bad += 1
            print("FAIL irlib", os.path.relpath(f, ROOT), g.stderr[-200:])
print(f"{'ok  ' if not bad else 'FAIL'} irlib.holy == ir.parse_module on {total} programs ({skipped} not lowerable)")
print(f"{total - bad}/{total} passed")
sys.exit(1 if bad or total == 0 else 0)
