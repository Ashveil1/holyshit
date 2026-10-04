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

# kernel modules import std.*, so the repo root has to be on HSPATH
os.environ["HSPATH"] = ROOT + os.pathsep + os.environ.get("HSPATH", "")

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
    # List values on bare metal
    kl = os.path.join(d, "kl.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kxlist.hs"), kl)
    check("kxlist build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kl, timeout=8)
        for line in ("[1, 2, 3]", "[1, 2, 3, 4]", "[99, 2, 3, 4]",
                     "108", "[0, 1, 2]", "klist-done"):
            check(f"kxlist serial has {line!r}", line in out, out[-800:])
    # import on bare metal (module init + attr, no OS)
    ki = os.path.join(d, "ki.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kimp.hs"), ki)
    check("kimp build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(ki, timeout=8)
        for line in ("42", "kmod", "kimp-done"):
            check(f"kimp serial has {line!r}", line in out, out[-800:])
    # slicing + split/find/join on bare metal
    kc = os.path.join(d, "kc.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kxslice.hs"), kc)
    check("kxslice build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kc, timeout=8)
        for line in ("hello", "world", "[a, b, c]", "[x, , y]", "2", "-1",
                     "a-b", "[20, 30]", "[30, 40]", "kslice-done"):
            check(f"kxslice serial has {line!r}", line in out, out[-800:])
    # try/except/finally/raise on bare metal
    kt = os.path.join(d, "kt.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "ktry.hs"), kt)
    check("ktry build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kt, timeout=8)
        for line in ("k-try", "cannot add Int and Str", "k-boom",
                     "k-fin", "k-zero", "k-clean", "k-after", "ktry-done",
                     "k-fin-before-rethrow", "k-fin-before-typeerror",
                     "k-end"):
            check(f"ktry serial has {line!r}", line in out, out[-800:])
        # finally must run before the error keeps unwinding
        order = [out.find(x) for x in ("k-fin-before-rethrow",
                                       "k-outer at line")]
        check("ktry finally runs before rethrow unwinds",
              all(i >= 0 for i in order) and order[0] < order[1], order)
    # memory introspection primitives (CR3/CR2/mb_info/mb_magic/image_end/invlpg)
    kp = os.path.join(d, "kp.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kprim.hs"), kp)
    check("kprim build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kp, timeout=8)
        for line in ("kprim", "kprim-done"):
            check(f"kprim serial has {line!r}", line in out, out[-800:])
        check("kprim did not fault", "EXC " not in out, out[-800:])
    # dynamic paging: map/unmap frames, split huge pages, use the mappings
    kpg = os.path.join(d, "kpg.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kpaging.hs"), kpg)
    check("kpaging build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kpg, timeout=8)
        check("kpaging finished", "kpaging-done" in out, out[-800:])
        check("kpaging did not fault", "EXC " not in out, out[-800:])
        # kpaging.hs counts its own failures and prints "fails N"
        m = re.search(r"fails (\d+)", out)
        check("kpaging all assertions pass", m and m.group(1) == "0",
              out[-800:])
        check("kpaging ran its checks", out.count("\nok ") >= 30, out[-800:])
    # real frame allocator on the bootloader's memory map
    km = os.path.join(d, "km.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kpmmtest.hs"), km)
    check("kpmmtest build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(km, timeout=10)
        check("kpmm banner", "kpmm" in out, out[-800:])
        check("kpmm finished", "kpmm-done" in out, out[-800:])
        check("kpmm did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kpmm all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kpmm ran its checks", out.count("\nok ") >= 25, out[-800:])
    # kmalloc: std.heap over real frames
    kh = os.path.join(d, "kh.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kheaptest.hs"), kh)
    check("kheaptest build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kh, timeout=10)
        check("kheap finished", "kheap-done" in out, out[-800:])
        check("kheap did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kheap all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kheap ran its checks", out.count("\nok ") >= 25, out[-800:])
    # address spaces: a new PML4 shares the kernel, isolates user pages
    ka = os.path.join(d, "ka.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kaddrtest.hs"), ka)
    check("kaddrtest build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(ka, timeout=10)
        check("kaddr finished", "kaddr-done" in out, out[-800:])
        check("kaddr did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kaddr all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kaddr ran its checks", out.count("\nok ") >= 20, out[-800:])
    # cooperative tasks: spawn/yield/exit/switch on bare metal
    kt = os.path.join(d, "kt.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "ktasktest.hs"), kt)
    check("ktasktest build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kt, timeout=10)
        check("ktask finished", "ktask-done" in out, out[-800:])
        check("ktask did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("ktask all assertions pass", m and m.group(1) == "0", out[-800:])
        check("ktask ran its checks", out.count("\nok ") >= 12, out[-800:])
        order = [out.find(x) for x in ("a start", "b start", "c start")]
        check("ktask starts in round-robin order",
              all(i >= 0 for i in order) and order == sorted(order), order)
        exits = [out.find(x) for x in ("a exit", "b exit", "c exit")]
        check("ktask all tasks exit, c last",
              all(i >= 0 for i in exits) and exits[2] == max(exits), exits)
    # preemption: hogs that never yield are still force-switched
    kp = os.path.join(d, "kpre.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kpreempt.hs"), kp)
    check("kpreempt build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kp, timeout=15)
        check("kpreempt finished", "kpreempt-done" in out, out[-800:])
        check("kpreempt did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kpreempt all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kpreempt every hog preempted",
              all(f"ok hog{i} was preempted" in out for i in range(3)),
              out[-800:])
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
