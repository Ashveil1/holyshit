#!/usr/bin/env python3
"""arm64 corpus differential: interp.py vs IR backend -> arm64 ELF under qemu.

python3 tests/arm64_corpus.py [name ...]   (QEMU_AARCH64 overrides the binary)
Reports ok / FAIL / build-refused per program; not a gate yet.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QEMU = os.environ.get("QEMU_AARCH64") or shutil.which("qemu-aarch64") or \
    shutil.which("qemu-aarch64-static") or "/tmp/qemu-user/usr/bin/qemu-aarch64-static"
if not os.path.exists(QEMU):
    print("ok   skip arm64 corpus: qemu-aarch64 unavailable")
    sys.exit(0)
env0 = dict(os.environ)
env0["HSROOT"] = ROOT


def env_for(name):
    e = dict(env0)
    p = os.path.join(HERE, name + ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip()
    return e


def run(cmd, stdin, env):
    shutil.rmtree("/tmp/opencode/hs_fs_test", ignore_errors=True)
    try:
        r = subprocess.run(cmd, input=stdin, capture_output=True, timeout=60, env=env, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return (-1, b"", b"timeout")
    return (r.returncode, r.stdout, r.stderr)


names = sys.argv[1:] or [os.path.splitext(os.path.basename(p))[0]
                         for p in sorted(glob.glob(os.path.join(HERE, "*.holy")))]
ok = refused = bad = 0
FAILED = []
PIN_FAIL = {"err_umix", "t_bits"}   # documented x64 Int divergences
EXPECT_FAIL, EXPECT_REFUSED = 2, 14
with tempfile.TemporaryDirectory(prefix="hs-a64.") as d:
    for name in names:
        if name.startswith("mod_") or os.path.exists(os.path.join(HERE, name + ".nativeonly")):
            continue
        prog = os.path.join(HERE, name + ".holy")
        stdin = None
        if os.path.exists(os.path.join(HERE, name + ".stdin")):
            stdin = open(os.path.join(HERE, name + ".stdin"), "rb").read()
        pargs = []
        if os.path.exists(os.path.join(HERE, name + ".args")):
            pargs = [l.rstrip("\n") for l in open(os.path.join(HERE, name + ".args")) if l.strip()]
        env = env_for(name)
        ref = run([sys.executable, os.path.join(ROOT, "interp.py"), prog] + pargs, stdin, env)
        out = os.path.join(d, name)
        b = subprocess.run([sys.executable, os.path.join(ROOT, "a64build.py"), prog, out],
                           capture_output=True, env=env, cwd=ROOT)
        if b.returncode != 0 or not os.path.exists(out):
            refused += 1
            msg = (b.stdout + b.stderr).decode("utf-8", "replace").strip().splitlines()
            print(f"build {name}: {msg[-1][:120] if msg else b.returncode}")
            continue
        got = run([QEMU, out] + pargs, stdin, env)
        if got == ref:
            ok += 1
            print(f"ok   {name}")
        else:
            bad += 1
            FAILED.append(name)
            print(f"FAIL {name}: rc {ref[0]} -> {got[0]}  out {ref[1][:60]!r} vs {got[1][:60]!r} err {got[2][:80]!r}")
print(f"arm64 corpus: {ok} ok, {bad} fail, {refused} build-refused")
if not sys.argv[1:]:
    # pinned classification of the full corpus (same refusals as the x64 backend,
    # plus extern libraries, which need a dynamic aarch64 image)
    if (bad, refused) != (EXPECT_FAIL, EXPECT_REFUSED) or set(FAILED) != PIN_FAIL:
        print(f"arm64 corpus: unexpected (fail={sorted(FAILED)})")
        sys.exit(1)
