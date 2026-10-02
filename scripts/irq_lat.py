#!/usr/bin/env python3
"""Measure timer-interrupt delivery latency with zero libc/gcc.

Builds a static ELF (via x64.py) that installs a SIGALRM handler recording
rdtsc on every fire (1ms interval, N samples), then prints raw TSC deltas.
Run with: python3 scripts/irq_lat.py [N=1000] [interval_us=1000]
"""
import os
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from x64 import Asm, link_elf

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
USEC = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

a = Asm()

# ---------- data ----------
a.data_label("ticks")
a.data_qword(0)          # sample count
a.data_label("buf")      # N x u64 tsc samples (16MB arena not needed; fixed)
a.data_bytes(b"\0" * (8 * N))
a.data_label("pbuf")
a.data_bytes(b"\0" * 32)
a.data_label("pbuf_e")

# ---------- restorer for SA_RESTORER ----------
a.label("restorer")
a.mov_ri32("rax", 15)  # rt_sigreturn
a.syscall()

# ---------- SIGALRM handler: ticks[i++] = rdtsc ----------
a.label("handler")
for r in ("rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"):
    a.push_r(r)
a.code += bytes([0x0F, 0x31])  # rdtsc -> edx:eax
a.mov_rr("rcx", "rdx")
a.code += bytes([0x48, 0xC1, 0xE1, 0x20])  # shl rcx, 32
a.or_rr("rcx", "rax")  # rcx = full tsc
a.lea_rip("rax", "ticks")
a.mov_rm("rdx", "rax", 0)
a.cmp_ri32("rdx", N)
lab_full = "hfull"
a.jcc("ae", lab_full)
# buf[rdx] = rcx
a.lea_rip("rax", "buf")
# store: need base+idx*8 -> use mov_mrx
a.mov_mrx("rax", "rdx", 8, 0, "rcx")
a.lea_rip("rax", "ticks")
a.mov_rm("rdx", "rax", 0)
a.add_ri32("rdx", 1)
a.lea_rip("rax", "ticks")
a.mov_mr("rax", "rdx", 0)
a.label(lab_full)
for r in ("r11", "r10", "r9", "r8", "rdi", "rsi", "rdx", "rcx", "rax"):
    a.pop_r(r)
a.ret()

# ---------- print_u64 in rax (clobbers rcx rdx rsi rdi r8) ----------
a.label("print_u64")
a.lea_rip("rsi", "pbuf_e")
a.test_rr("rax", "rax")
lab_nz, lab_lp, lab_dn = "pnz", "plp", "pdn"
a.jcc("ne", lab_nz)
a.sub_ri32("rsi", 1)
a.mov_ri32("rax", 48)
a.mov_mr8("rsi", 0, 0)
a.jmp(lab_dn)
a.label(lab_nz)
a.label(lab_lp)
a.mov_ri32("r8", 10)
a.mov_ri32("rdx", 0)
a.div_r("r8")
a.add_ri8("rdx", 48)
a.push_r("rax")
a.mov_rr("rax", "rdx")
a.sub_ri32("rsi", 1)
a.mov_mr8("rsi", 0, 0)
a.pop_r("rax")
a.test_rr("rax", "rax")
a.jcc("ne", lab_lp)
a.label(lab_dn)
a.push_r("rsi")
a.lea_rip("rcx", "pbuf_e")
a.pop_r("rsi")
a.sub_rr("rcx", "rsi")
a.mov_rr("rdx", "rcx")
a.mov_ri32("rdi", 1)
a.mov_ri32("rax", 1)
a.syscall()
a.ret()

# ---------- _start ----------
a.label("_start")
# sigaction(SIGALRM=14, {handler, SA_RESTORER, restorer, mask=0})
# struct sigaction 32B on stack
a.sub_ri32("rsp", 32)
a.lea_rip("rax", "handler")
a.mov_mr("rsp", "rax", 0)
a.mov_ri32("rax", 0x04000000)
a.mov_mr("rsp", "rax", 8)
a.lea_rip("rax", "restorer")
a.mov_mr("rsp", "rax", 16)
a.mov_ri32("rax", 0)
a.mov_mr("rsp", "rax", 24)
a.mov_rr("rsi", "rsp")
a.mov_ri32("rdi", 14)
a.mov_ri32("rdx", 0)
a.mov_ri32("r10", 8)
a.mov_ri32("rax", 13)  # rt_sigaction
a.syscall()
a.add_ri32("rsp", 32)
# setitimer(ITIMER_REAL=0, {interval, value}, NULL)
a.sub_ri32("rsp", 32)
a.mov_ri32("rax", 0)
for off in (0, 8, 16, 24):
    a.mov_mr("rsp", "rax", off)
a.mov_ri32("rax", USEC)
a.mov_mr("rsp", "rax", 8)   # interval usec
a.mov_mr("rsp", "rax", 24)  # value usec
a.mov_rr("rsi", "rsp")
a.mov_ri32("rdi", 0)
a.mov_ri32("rdx", 0)
a.mov_ri32("rax", 38)  # setitimer
a.syscall()
a.add_ri32("rsp", 32)
# spin until N samples (hlt to save power? pause loop)
a.label("spin")
a.lea_rip("rax", "ticks")
a.mov_rm("rax", "rax", 0)
a.cmp_ri32("rax", N)
a.jcc("b", "spin")
# print deltas buf[1]-buf[0], ... as decimal lines
a.mov_ri32("rbx", 1)
a.label("ploop")
a.cmp_ri32("rbx", N)
a.jcc("ae", "pdone")
a.lea_rip("rax", "buf")
a.mov_rmx("rcx", "rax", "rbx", 8, 0)  # buf[i]
a.mov_rmx("rdx", "rax", "rbx", 8, -8)  # buf[i-1]
a.sub_rr("rcx", "rdx")
a.push_r("rbx")
a.push_r("rcx")
a.call("print_u64_args")  # custom: value on stack, prints + newline
a.add_ri32("rsp", 8)
a.pop_r("rbx")
a.add_ri32("rbx", 1)
a.jmp("ploop")
a.label("pdone")
a.mov_ri32("rdi", 0)
a.mov_ri32("rax", 60)
a.syscall()

# print_u64_args: [rsp+8] = value -> decimal + newline
a.label("print_u64_args")
a.mov_rm("rax", "rsp", 8)
a.push_r("rax")
a.call("print_u64")
a.add_ri32("rsp", 8)
a.lea_rip("rsi", "nl_")
a.mov_ri32("rdx", 1)
a.mov_ri32("rdi", 1)
a.mov_ri32("rax", 1)
a.syscall()
a.ret()
a.label("nl_")
a.code += b"\n"

from x64 import layout, pack

lo = layout(len(a.code), len(a.data))
code = a.resolve(lo["text_vaddr"], lo["data_vaddr"])
img = pack(code, bytes(a.data), a.labels["_start"], lo)
out = "/tmp/opencode/irq_lat.elf"
open(out, "wb").write(img)
os.chmod(out, 0o755)
print(f"built {out} ({len(img)} bytes)", file=sys.stderr)
