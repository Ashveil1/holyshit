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

import io
from contextlib import redirect_stderr, redirect_stdout

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

# ---------- the whole tests/*.hs corpus through the IR path ----------
# tests/x64/ only covers the x64-specific features; this pass builds every
# program the interpreter suite runs and diffs its real output against
# interp.py, so a regression anywhere in the language shows up here and not
# months later. Programs outside the hosted x64 subset report SKIP (honest,
# counted separately) — the same convention test_ir.py uses.
_CORPUS_SKIP = ("not in x64 subset", "IR: unsupported", "IR: builtin",
                "IR: not in subset", "IR: '", "x64 subset",
                "not supported by xbuild", "needs a C compiler")
# Programs the interpreter suite runs against a fixture it starts itself
# (t_sock needs the throwaway HTTP server in test.py); standalone they
# cannot run, so this pass leaves them alone.
_CORPUS_FIXTURE = {"t_sock"}
# Programs that differ from interp on x64 for a documented reason. They are
# counted and printed, never silently skipped: the x64 backend's own choices
# (62-bit Int, type-blind unsafe) are part of its contract, see
# docs/x64-subset.md.
_CORPUS_KNOWN = {
    "err_umix": "unsafe is type-blind on x64 (no I64/U64 mix check)",
    "t_bits": "62-bit Int: `1 << 61` is the sign bit on x64",
}


def _corpus_env(name):
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


def _clean_corpus():
    for junk in ("hs_fs_test", "hs_json_test", "lsx", "t1", "t2", "t3"):
        try:
            import shutil as _sh
            _sh.rmtree("/tmp/opencode/" + junk)
        except OSError:
            pass


nskip = 0
nknown = 0
with tempfile.TemporaryDirectory() as _d:
    _out = os.path.join(_d, "corpus")
    for prog in sorted(glob.glob(os.path.join(HERE, "*.hs"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue
        if os.path.exists(os.path.join(HERE, name + ".nativeonly")):
            continue
        if name in _CORPUS_FIXTURE:
            continue
        total += 1
        _clean_corpus()
        _env = _corpus_env(name)
        _err, _sout = io.StringIO(), io.StringIO()
        _old = dict(os.environ)
        os.environ.update(_env)
        try:
            with redirect_stderr(_err):
                with redirect_stdout(_sout):
                    try:
                        rc = build_x64(prog, _out)
                    except Exception as e:
                        print(str(e), file=_err)
                        rc = 1
        finally:
            os.environ.clear()
            os.environ.update(_old)
        if rc != 0:
            if any(m in _err.getvalue() for m in _CORPUS_SKIP):
                nskip += 1
                total -= 1
                continue
            # a .fail file means the program is supposed to die; the x64
            # path is allowed to catch it at build time instead of runtime
            _fp = os.path.join(HERE, name + ".fail")
            if os.path.exists(_fp):
                with open(_fp, encoding="utf-8") as f:
                    if f.read().strip() in _err.getvalue():
                        print(f"ok   corpus/{name} (compile error as expected)")
                        continue
            print(f"FAIL corpus/{name}: build failed: {_err.getvalue().strip()}")
            fails += 1
            continue
        _sin = None
        _sp = os.path.join(HERE, name + ".stdin")
        if os.path.exists(_sp):
            with open(_sp, "rb") as f:
                _sin = f.read()
        _args = []
        _ap = os.path.join(HERE, name + ".args")
        if os.path.exists(_ap):
            with open(_ap, encoding="utf-8") as f:
                _args = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
        _clean_corpus()
        try:
            _got = subprocess.run([_out] + _args, input=_sin,
                                  capture_output=True, timeout=60, env=_env)
            got = (_got.stdout.decode(errors="replace"),
                   _got.stderr.decode(errors="replace"),
                   _got.returncode)
        except subprocess.TimeoutExpired:
            got = ("TIMEOUT", "", -99)
        _clean_corpus()
        _ref = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                               prog] + _args, input=_sin,
                              capture_output=True, timeout=120, env=_env)
        want = (_ref.stdout.decode(errors="replace"),
                _ref.stderr.decode(errors="replace"),
                _ref.returncode)
        if got == want:
            print(f"ok   corpus/{name}")
        elif name in _CORPUS_KNOWN:
            nknown += 1
            print(f"ok   corpus/{name} (known x64 divergence: "
                  f"{_CORPUS_KNOWN[name]})")
        else:
            print(f"FAIL corpus/{name}")
            fails += 1
            print(f"  interp: rc={want[2]} out={want[0][:200]!r} "
                  f"err={want[1][-200:]!r}")
            print(f"  x64:    rc={got[2]} out={got[0][:200]!r} "
                  f"err={got[1][-200:]!r}")
print(f"corpus skipped (outside x64 subset): {nskip}")
print(f"corpus known x64 divergences: {nknown}")

# ---------- GC: the alloc bench must run in bounded memory ----------
# 5M short-lived strings used to cost ~690 MB (bump allocator, no free).
total += 1
with tempfile.TemporaryDirectory() as _d:
    _exe = os.path.join(_d, "alloc_bench")
    _rc = build_x64(os.path.join(ROOT, "bench", "alloc.hs"), _exe)
    if _rc != 0:
        print("FAIL gc bound: build failed")
        fails += 1
    else:
        import resource as _res

        def _cap():
            # address-space cap: the old bump allocator needed ~690 MB
            _res.setrlimit(_res.RLIMIT_AS, (100 << 20, 100 << 20))
        _p = subprocess.run([_exe], stdout=subprocess.PIPE,
                            preexec_fn=_cap, timeout=120)
        _out = _p.stdout.decode().strip()
        if _p.returncode == 0 and _out == "48888890":
            print("ok   gc bound: alloc bench runs under a 100 MB address-space cap")
        else:
            print(f"FAIL gc bound: rc={_p.returncode} out={_out!r} (cap 100 MB)")
            fails += 1

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
