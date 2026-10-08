#!/usr/bin/env python3
"""holyshit IR->x64 differential tests: python3 tests/test_irx64.py

Builds each tests/<name>.hs twice — once through x64gen (AST path,
reference) and once through irx64 (IR path) — and requires the two
static ELFs to agree byte-for-byte on stdout, stderr and exit code.

Files outside the irx64 subset report SKIP (honest, counted separately);
files the AST backend itself rejects are skipped too (no reference).
"""
import glob
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from x64gen import build_x64
from irx64 import build_irx64

_CHILD_ENV = dict(os.environ)

SKIP_MARKS = ("not in irx64 subset yet", "IR: unsupported", "IR: builtin",
              "not in x64 subset", "is not a value")


def _test_env(name):
    e = dict(_CHILD_ENV)
    p = os.path.join(HERE, name + ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip()
    return e


def _clean_fs():
    import shutil
    shutil.rmtree("/tmp/opencode/hs_fs_test", ignore_errors=True)
    try:
        os.remove("/tmp/opencode/hs_x64file_a.txt")
    except OSError:
        pass


def _build(fn, prog, out):
    err = io.StringIO()
    sout = io.StringIO()
    with redirect_stderr(err):
        with redirect_stdout(sout):
            try:
                rc = fn(prog, out)
            except Exception as e:  # noqa: BLE001 - harness reports it
                print(str(e), file=err)
                rc = 1
    return rc, err.getvalue()


def _run(path, pargs, sin, env):
    try:
        return subprocess.run([path] + pargs, input=sin,
                              capture_output=True, timeout=60,
                              env=env), None
    except subprocess.TimeoutExpired:
        return None, "timeout"


fails = 0
total = 0
nskipped = []
with tempfile.TemporaryDirectory() as d:
    for prog in sorted(glob.glob(os.path.join(HERE, "*.hs"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue
        if os.path.exists(os.path.join(HERE, name + ".nativeonly")):
            continue
        total += 1
        tenv = _test_env(name)
        old_env = dict(os.environ)
        os.environ.update(tenv)  # HSPATH affects build-time imports
        try:
            ref = os.path.join(d, name + ".ref")
            rrc, rerr = _build(build_x64, prog, ref)
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        if rrc != 0:
            nskipped.append(name + " (ast-refuses)")
            total -= 1
            continue
        os.environ.update(tenv)
        try:
            out = os.path.join(d, name + ".irx")
            irc, ierr = _build(build_irx64, prog, out)
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        if irc != 0:
            if any(m in ierr for m in SKIP_MARKS):
                nskipped.append(name)
                total -= 1
                continue
            print(f"FAIL {name}: irx64 build failed: {ierr.strip()[-300:]}")
            fails += 1
            continue
        sin = None
        sin_path = os.path.join(HERE, name + ".stdin")
        if os.path.exists(sin_path):
            with open(sin_path, "rb") as f:
                sin = f.read()
        pargs = []
        args_path = os.path.join(HERE, name + ".args")
        if os.path.exists(args_path):
            with open(args_path, encoding="utf-8") as f:
                pargs = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
        _clean_fs()
        ra, tea = _run(ref, pargs, sin, tenv)
        _clean_fs()
        rb, teb = _run(out, pargs, sin, tenv)
        if tea or teb:
            print(f"FAIL {name}: timeout (ref={tea} irx={teb})")
            fails += 1
            continue
        ok = (ra.stdout == rb.stdout and ra.stderr == rb.stderr and
              ra.returncode == rb.returncode)
        print(("ok   " if ok else "FAIL") + f" {name}")
        if not ok:
            fails += 1
            print(f"  ast: rc={ra.returncode} out={ra.stdout!r} "
                  f"err={ra.stderr[-200:]!r}")
            print(f"  irx: rc={rb.returncode} out={rb.stdout!r} "
                  f"err={rb.stderr[-200:]!r}")

print(f"skipped (no reference or outside irx64 subset): {len(nskipped)}")
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
