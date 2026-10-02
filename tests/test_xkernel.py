#!/usr/bin/env python3
"""holyshit freestanding-x64 kernel tests: python3 tests/test_xkernel.py
Builds kernel/xdemo.hs with zero gcc/as/ld, boots on QEMU, checks serial.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from x64gen import build_xkernel

QEMU = shutil.which("qemu-system-x86_64")

fails = 0
total = 0


def check(name, cond, detail=""):
    global fails, total
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        fails += 1


with tempfile.TemporaryDirectory() as d:
    elf = os.path.join(d, "kx.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "xdemo.hs"), elf)
    check("xkernel build clean", rc == 0)
    if rc != 0:
        print(f"{fails}/{total} passed")
        sys.exit(1)
    if QEMU is None:
        print("skip boot tests (qemu-system-x86_64 not installed)")
    else:
        slog = os.path.join(d, "serial.log")
        p = subprocess.Popen([QEMU, "-kernel", elf, "-serial", f"file:{slog}",
                              "-display", "none"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(8)
        finally:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        try:
            with open(slog, encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        for line in ("hs xkernel boot", "fib: 55", "45", "7", "halted"):
            check(f"boot serial has {line!r}", line in out, out[-800:])

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
