#!/usr/bin/env python3
"""Self-hosted lexer (selfhost/lex.hs) must match interp's lexer on every
.hs file in the repo, run both by interp and by the x64 build (no gcc)."""
import glob
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from x64gen import build_x64  # noqa: E402

files = []
for d in ("tests", "tests/x64", "examples", "std", "kernel", "selfhost", "bench"):
    files += sorted(glob.glob(os.path.join(ROOT, d, "*.hs")))
total = fails = 0


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return r.stdout, r.returncode


with tempfile.TemporaryDirectory() as d:
    exe = os.path.join(d, "lexhs")
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(os.path.join(ROOT, "selfhost", "lex.hs"), exe)
    if rc != 0:
        print("FAIL build selfhost/lex.hs with xbuild")
        sys.exit(1)
    for f in files:
        want, wrc = run([sys.executable, os.path.join(ROOT, "selfhost", "dump_lex.py"), f])
        rel = os.path.relpath(f, ROOT)
        for how, cmd in (("interp", [sys.executable, os.path.join(ROOT, "interp.py"),
                                     os.path.join(ROOT, "selfhost", "lex.hs"), f]),
                         ("x64", [exe, f])):
            total += 1
            got, grc = run(cmd)
            if got.rstrip("\n") == want.rstrip("\n") and (grc == 0) == (wrc == 0):
                print(f"ok   lex[{how}] {rel}")
            else:
                fails += 1
                print(f"FAIL lex[{how}] {rel}")
                gl, wl = got.split("\n"), want.split("\n")
                for i, (g, w) in enumerate(zip(gl, wl)):
                    if g != w:
                        print(f"  line {i + 1}: got {g!r} want {w!r}")
                        break
                else:
                    print(f"  length differs: got {len(gl)} want {len(wl)}")
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
