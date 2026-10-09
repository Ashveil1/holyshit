#!/usr/bin/env python3
"""holyshit IR->x64 differential tests: python3 tests/test_irx64.py

Builds each tests/<name>.hs twice — once through the legacy AST-direct
backend (build_x64_ast, reference) and once through irx64 (IR path) —
and requires the two static ELFs to agree byte-for-byte on stdout,
stderr and exit code. (Since the Task 4 switchover, build_x64 itself
routes through IR; this suite keeps the old path honest.)

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
from x64gen import build_x64_ast as build_x64
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


def _run_interp(prog, pargs, sin, env):
    try:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                            prog] + pargs, input=sin, capture_output=True,
                           timeout=60, env=env)
        out = r.stdout.decode() if isinstance(r.stdout, bytes) else r.stdout
        err = r.stderr.decode() if isinstance(r.stderr, bytes) else r.stderr
        return (out, err, r.returncode), None
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
        # pass on AST-path agreement; agreement with interp alone also
        # passes but is flagged (!!) for triage: the IR path fixed an
        # x64gen-today divergence (ufunc segfault, unsafe "unbound").
        ok_ast = (ra.stdout == rb.stdout and ra.stderr == rb.stderr and
                  ra.returncode == rb.returncode)
        if ok_ast:
            print(f"ok   {name}")
            continue
        _clean_fs()
        ri, tei = _run_interp(prog, pargs, sin, tenv)
        if tei:
            print(f"FAIL {name}: interp timeout")
            fails += 1
            continue
        if (ri[0], ri[1], ri[2]) == (rb.stdout.decode(), rb.stderr.decode(),
                                     rb.returncode):
            print(f"ok   {name} (!! matches interp, not x64gen)")
            continue
        print(f"FAIL {name}")
        fails += 1
        print(f"  ast: rc={ra.returncode} out={ra.stdout!r} "
              f"err={ra.stderr[-200:]!r}")
        print(f"  irx: rc={rb.returncode} out={rb.stdout!r} "
              f"err={rb.stderr[-200:]!r}")
        print(f"  int: rc={ri[2]} out={ri[0]!r} err={ri[1][-200:]!r}")

print(f"skipped (no reference or outside irx64 subset): {len(nskipped)}")
grand_total, grand_fails = total, fails

# ---------- inline file-op cases (t_fs needs json_str, which needs the
# module machinery, so the file helpers get direct differential tests) ----------

FILE_CASES = [
    ("fs_basic",
     'mkdir(P)\nwrite_text(P + "/a.txt", "hello")\n'
     'append_text(P + "/a.txt", " world")\nprint read_text(P + "/a.txt")\n'
     'print exists(P + "/a.txt")\nprint exists(P + "/no")\nprint ls(P)\n'),
    ("fs_err",
     'print read_text(5)\n'),
]

ffails = ftotal = 0
with tempfile.TemporaryDirectory() as d:
    for name, template in FILE_CASES:
        ftotal += 1
        progs = []
        for tag, builder in (("ref", build_x64), ("irx", build_irx64)):
            work = os.path.join(d, f"{name}_{tag}")
            os.mkdir(work)
            src = template.replace("P", '"' + work + '"')
            prog = os.path.join(d, f"{name}_{tag}.hs")
            with open(prog, "w") as f:
                f.write(src)
            old_env = dict(os.environ)
            try:
                rc, err = _build(builder, prog, os.path.join(d, tag))
            finally:
                os.environ.clear()
                os.environ.update(old_env)
            progs.append((rc, err, os.path.join(d, tag), work))
        (rrc, rerr, rp, rwork), (irc, ierr, ip, iwork) = progs
        if rrc != 0 or irc != 0:
            ok = (rrc == irc and rerr == ierr)
            print(("ok   " if ok else "FAIL") + f" {name} (build)")
            ffails += 0 if ok else 1
            continue
        ra = subprocess.run([rp], capture_output=True, timeout=60)
        rb = subprocess.run([ip], capture_output=True, timeout=60)
        # separate scratch dirs per side: normalize each to P
        na = (ra.stdout.replace(rwork.encode(), b"P"),
              ra.stderr.replace(rwork.encode(), b"P"))
        nb = (rb.stdout.replace(iwork.encode(), b"P"),
              rb.stderr.replace(iwork.encode(), b"P"))
        ok = ra.returncode == rb.returncode and na == nb
        print(("ok   " if ok else "FAIL") + f" {name}")
        if not ok:
            ffails += 1
            print(f"  ast: rc={ra.returncode} out={ra.stdout!r} "
                  f"err={ra.stderr[-200:]!r}")
            print(f"  irx: rc={rb.returncode} out={rb.stdout!r} "
                  f"err={rb.stderr[-200:]!r}")

print(f"{grand_total + ftotal - grand_fails - ffails}/"
      f"{grand_total + ftotal} passed")
sys.exit(1 if grand_fails + ffails else 0)
