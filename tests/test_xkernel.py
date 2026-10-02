#!/usr/bin/env python3
"""holyshit freestanding-x64 kernel tests: python3 tests/test_xkernel.py
Builds kernel/*.hs with zero gcc/as/ld, boots on QEMU, checks serial.
"""
import os
import re
import shutil
import socket
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


def boot(elf, timeout=30, sendkeys=(), mem="256M"):
    d = tempfile.mkdtemp(prefix="xkboot_")
    slog = os.path.join(d, "serial.log")
    msock = os.path.join(d, "mon.sock")
    p = subprocess.Popen([QEMU, "-kernel", elf, "-serial", f"file:{slog}",
                          "-display", "none", "-m", mem,
                          "-monitor", f"unix:{msock},server=on,wait=off"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for delay, key in sendkeys:
            time.sleep(delay)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(msock)
            s.sendall(f"sendkey {key}\n".encode())
            s.close()
        time.sleep(timeout)
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
    with open(slog, encoding="utf-8", errors="replace") as f:
        return f.read()


with tempfile.TemporaryDirectory() as d:
    kx = os.path.join(d, "kx.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "xdemo.hs"), kx)
    check("xkernel build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kx, timeout=8)
        for line in ("hs xkernel boot", "fib: 55", "45", "7", "halted"):
            check(f"boot serial has {line!r}", line in out, out[-800:])
    # timer + keyboard + PMM
    k2 = os.path.join(d, "k2.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kx2.hs"), k2)
    check("kx2 build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(k2, timeout=6, sendkeys=[(4, "a")])
        m0 = re.search(r"t0: (\d+)", out)
        m1 = re.search(r"t1: (\d+)", out)
        check("timer t0/t1 present", m0 and m1, out[-800:])
        if m0 and m1:
            check("timer advanced ~200 ticks",
                  int(m1.group(1)) - int(m0.group(1)) >= 150, out[-800:])
        check("keyboard key: a", "key: a" in out, out[-800:])
        mems = re.findall(r"\{'total': (\d+), 'free': (\d+)", out)
        if not mems:
            mems = re.findall(r"total[:=]?\s*(\d+)", out)
        check("pmm total sane", "32768" in out, out[-800:])
        check("pmm alloc(3) addr", "67108864" in out, out[-800:])
        check("pmm free delta -3", "32765" in out, out[-800:])
        check("kdone", "kdone" in out, out[-800:])
    # Str / Bool / Null values on bare metal
    ks = os.path.join(d, "ks.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kxstr.hs"), ks)
    check("kxstr build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(ks, timeout=8)
        for line in ("ab", "abcd", "true", "false", "null",
                     "zero is false", "kstr-done"):
            check(f"kxstr serial has {line!r}", line in out, out[-800:])
        check("kxstr len", "4" in out and "2" in out, out[-800:])
    # exceptions
    for prog, vec in (("kxexc_pf.hs", "EXC 14"), ("kxexc_de.hs", "EXC 0")):
        kx = os.path.join(d, "kx.elf")
        rc = build_xkernel(os.path.join(ROOT, "kernel", prog), kx)
        check(f"{prog} build clean", rc == 0)
        if rc == 0 and QEMU is not None:
            out = boot(kx, timeout=8)
            check(f"{prog} reports {vec}", vec in out, out[-800:])
    if QEMU is None:
        print("skip boot tests (qemu-system-x86_64 not installed)")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
