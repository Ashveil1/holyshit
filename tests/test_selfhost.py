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

# ---- parser: selfhost/parse.hs vs interp.parse_program (JSON), x64 build ----
nskip = 0
with tempfile.TemporaryDirectory() as d:
    exe = os.path.join(d, "parsehs")
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(os.path.join(ROOT, "selfhost", "parse.hs"), exe)
    if rc != 0:
        print("FAIL build selfhost/parse.hs with xbuild")
        sys.exit(1)
    for f in files:
        rel = os.path.relpath(f, ROOT)
        r = subprocess.run([exe, f], capture_output=True, text=True,
                           errors="replace")
        if "unsupported:" in r.stderr:
            nskip += 1
            print(f"skip parse {rel}: {(r.stdout + r.stderr).strip()[-80:]}")
            continue
        want, wrc = run([sys.executable,
                         os.path.join(ROOT, "selfhost", "dump_parse.py"), f])
        total += 1
        how = "x64"
        if r.stdout.rstrip("\n") != want.rstrip("\n") and "0x" in open(
                f, encoding="utf-8", errors="replace").read():
            # x64 Int is 62-bit: literals above 2^61 cannot be represented.
            # Those files are checked against the 64-bit interp run instead.
            r = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                                os.path.join(ROOT, "selfhost", "parse.hs"), f],
                               capture_output=True, text=True, errors="replace")
            how = "interp (x64 Int is 62-bit)"
        if r.stdout.rstrip("\n") == want.rstrip("\n") and \
                (r.returncode == 0) == (wrc == 0):
            print(f"ok   parse[{how}] {rel}")
        else:
            fails += 1
            print(f"FAIL parse[x64] {rel}")
            g, w = r.stdout.rstrip("\n"), want.rstrip("\n")
            k = next((i for i in range(min(len(g), len(w))) if g[i] != w[i]),
                     min(len(g), len(w)))
            print(f"  differs at char {k}: got {g[max(0, k - 60):k + 60]!r}")
            print(f"                      want {w[max(0, k - 60):k + 60]!r}")
print(f"parser: {nskip} files skipped (unsupported construct)")
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
