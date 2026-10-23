#!/usr/bin/env python3
"""The hs source compiler's AArch64 target matches a64build.py byte for byte.

Build a host-native compiler, compare the complete tests/*.holy corpus including
refusal classification, and run three generated programs on arm64 or QEMU.
Python is the independent reference/test harness, not the compiler under test.
"""
import glob
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARM = platform.machine() in ("aarch64", "arm64")
ENV = dict(os.environ, HSROOT=str(ROOT), HSPATH=os.pathsep.join(
    str(ROOT / p) for p in ("selfhost/a64", "selfhost", "selfhost/be")))


def run(args, timeout=120):
    return subprocess.run([str(x) for x in args], cwd=ROOT, env=ENV,
                          capture_output=True, timeout=timeout)


def main():
    good = refused = 0
    with tempfile.TemporaryDirectory(prefix="hs-a64compiler.") as d:
        d = Path(d)
        compiler = d / "compiler"
        source = ROOT / "selfhost/be/compile.holy"
        build = ([sys.executable, ROOT / "a64build.py"] if ARM else
                 [ROOT / "bootstrap/hs-hosted-x86_64"])
        r = run(build + [source, compiler], timeout=600)
        if r.returncode:
            print("FAIL compiler build:", r.stderr.decode(errors="replace")[-600:])
            return 1
        smoke = {}
        for source in sorted(glob.glob(str(ROOT / "tests/*.holy"))):
            name = Path(source).stem
            want, got = d / "reference", d / "actual"
            want.unlink(missing_ok=True)
            got.unlink(missing_ok=True)
            ref = run([sys.executable, ROOT / "a64build.py", source, want])
            actual = run([compiler, source, got])
            if bool(ref.returncode) != bool(actual.returncode):
                print("FAIL refusal:", name, ref.returncode, actual.returncode,
                      actual.stderr.decode(errors="replace")[-300:])
                return 1
            if ref.returncode:
                if got.exists():
                    print("FAIL refused source wrote an ELF:", name)
                    return 1
                refused += 1
                continue
            if not got.exists() or got.read_bytes() != want.read_bytes():
                print("FAIL ELF bytes:", name,
                      actual.stderr.decode(errors="replace")[-300:])
                return 1
            if got.read_bytes()[18:20] != bytes([183, 0]):
                print("FAIL non-AArch64 ELF:", name)
                return 1
            good += 1
            if name in ("fib", "dict_hash", "floatlit"):
                dest = d / name
                shutil.copy2(got, dest)
                smoke[name] = dest
        if not good or not refused:
            print("FAIL empty positive or negative corpus")
            return 1
        print(f"ok AArch64 compiler: {good} identical ELFs, {refused} shared refusals")
        qemu = (shutil.which("qemu-aarch64") or shutil.which("qemu-aarch64-static"))
        fallback = Path("/tmp/qemu-user/usr/bin/qemu-aarch64-static")
        if not qemu and fallback.exists():
            qemu = str(fallback)
        if ARM or qemu:
            if len(smoke) != 3:
                print("FAIL missing smoke fixtures:", sorted(smoke))
                return 1
            for name, image in smoke.items():
                ref = run([sys.executable, ROOT / "interp.py", ROOT / f"tests/{name}.holy"])
                actual = run(([] if ARM else [qemu]) + [image])
                if (actual.returncode, actual.stdout, actual.stderr) != (
                        ref.returncode, ref.stdout, ref.stderr):
                    print("FAIL execution:", name, actual.returncode,
                          actual.stderr.decode(errors="replace")[-300:])
                    return 1
            print("ok 3 AArch64 execution checks (" + ("native" if ARM else "QEMU") + ")")
        else:
            print("skip execution: no arm64 host or QEMU; byte oracle passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
