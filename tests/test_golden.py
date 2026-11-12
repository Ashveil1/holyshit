#!/usr/bin/env python3
"""Golden corpus parity gate: python3 tests/test_golden.py

Builds the eager in-process JIT driver (selfhost/be/jit_run.holy) once from
the committed seed, then runs every runnable tests/<name>.holy through it
and compares (exit code, stdout, stderr) byte for byte against the FROZEN
reference in tests/golden/<name>.golden (regenerate intentionally with
python3 scripts/mkgolden.py). Unlike tests/test_jit_corpus.py this gate
needs no live interpreter, so corpus parity still gates CI when interp.py
is no longer part of it.

Every corpus entry is classified by tests/corpus_pins.py:
- parity:     must match the golden byte for byte (the gate)
- divergence: documented native/JIT-vs-interp difference, asserted NOT to be
              byte-equal so a future fix forces reclassification there and in
              docs/jit-corpus.md

Coverage is part of the gate: every runnable tests/<name>.holy must have a
golden and every golden must have a program, so adding or removing a corpus
program forces a deliberate scripts/mkgolden.py run.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from corpus_pins import DIVERGENCE

GOLDEN = os.path.join(HERE, "golden")

_BASE_ENV = dict(os.environ)
_BASE_ENV["HSPATH"] = os.path.join(ROOT, "selfhost") + ":" + os.path.join(ROOT, "selfhost", "be")
_BASE_ENV["HSROOT"] = ROOT


def _test_env(name):
    # per-test env overlay: tests/<name>.env has KEY=VAL lines (# comments ok)
    e = dict(_BASE_ENV)
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


def _read_golden(path):
    with open(path, "rb") as f:
        data = f.read()
    head, _, body = data.partition(b"\n\n")
    fields = {}
    lines = head.split(b"\n")
    assert lines[0] == b"HSGOLD1", f"{path}: bad magic"
    for ln in lines[1:]:
        k, _, v = ln.partition(b"=")
        fields[k.decode()] = int(v)
    rc = fields["rc"]
    out = body[:fields["stdout"]]
    err = body[fields["stdout"]:fields["stdout"] + fields["stderr"]]
    assert len(out) == fields["stdout"] and len(err) == fields["stderr"], \
        f"{path}: truncated golden"
    return (rc, out, err)


def _run_driver(driver, prog, stdin, env, pargs):
    # t_fs uses a fixed scratch dir: start clean so ls() is deterministic.
    shutil.rmtree("/tmp/opencode/hs_fs_test", ignore_errors=True)
    r = subprocess.run([driver, prog] + pargs, input=stdin, capture_output=True,
                       timeout=120, env=env, cwd=ROOT)
    return (r.returncode, r.stdout, r.stderr)


fails = 0
total = 0
with tempfile.TemporaryDirectory(prefix="hs-golden.") as d:
    driver = os.path.join(d, "jit")
    r = subprocess.run([os.path.join(ROOT, "bootstrap", "hs-hosted-x86_64"),
                        os.path.join(ROOT, "selfhost", "be", "jit_run.holy"),
                        driver],
                       capture_output=True, timeout=600, env=_BASE_ENV)
    if r.returncode != 0:
        print(f"FAIL jit driver build: {r.stderr.decode().strip()[-400:]}")
        sys.exit(1)
    for prog in sorted(glob.glob(os.path.join(HERE, "*.holy"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue  # helper module, imported by other tests, never run directly
        if os.path.exists(os.path.join(HERE, name + ".nativeonly")):
            continue  # interp skips these; no reference recorded
        total += 1
        gpath = os.path.join(GOLDEN, name + ".golden")
        if not os.path.exists(gpath):
            print(f"FAIL {name}: no golden - run python3 scripts/mkgolden.py "
                  f"and commit tests/golden/{name}.golden")
            fails += 1
            continue
        ref = _read_golden(gpath)
        stdin = None
        sin_path = os.path.join(HERE, name + ".stdin")
        if os.path.exists(sin_path):
            with open(sin_path, "rb") as f:
                stdin = f.read()
        pargs = []
        args_path = os.path.join(HERE, name + ".args")
        if os.path.exists(args_path):
            with open(args_path, encoding="utf-8") as f:
                pargs = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
        try:
            got = _run_driver(driver, prog, stdin, _test_env(name), pargs)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: JIT timeout")
            fails += 1
            continue
        same = ref == got
        if name in DIVERGENCE:
            if same:
                print(f"FAIL {name}: now byte-identical to the frozen reference; "
                      f"move it out of DIVERGENCE (was: {DIVERGENCE[name]})")
                fails += 1
            else:
                print(f"ok   {name} (documented divergence)")
            continue
        if not same:
            print(f"FAIL {name}: rc {ref[0]} -> {got[0]}\n"
                  f"--- golden stdout ---\n{ref[1].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- jit stdout ---\n{got[1].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- golden stderr ---\n{ref[2].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- jit stderr ---\n{got[2].decode('utf-8', 'replace')[-400:]}\n"
                  f"(if the interp reference changed deliberately, regenerate: "
                  f"python3 scripts/mkgolden.py)")
            fails += 1
            continue
        print(f"ok   {name}")
    for g in sorted(glob.glob(os.path.join(GOLDEN, "*.golden"))):
        name = os.path.splitext(os.path.basename(g))[0]
        if not os.path.exists(os.path.join(HERE, name + ".holy")):
            print(f"FAIL stale golden {name}.golden: no tests/{name}.holy")
            fails += 1

if fails:
    print(f"{total - fails}/{total} golden corpus parity")
    sys.exit(1)
print(f"{total}/{total} golden corpus parity")
