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
from x64gen import build_xkernel, build_x64

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


def boot(elf, timeout=30, sendkeys=(), mem="256M", initrd=None, disk=None):
    d = tempfile.mkdtemp(prefix="xkboot_")
    slog = os.path.join(d, "serial.log")
    msock = os.path.join(d, "mon.sock")
    cmd = [QEMU, "-kernel", elf, "-serial", f"file:{slog}",
           "-display", "none", "-m", mem,
           "-monitor", f"unix:{msock},server=on,wait=off"]
    if initrd is not None:
        # multiboot module 0: the kernel reads it via kmb.mod_start(0)
        cmd += ["-initrd", initrd]
    if disk is not None:
        # raw disk on the primary IDE channel: the ATA driver reads it
        cmd += ["-drive", f"file={disk},if=ide,format=raw,index=0,media=disk"]
    p = subprocess.Popen(cmd,
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
    # filesystem: ramdisk via -initrd plus live file operations
    rd = os.path.join(d, "ramdisk.krfs")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "mkramdisk.py"),
                        os.path.join(ROOT, "kernel", "ramdisk"), rd],
                       capture_output=True, text=True)
    check("mkramdisk packs", r.returncode == 0, r.stderr[-300:])
    kf = os.path.join(d, "kf.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kfstest.hs"), kf)
    check("kfstest build clean", rc == 0)
    if rc == 0 and r.returncode == 0 and QEMU is not None:
        out = boot(kf, timeout=10, initrd=rd)
        check("kfs finished", "kfs-done" in out, out[-800:])
        check("kfs did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kfs all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kfs ran its checks", out.count("\nok ") >= 25, out[-800:])
    # user mode: hand-built ring-3 stub exits through the syscall stub
    kr = os.path.join(d, "kr3.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kring3.hs"), kr)
    check("kring3 build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kr, timeout=10)
        check("kring3 finished", "kring3-done" in out, out[-800:])
        check("kring3 did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kring3 all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kring3 ran its checks", out.count("\nok ") >= 20, out[-800:])
    # user mode: sysret back to ring 3, then hlt faults with the USER rip
    kret = os.path.join(d, "kret.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kring3ret.hs"), kret)
    check("kring3ret build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(kret, timeout=10)
        check("kring3ret handler ran", "ret-ok" in out, out[-800:])
        check("kring3ret faults in ring 3",
              re.search(r"EXC 13 rip=87\d+ cs=35", out) is not None,
              out[-800:])
    # user mode: write() returns to ring 3, then exit() stops back in kernel
    krw = os.path.join(d, "krw.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kring3wr.hs"), krw)
    check("kring3wr build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(krw, timeout=10)
        check("kring3wr finished", "kring3wr-done" in out, out[-800:])
        check("kring3wr did not fault", "EXC " not in out, out[-800:])
        check("kring3wr user output", "hello" in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kring3wr all assertions pass", m and m.group(1) == "0", out[-800:])
    # user mode: real user ELF in ring 3, syscalls served from .hs
    uu = os.path.join(d, "uuser.elf")
    rc = build_x64(os.path.join(ROOT, "kernel", "uuser.hs"), uu)
    check("uuser build clean", rc == 0)
    ku = os.path.join(d, "ku.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kusermode.hs"), ku)
    check("kusermode build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        # 25s: binaries grew (arity checks, file runtime, names) and TCG
        # translation is slow on the first boot; 15s flaked on loaded hosts
        out = boot(ku, timeout=25, initrd=uu)
        check("kusermode finished", "kusermode-done" in out, out[-800:])
        check("kusermode did not fault", "EXC " not in out, out[-800:])
        for line in ("hello from ring 3, holyshit", "user line 3"):
            check(f"kusermode user output {line!r}", line in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kusermode all assertions pass", m and m.group(1) == "0",
              out[-800:])
        check("kusermode ran its checks", out.count("\nok ") >= 15, out[-800:])
    # file syscalls without ring 3: sys_open/read/write/close + copy_out,
    # deterministic (no keyboard timing involved)
    kio = os.path.join(d, "kio.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kiotest.hs"), kio)
    check("kiotest build clean", rc == 0)
    if rc == 0 and r.returncode == 0 and QEMU is not None:
        out = boot(kio, timeout=10, initrd=rd)
        check("kio finished", "kiotest-done" in out, out[-800:])
        check("kio did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kio all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kio ran its checks", out.count("\nok ") >= 10, out[-800:])
    # ATA driver (kernel/kata.hs) on a real IDE disk: identify + PIO
    # read/write round-trip. The image is built here so the pattern
    # sector 4 (AB CD 5A repeating) and the intact neighbour byte
    # (sector 10 offset 0 = 0x5A) are exactly what katatest expects.
    kdisk = os.path.join(d, "kata.img")
    with open(kdisk, "wb") as f:
        img = bytearray(1 << 20)
        pat = (0xAB, 0xCD, 0x5A)
        for i in range(512):
            img[4 * 512 + i] = pat[i % 3]
        img[10 * 512] = 0x5A
        f.write(img)
    ka = os.path.join(d, "kata.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "katatest.hs"), ka)
    check("katatest build clean", rc == 0)
    if rc == 0 and QEMU is not None:
        out = boot(ka, timeout=20, disk=kdisk)
        check("kata finished", "kata-done" in out, out[-800:])
        check("kata did not fault", "EXC " not in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kata all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kata ran its checks", out.count("\nok ") >= 8, out[-800:])
    # shell: stage ramdisk + user ELFs, pack, then type over sendkeys.
    # Keys start late and slow: TCG boot takes seconds and the keyboard
    # flag is one deep, so anything typed during boot collapses.
    shd = os.path.join(d, "stage")
    shutil.copytree(os.path.join(ROOT, "kernel", "ramdisk"), shd)
    os.makedirs(os.path.join(shd, "bin"))
    uu = os.path.join(d, "uush.elf")
    rc = build_x64(os.path.join(ROOT, "kernel", "uush.hs"), uu)
    check("uush build clean", rc == 0)
    uh = os.path.join(d, "hi.elf")
    rc = build_x64(os.path.join(ROOT, "kernel", "uuhi.hs"), uh)
    check("uuhi build clean", rc == 0)
    shutil.copy(uu, os.path.join(shd, "bin", "uush"))
    shutil.copy(uh, os.path.join(shd, "bin", "hi"))
    srd = os.path.join(d, "shell.krfs")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "mkramdisk.py"),
                        shd, srd], capture_output=True, text=True)
    check("shell ramdisk packs", r.returncode == 0, r.stderr[-300:])
    ku = os.path.join(d, "kush.elf")
    rc = build_xkernel(os.path.join(ROOT, "kernel", "kushtest.hs"), ku)
    check("kushtest build clean", rc == 0)

    def shkeys(lines):
        # (delay, key) with a slow start and 0.6s pacing; \x08 = backspace.
        # Unknown QEMU key names fail LOUD (reply-checked) instead of
        # silently dropping keys and garbling the session.
        out = []
        first = True
        for line in lines:
            for ch in line:
                if ch == "\x08":
                    key = "backspace"
                elif ch == " ":
                    key = "spc"
                elif ch == "/":
                    key = "slash"
                else:
                    key = ch
                out.append(((15 if first else 0.6), key))
                first = False
            out.append((0.6, "ret"))
        return out

    def shboot(lines, timeout):
        # boot() but every sendkey reply is checked for errors
        slog = os.path.join(d, "shserial.log")
        msock = os.path.join(d, "shmon.sock")
        if os.path.exists(slog):
            os.unlink(slog)
        try:
            os.unlink(msock)
        except OSError:
            pass
        p = subprocess.Popen([QEMU, "-kernel", ku, "-serial", f"file:{slog}",
                              "-display", "none", "-m", "256M",
                              "-monitor", f"unix:{msock},server=on,wait=off",
                              "-initrd", srd],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for delay, key in shkeys(lines):
                time.sleep(delay)
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect(msock)
                s.recv(4096)
                s.sendall(f"sendkey {key}\n".encode())
                time.sleep(0.2)
                try:
                    rep = s.recv(4096).decode(errors="replace")
                except socket.timeout:
                    rep = ""
                s.close()
                check(f"sendkey {key} accepted", "error" not in rep.lower()
                      and "unknown" not in rep.lower(), rep[-200:])
            time.sleep(timeout)
        finally:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        with open(slog, encoding="utf-8", errors="replace") as f:
            return f.read()

    if rc == 0 and r.returncode == 0 and QEMU is not None:
        # session A: files, errors, write/rm, backspace correction, exit
        out = shboot(["help", "ls /", "caa\x08t /motd", "cat /nope", "bogus",
                      "mkdir /tmp", "ls /", "write /n xyzzy 123", "cat /n",
                      "rm /n", "exit"], 25)
        check("kush finished", "kushell-done" in out, out[-800:])
        check("kush did not fault", "EXC " not in out, out[-800:])
        for line in ("commands: help echo cat ls mkdir rm write run exit",
                     "holyshit test ramdisk", "second line here",
                     "no such file", "unknown command: bogus", "xyzzy 123"):
            check(f"kush output {line!r}", line in out, out[-800:])
        check("kush tmp listed", "\ntmp\n" in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kush all assertions pass", m and m.group(1) == "0", out[-800:])
        check("kush ran its checks", out.count("\nok ") >= 12, out[-800:])
        # session B: exec a real program from VFS (one-shot: no return)
        out = shboot(["help", "ls /", "run /nope", "run /bin/hi"], 20)
        check("kushexec finished", "kushell-done" in out, out[-800:])
        check("kushexec did not fault", "EXC " not in out, out[-800:])
        for line in ("exec failed", "hi from exec"):
            check(f"kushexec output {line!r}", line in out, out[-800:])
        m = re.search(r"fails (\d+)", out)
        check("kushexec all assertions pass", m and m.group(1) == "0",
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
