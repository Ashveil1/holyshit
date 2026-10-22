#!/usr/bin/env python3
"""arm64 assembler gate: python3 tests/test_arm64_asm.py

Assembles small A64 programs with arm64.py into static ELF64 files, runs them
(natively on an arm64 host, else under qemu-aarch64[-static]) and compares
stdout and exit status with values computed in Python. Skips with a clear
message when no arm64 execution route exists.
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import arm64
from arm64 import Asm, SP, XZR, LR, FP

X0, X1, X2, X3, X4, X5, X8, X19, X20 = 0, 1, 2, 3, 4, 5, 8, 19, 20


def runner():
    if platform.machine() in ("aarch64", "arm64"):
        return []
    for name in ("qemu-aarch64-static", "qemu-aarch64"):
        p = shutil.which(name)
        if p:
            return [p]
    for p in ("/tmp/qemu-user/usr/bin/qemu-aarch64-static",):
        if os.path.exists(p):
            return [p]
    return None


def print_int(a):
    # x0 = signed value; writes decimal + "\n" to fd 1. Clobbers x0-x5.
    a.label("print_int")
    a.stp_pre(FP, LR, SP, -48)
    a.add_imm(FP, SP, 0)
    a.add_imm(X1, SP, 47)            # write cursor (end of buffer)
    a.mov_imm(X2, 10)
    a.strb(X2, X1, 0)                # newline
    a.mov_imm(X5, 0)                 # sign flag
    a.cmp_imm(X0, 0)
    a.b_cond("ge", "pi_pos")
    a.neg(X0, X0)
    a.mov_imm(X5, 1)
    a.label("pi_pos")
    a.label("pi_loop")
    a.mov_imm(X2, 10)
    a.udiv(X3, X0, X2)
    a.msub(X4, X3, X2, X0)           # x4 = x0 - x3*10
    a.add_imm(X4, X4, 48)
    a.sub_imm(X1, X1, 1)
    a.strb(X4, X1, 0)
    a.mov(X0, X3)
    a.cbnz(X0, "pi_loop")
    a.cbz(X5, "pi_out")
    a.mov_imm(X2, 45)
    a.sub_imm(X1, X1, 1)
    a.strb(X2, X1, 0)
    a.label("pi_out")
    a.add_imm(X2, SP, 48)
    a.sub(X2, X2, X1)                # length
    a.sub_imm(X2, X2, 1)
    a.add_imm(X2, X2, 1)
    a.mov_imm(X0, 1)
    a.mov_imm(X8, 64)
    a.svc()
    a.ldp_post(FP, LR, SP, 48)
    a.ret()


def program_basic():
    a = Asm()
    a.b("main")
    print_int(a)
    a.label("main")
    # fib(1..20) with registers x19,x20 preserved across calls
    a.mov_imm(X19, 0)
    a.mov_imm(X20, 1)
    a.mov_imm(6, 20)                 # counter in x6 (reloaded: print_int clobbers x0-x5)
    a.label("fib_loop")
    a.mov(X0, X20)
    a.stp_pre(6, 7, SP, -16)
    a.bl("print_int")
    a.ldp_post(6, 7, SP, 16)
    a.add(X1, X19, X20)
    a.mov(X19, X20)
    a.mov(X20, X1)
    a.sub_imm(6, 6, 1)
    a.cbnz(6, "fib_loop")
    # signed ops
    for v in (-7, 7):
        a.mov_imm(X0, v)
        a.mov_imm(X1, 3)
        a.sdiv(X2, X0, X1)
        a.msub(X3, X2, X1, X0)       # remainder (truncated)
        a.mov(X0, X2)
        a.bl("print_int")
        a.mov_imm(X0, v)
        a.mov_imm(X1, 3)
        a.sdiv(X2, X0, X1)
        a.msub(X0, X2, X1, X0)
        a.bl("print_int")
    # shifts and logic
    a.mov_imm(X0, 0x123456789ABCDEF)
    a.lsr_imm(X0, X0, 12)
    a.bl("print_int")
    a.mov_imm(X0, -4096)
    a.asr_imm(X0, X0, 4)
    a.bl("print_int")
    a.mov_imm(X0, 5)
    a.lsl_imm(X0, X0, 40)
    a.bl("print_int")
    a.mov_imm(X0, 0xF0F0)
    a.mov_imm(X1, 0x0FF0)
    a.and_(X19, X0, X1)
    a.orr(X20, X0, X1)
    a.eor(21, X0, X1)
    for r in (X19, X20, 21):
        a.mov(X0, r)
        a.bl("print_int")
    a.mov_imm(X0, 3)
    a.mov_imm(X1, 5)
    a.cmp(X0, X1)
    a.csel(X19, X0, X1, "gt")        # picks x1 (5): 3 > 5 is false
    a.cset(X20, "lt")
    a.mov(X0, X19)
    a.bl("print_int")
    a.mov(X0, X20)
    a.bl("print_int")
    a.mov_imm(X0, 2 ** 62 + 12345)
    a.bl("print_int")
    a.mov_imm(X0, 0)
    a.mov_imm(X8, 93)
    a.svc()
    return a.finish()


def expected_basic():
    out = []
    x, y = 0, 1
    for _ in range(20):
        out.append(y)
        x, y = y, x + y

    def tdiv(a, b):
        q = abs(a) // abs(b)
        return -q if (a < 0) != (b < 0) else q
    for v in (-7, 7):
        q = tdiv(v, 3)
        out.append(q)
        out.append(v - q * 3)
    out.append(0x123456789ABCDEF >> 12)
    out.append(-4096 >> 4)
    out.append(5 << 40)
    out += [0xF0F0 & 0x0FF0, 0xF0F0 | 0x0FF0, 0xF0F0 ^ 0x0FF0]
    out += [5, 1, 2 ** 62 + 12345]
    return "".join(f"{v}\n" for v in out)


def main():
    run = runner()
    if run is None:
        print("skip arm64 asm: no arm64 host and no qemu-aarch64 found")
        return 0
    fails = 0
    cases = [("basic", program_basic(), expected_basic(), 0)]
    with tempfile.TemporaryDirectory(prefix="hs-arm64.") as d:
        for name, code, want, rc in cases:
            path = os.path.join(d, name)
            with open(path, "wb") as f:
                f.write(arm64.elf_exec(code))
            os.chmod(path, 0o755)
            r = subprocess.run(run + [path], capture_output=True, timeout=60)
            got = r.stdout.decode()
            if got != want or r.returncode != rc:
                print(f"FAIL {name}: rc {r.returncode}\n--- got ---\n{got}\n--- want ---\n{want}\n{r.stderr.decode()}")
                fails += 1
            else:
                print(f"ok   {name}")
    if fails:
        return 1
    print(f"{len(cases)}/{len(cases)} arm64 asm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
