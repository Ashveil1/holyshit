#!/usr/bin/env python3
"""hs run JIT integration: explicit backend, auto path, fallback semantics.

Builds the driver once into a private HS_RUN_CACHE_DIR, then checks:
explicit --backend jit runs; auto uses the driver (warm); a compile error
falls through the auto chain with the interpreter's message and rc 1;
HS_JIT=off opts out of the driver."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HS = [sys.executable, str(ROOT / "hs.py")]


def run(args, env, cwd):
    return subprocess.run(HS + args, env=env, capture_output=True,
                          text=True, timeout=600, cwd=cwd)


fails = 0
with tempfile.TemporaryDirectory(prefix="hs jit auto ") as d:
    d = Path(d)
    env = dict(os.environ, HS_RUN_CACHE_DIR=str(d / "cache"))
    env.pop("HS_JIT", None)
    prog = d / "ok.holy"
    prog.write_text('print "jit-auto-ok"\nprint 6 * 7\n')

    r = run(["run", str(prog), "--backend", "jit"], env, d)
    if r.returncode != 0 or r.stdout != "jit-auto-ok\n42\n":
        fails += 1
        print("FAIL explicit jit", r.returncode, repr(r.stdout), r.stderr[-300:])
    if "building the JIT driver" not in r.stderr:
        fails += 1
        print("FAIL expected one-time build notice", r.stderr[-300:])

    r = run(["run", str(prog)], env, d)
    if r.returncode != 0 or r.stdout != "jit-auto-ok\n42\n":
        fails += 1
        print("FAIL auto jit", r.returncode, repr(r.stdout), r.stderr[-300:])
    if not (d / "ok.hsc").is_file():
        fails += 1
        print("FAIL auto did not leave a .hsc code cache")

    bad = d / "bad.holy"
    bad.write_text("print x +\n")
    r = run(["run", str(bad)], env, d)
    if r.returncode != 1 or "expression expected" not in r.stderr:
        fails += 1
        print("FAIL auto fallback error", r.returncode, repr(r.stdout),
              r.stderr[-300:])

    env_off = dict(env, HS_JIT="off")
    r = run(["run", str(prog)], env_off, d)
    if r.returncode != 0 or r.stdout != "jit-auto-ok\n42\n":
        fails += 1
        print("FAIL HS_JIT=off", r.returncode, repr(r.stdout), r.stderr[-300:])

total = 5
print(f"{total - fails}/{total} jit run auto")
sys.exit(1 if fails else 0)
