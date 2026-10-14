#!/usr/bin/env python3
"""selfhost/be (the x64 hosted backend translated to hs: irlib + be.hs +
asm/gcrt/elf) must emit exactly the ELF image irx64.py builds from the same
IR text, for every program in the corpus below."""
import glob
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import ir  # noqa: E402
import irx64  # noqa: E402

HS = [sys.executable, os.path.join(ROOT, "hs.py")]
env = dict(os.environ, HSROOT=ROOT, HSPATH=os.path.join(ROOT, "selfhost") + ":" + os.path.join(ROOT, "selfhost", "be"))
progs = sorted(glob.glob(os.path.join(ROOT, "tests", "*.hs")))
only = sys.argv[1:]
total = bad = skipped = 0
with tempfile.TemporaryDirectory() as d:
    for f in progs:
        if only and os.path.basename(f) not in only:
            continue
        r = subprocess.run(HS + ["ir", f], capture_output=True, text=True)
        if r.returncode:
            skipped += 1
            continue
        try:
            want = irx64.GenIR(ir.parse_module(r.stdout), os.path.dirname(f)).build_ir_image()
        except Exception:
            skipped += 1
            continue
        p = os.path.join(d, "out.elf")
        env["HSROOT"] = ROOT
        g = subprocess.run(HS + ["run", os.path.join(ROOT,"selfhost/be/compile.hs"),
            "--backend", "interp", f, p], capture_output=True,text=True,env=env,timeout=120)
        total += 1
        got = open(p,"rb").read() if os.path.exists(p) else b""
        if got != want:
            bad += 1
            print("FAIL compile",os.path.basename(f),len(got),len(want),g.stderr[-180:],flush=True)
        if os.path.exists(p):
            os.unlink(p)
print(f"{total-bad}/{total} passed ({skipped} rejected by Python emitter)")
sys.exit(bool(bad) or not total)
