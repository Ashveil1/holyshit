#!/usr/bin/env python3
"""holyshit kernel tests (เฟส 5a/5b): python3 tests/test_kernel.py
- static: build clean, ELF/entry, multiboot1+2 checksums, no-libc
- boot demo.hs: serial lines
- boot kdemo2.hs: timer ticks + keyboard (monitor sendkey) + PMM deltas
- boot kexc_pf.hs / kexc_de.hs: exception stubs print + halt
"""
import io
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from hs import build_kernel

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + (f" ({detail})" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


QEMU = shutil.which("qemu-system-x86_64")


def boot(elf, timeout=30, sendkeys=(), settle=3):
    """Boot elf headless, serial to file. Optionally send monitor keys
    [(delay_after_boot, key)]. Returns serial text."""
    d = tempfile.mkdtemp(prefix="hsboot")
    slog = os.path.join(d, "serial.log")
    msock = os.path.join(d, "mon.sock")
    cmd = [QEMU, "-kernel", elf, "-serial", f"file:{slog}",
           "-display", "none", "-no-reboot"]
    if sendkeys:
        cmd += ["-monitor", f"unix:{msock},server=on,wait=off"]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        mon = None
        if sendkeys:
            for _ in range(50):
                try:
                    mon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    mon.connect(msock)
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                return ""
            mon.recv(4096)
        t0 = time.time()
        for delay, key in sendkeys:
            while time.time() - t0 < delay:
                time.sleep(0.2)
            mon.sendall(f"sendkey {key}\n".encode())
            time.sleep(0.5)
        if mon:
            mon.close()
        # let the guest run / finish
        time.sleep(settle)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        with open(slog, encoding="utf-8", errors="replace") as f:
            return f.read()
    finally:
        p.kill()


def main():
    with tempfile.TemporaryDirectory() as d:
        elf = os.path.join(d, "kernel.elf")
        err = io.StringIO()
        with redirect_stderr(err):
            rc = build_kernel(os.path.join(ROOT, "kernel", "demo.hs"), elf)
        check("kernel build clean", rc == 0, err.getvalue()[-2000:])
        if rc != 0:
            return 1
        k64 = elf + ".k64"
        check("64-bit payload kept", os.path.exists(k64))
        with open(k64, "rb") as f:
            img = f.read()

        check("payload ELF64", img[4] == 2, f"class={img[4]}")
        check("payload x86-64", struct.unpack_from("<H", img, 18)[0] == 62)
        e_entry = struct.unpack_from("<Q", img, 24)[0]
        r = subprocess.run(["nm", k64], capture_output=True, text=True)
        start = None
        has_undef = False
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "U":
                has_undef = True
            if len(parts) == 3 and parts[2] == "_start":
                start = int(parts[0], 16)
        check("no undefined symbols", not has_undef)
        check("entry == _start", start is not None and e_entry == start,
              f"entry={e_entry:#x} _start={start}")

        e_shoff = struct.unpack_from("<Q", img, 40)[0]
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", img, 58)
        sec = {}
        for i in range(e_shnum):
            o = e_shoff + i * e_shentsize
            sec[i] = struct.unpack_from("<IIQQQQ", img, o)
        shstr = sec[e_shstrndx]
        shstrdat = img[shstr[4]:shstr[4] + shstr[5]]
        named = {}
        for i, (name, stype, flags, addr, off, size) in sec.items():
            nm = shstrdat[name:].split(b"\0", 1)[0].decode()
            named[nm] = (addr, off, size)

        def v2f(vaddr):
            for (name, stype, flags, addr, off, size) in sec.values():
                if stype != 8 and addr <= vaddr < addr + size:
                    return off + (vaddr - addr)
            return None

        mb2_off = None
        for v in range(0x100000, 0x100000 + 32768, 8):
            fo = v2f(v)
            if fo is None:
                continue
            if u32(img, fo) == 0xE85250D6:
                mb2_off = fo
                break
        check("mb2 header found in first 32K", mb2_off is not None)
        if mb2_off is not None:
            mb2 = img[mb2_off:mb2_off + 24]
            check("mb2 arch=0", u32(mb2, 4) == 0)
            hlen = u32(mb2, 8)
            check("mb2 checksum",
                  (u32(mb2, 0) + u32(mb2, 4) + hlen + u32(mb2, 12)) % 2**32 == 0)
            check("mb2 end tag", mb2[16:24] == b"\x00\x00\x00\x00\x08\x00\x00\x00")

        mb1_off = None
        for v in range(0x100000, 0x100000 + 8192, 4):
            fo = v2f(v)
            if fo is None:
                continue
            if u32(img, fo) == 0x1BADB002:
                mb1_off = fo
                break
        check("mb1 header found in first 8K", mb1_off is not None)
        if mb1_off is not None:
            mb1 = img[mb1_off:mb1_off + 12]
            check("mb1 checksum", (u32(mb1, 0) + u32(mb1, 4) + u32(mb1, 8)) % 2**32 == 0)

        check("no .dynamic (no libc)", ".dynamic" not in named)
        check("no .interp", ".interp" not in named)

        with open(elf, "rb") as f:
            ldimg = f.read()
        check("loader ELF32", ldimg[4] == 1, f"class={ldimg[4]}")
        mb = ldimg.find(b"\x02\xb0\xad\x1b")
        check("loader mb1 in first 8K", 0 <= mb < 8192, f"off={mb}")
        if mb >= 0:
            check("loader mb1 checksum",
                  (u32(ldimg, mb) + u32(ldimg, mb + 4) + u32(ldimg, mb + 8)) % 2**32 == 0)
        r = subprocess.run(["nm", elf], capture_output=True, text=True)
        check("loader has _start32", " _start32" in r.stdout)
        check("loader no undef symbols",
              not any(l.split()[1] == "U" for l in r.stdout.splitlines() if len(l.split()) >= 3))

        if not QEMU:
            print("skip boot tests (qemu-system-x86_64 not installed)")
            print(f"{'ALL PASS' if not fails else f'{len(fails)} FAILURES: {fails}'}")
            return 1 if fails else 0

        out = boot(elf)
        for line in ("hs kernel boot", "fib: 55", "72", "45", "3.5", "halted"):
            check(f"boot serial has {line!r}", line in out, out[-1500:])

        # timer + keyboard + PMM
        k2 = os.path.join(d, "k2.elf")
        err = io.StringIO()
        with redirect_stderr(err):
            rc = build_kernel(os.path.join(ROOT, "kernel", "kdemo2.hs"), k2)
        check("kdemo2 build clean", rc == 0, err.getvalue()[-2000:])
        if rc == 0:
            out = boot(k2, timeout=40, sendkeys=[(4, "a")], settle=6)
            m0 = re.search(r"t0: (\d+)", out)
            m1 = re.search(r"t1: (\d+)", out)
            check("timer t0/t1 present", m0 and m1, out[-1500:])
            if m0 and m1:
                check("timer advanced ~200 ticks", int(m1.group(1)) - int(m0.group(1)) >= 150,
                      f"t0={m0.group(1)} t1={m1.group(1)}")
            check("keyboard key: a", "key: a" in out, out[-1500:])
            mems = re.findall(r"\{total: (\d+), free: (\d+), page: 4096\}", out)
            check("meminfo x2", len(mems) == 2, out[-1500:])
            if len(mems) == 2:
                t0, f0 = map(int, mems[0])
                t1, f1 = map(int, mems[1])
                check("pmm total sane", t0 >= 30000, str(mems))
                check("pmm total stable", t0 == t1, str(mems))
                check("pmm_alloc(3) freed -3", f0 - f1 == 3, str(mems))
            check("kdone", "kdone" in out, out[-1500:])

        # exceptions halt with report
        for prog, vec in (("kexc_pf.hs", "EXC 14"), ("kexc_de.hs", "EXC 0")):
            kx = os.path.join(d, "kx.elf")
            err = io.StringIO()
            with redirect_stderr(err):
                rc = build_kernel(os.path.join(ROOT, "kernel", prog), kx)
            check(f"{prog} build clean", rc == 0, err.getvalue()[-2000:])
            if rc == 0:
                out = boot(kx, settle=2)
                check(f"{prog} reports {vec}", vec in out, out[-1500:])
                check(f"{prog} halts after", "after-" not in out, out[-1500:])

    print(f"{'ALL PASS' if not fails else f'{len(fails)} FAILURES: {fails}'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
