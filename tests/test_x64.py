#!/usr/bin/env python3
"""holyshit x86-64 backend tests: python3 tests/test_x64.py
Builds each tests/x64/<name>.hs to a static ELF (no gcc) and checks output.
Same .expected/.fail convention as test.py.
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from x64gen import build_x64

_CHILD_ENV = dict(os.environ)


def _test_env(name):
    # per-test env overlay: tests/x64/<name>.env has KEY=VAL lines
    # (# comments ok). Same convention as test.py (HSPATH affects
    # build-time imports).
    e = dict(_CHILD_ENV)
    p = os.path.join(HERE, "x64", name + ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip()
    return e

fails = 0
total = 0
# file.hs uses a fixed scratch file: start clean for determinism.
try:
    import os as _os
    _os.remove("/tmp/opencode/hs_x64file_a.txt")
except OSError:
    pass
with tempfile.TemporaryDirectory() as d:
    for prog in sorted(glob.glob(os.path.join(HERE, "x64", "*.hs"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue  # import helpers, built via their importers
        total += 1
        out = os.path.join(d, name)
        import io
        from contextlib import redirect_stderr, redirect_stdout
        err = io.StringIO()
        sout = io.StringIO()
        tenv = _test_env(name)
        old_env = dict(os.environ)
        os.environ.update(tenv)  # HSPATH affects build-time imports
        try:
            with redirect_stderr(err):
                with redirect_stdout(sout):
                    try:
                        rc = build_x64(prog, out)
                    except Exception as e:
                        print(str(e), file=err)
                        rc = 1
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        build_noise = sout.getvalue()
        fail_path = os.path.join(HERE, "x64", name + ".fail")
        if rc != 0:
            if os.path.exists(fail_path):
                with open(fail_path, encoding="utf-8") as f:
                    want_err = f.read().strip()
                if want_err in err.getvalue():
                    print(f"ok   {name} (compile error as expected)")
                    continue
            print(f"FAIL {name}: build failed: {err.getvalue().strip()}")
            fails += 1
            continue
        try:
            sin_path = os.path.join(HERE, "x64", name + ".stdin")
            sin = None
            if os.path.exists(sin_path):
                with open(sin_path, "rb") as f:
                    sin = f.read()
            pargs = []
            args_path = os.path.join(HERE, "x64", name + ".args")
            if os.path.exists(args_path):
                with open(args_path, encoding="utf-8") as f:
                    pargs = [ln.rstrip("\n") for ln in f
                             if ln.strip() != ""]
            r = subprocess.run([out] + pargs, input=sin, capture_output=True,
                               timeout=60, env=tenv)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: timeout")
            fails += 1
            continue
        if os.path.exists(fail_path):
            with open(fail_path, encoding="utf-8") as f:
                want_err = f.read().strip()
            if r.returncode == 0:
                print(f"FAIL {name}: expected error, exited 0")
                fails += 1
            elif want_err in r.stderr.decode():
                print(f"ok   {name}")
            else:
                print(f"FAIL {name}: stderr {r.stderr.decode()!r} lacks {want_err!r}")
                fails += 1
            continue
        with open(os.path.join(HERE, "x64", name + ".expected"), encoding="utf-8") as f:
            want = f.read()
        got = r.stdout.decode()
        if r.returncode != 0:
            print(f"FAIL {name}: exit {r.returncode}, stderr: {r.stderr.decode().strip()}")
            fails += 1
        elif got != want:
            print(f"FAIL {name}:\n--- want ---\n{want}--- got ---\n{got}---")
            fails += 1
        else:
            print(f"ok   {name}")

# ---------- hs.py CLI dispatch ----------
# Every `if argv[1] == "cmd"` in main() must exist exactly once: a deleted
# branch header turns the command into a fall-through into the *previous*
# backend (that is how `hs.py xkernel` silently became `hs.py build`).
import ast as _ast

total += 3
_src = open(os.path.join(ROOT, "hs.py"), encoding="utf-8").read()
_cmds = []
for _n in _ast.walk(_ast.parse(_src)):
    if isinstance(_n, _ast.Compare) and len(_n.ops) == 1 and \
            isinstance(_n.ops[0], _ast.Eq):
        _l, _r = _n.left, _n.comparators[0]
        if isinstance(_r, _ast.Constant) and isinstance(_r.value, str):
            _fn = _l
            if isinstance(_fn, _ast.Subscript) and \
                    isinstance(_fn.slice, _ast.Constant) and \
                    _fn.slice.value == 1:
                _cmds.append(_r.value)
_dupes = sorted({c for c in _cmds if _cmds.count(c) > 1})
if _dupes:
    print(f"FAIL hs.py dispatch: duplicated branch(es) {_dupes}")
    fails += 1
else:
    print("ok   hs.py dispatch: no duplicate subcommand branch")

# `run` is deliberately the fall-through default (build to a temp dir, then
# exec), so it has no branch of its own; every other subcommand must.
_want = {"build", "check", "fmt", "xbuild", "xrun", "xkernel", "ir", "lsp"}
_missing = sorted(_want - set(_cmds))
if _missing:
    print(f"FAIL hs.py dispatch: missing branch(es) {_missing}")
    fails += 1
else:
    print("ok   hs.py dispatch: every subcommand has a branch")

with tempfile.TemporaryDirectory() as _d:
    _src2 = os.path.join(_d, "cli.hs")
    with open(_src2, "w", encoding="utf-8") as _f:
        _f.write("unsafe:\n  I64 x = 6\n  print x * 7\n")
    _elf = os.path.join(_d, "cli.elf")
    _r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"),
                         "xkernel", _src2, "-o", _elf],
                        capture_output=True, text=True, timeout=300,
                        env=dict(_CHILD_ENV, HSPATH=ROOT))
    if _r.returncode != 0 or not os.path.exists(_elf) or \
            _r.stdout.find("no gcc/as/ld") < 0:
        print(f"FAIL hs.py xkernel CLI: rc={_r.returncode} "
              f"out={_r.stdout[-200:]!r} err={_r.stderr[-200:]!r}")
        fails += 1
    else:
        print("ok   hs.py xkernel CLI builds a freestanding ELF")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
