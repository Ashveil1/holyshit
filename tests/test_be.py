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
total = bad = skipped = deferred = 0
with tempfile.TemporaryDirectory() as d:
    for f in progs:
        rel = os.path.relpath(f, ROOT)
        if only and rel not in only and os.path.basename(f) not in only:
            continue
        src = open(f).read()
        if any(l.startswith(("import ", "from ")) for l in src.splitlines()):
            skipped += 1  # module programs need the AST->IR builder (S5)
            continue
        r = subprocess.run(HS + ["ir", f], capture_output=True, text=True)
        if r.returncode != 0:
            skipped += 1
            continue
        try:
            m = ir.parse_module(r.stdout)
            want = irx64.GenIR(m, os.path.dirname(f)).build_ir_image().hex()
        except Exception:
            skipped += 1  # compile-time error programs, modules, ffi: out of scope here
            continue
        p = os.path.join(d, "m.ir")
        open(p, "w").write(r.stdout)
        g = subprocess.run(HS + ["run", os.path.join(ROOT, "selfhost", "be", "irx64_run.hs"),
                                 "--backend", "interp", p], capture_output=True, text=True, env=env)
        if "unknown variable 'interp'" in g.stdout + g.stderr:
            deferred += 1  # json/fs helper modules are built from source: needs S5 (AST->IR)
            continue
        total += 1
        if g.stdout.strip() != want:
            bad += 1
            got = g.stdout.strip()
            n = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), None)
            print("FAIL be", rel, "first diff at", n, len(got), len(want), g.stderr[-160:])
print(f"{'ok  ' if not bad else 'FAIL'} be == irx64.py on {total - bad}/{total} programs ({skipped} skipped, {deferred} deferred to S5)")
print(f"{total - bad}/{total} passed")
sys.exit(1 if bad or total == 0 else 0)
