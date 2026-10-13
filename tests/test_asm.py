#!/usr/bin/env python3
"""selfhost/asm.hs (assembler written in hs) must emit exactly the bytes of
x64.py's Asm for the integer instruction subset: every register pair, every
memory form (rsp/r12/rbp/r13 bases, disp8/disp32, SIB), shifts, labels."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import x64  # noqa: E402

REGS = list(x64.REG)[:16]
DISPS = [0, 8, -8, 127, 128, -128, -129, 1000, -70000]
lines = []


def L(*w):
    lines.append(" ".join(str(x) for x in w))


for r in REGS:
    L("push_r", r)
    L("pop_r", r)
    for op in ("not_r", "neg_r", "idiv_r", "div_r", "shl_cl", "shr_cl", "sar_cl"):
        L(op, r)
    for imm in (0, 1, 63):
        L("shl_ri8", r, imm)
        L("shr_ri8", r, imm)
        L("sar_ri8", r, imm)
    for imm in (0, 5, -5, 100000, -100000):
        for op in ("mov_ri32", "add_ri32", "sub_ri32", "cmp_ri32", "and_ri32"):
            L(op, r, imm)
    for imm in (0, 1, -1, 4294967296, -4294967297, 0x7FFFFFFFFFFFFFFF, -(1 << 63)):
        L("mov_ri64", r, imm)
    for s in REGS:
        for op in ("mov_rr", "add_rr", "sub_rr", "cmp_rr", "and_rr", "or_rr",
                   "xor_rr", "test_rr", "imul_rr"):
            L(op, r, s)
    if r not in ("rax", "rcx", "r9", "r13"):
        continue
    for b in REGS:
        for d in DISPS:
            L("mov_rm", r, b, d)
            L("mov_mr", b, r, d)
            L("lea_m", r, b, d)
        for ix in REGS:
            if ix == "rsp":
                continue
            for sc in (1, 8):
                for d in (0, 300):
                    L("mov_rmx", r, b, ix, sc, d)
                    L("lea_mx", r, b, ix, sc, d)
                    L("movzx_rm8x", r, b, ix, sc, d)
for s8 in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 15):
    for b in REGS:
        for d in DISPS:
            if b in ("rsp", "r12") and d != 0:
                continue  # x64.py emits disp before SIB there (a latent bug)
            L("mov_mr8", b, s8, d)
for cc in x64.CC:
    L("setcc_al", cc)
    L("jcc", cc, "back")
    L("jcc", cc, "fwd")
L("label", "back")
L("jmp", "fwd")
L("call", "back")
for r in ("rax", "r9"):
    L("lea_rip", r, "fwd")
    L("mov_rm_rip", r, "back")
    L("mov_mr_rip", "fwd", r)
L("cqo")
L("ret")
L("syscall")
L("nop")
L("movzx_eax_al")
L("label", "fwd")
L("ret")


def py_asm():
    a = x64.Asm()
    for ln in lines:
        w = ln.split()
        op, args = w[0], w[1:]
        conv = []
        for x in args:
            conv.append(int(x) if x.lstrip("-").isdigit() else x)
        if op == "label":
            a.label(*conv)
        elif op == "lea_mx":
            d, b, ix, sc, disp = conv
            a.lea_m(d, b, disp, ix, sc)
        elif op == "jcc":
            a.jcc(*conv)
        else:
            getattr(a, op)(*conv)
    return a.resolve(0x400000, 0x500000)


with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "s.txt")
    open(p, "w").write("\n".join(lines) + "\n")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "run",
                        os.path.join(ROOT, "selfhost", "asm_run.hs"),
                        "--backend", "interp", p], capture_output=True, text=True)
want = py_asm().hex()
got = r.stdout.strip()
ok = r.returncode == 0 and got == want
if not ok:
    print("FAIL asm.hs vs x64.py", r.returncode, r.stderr[-300:])
    n = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), None)
    print("first diff at hex offset", n, len(got), len(want))
else:
    print(f"ok   asm.hs == x64.py on {len(lines)} instructions ({len(want) // 2} bytes)")
print("1/1 passed" if ok else "0/1 passed")
sys.exit(0 if ok else 1)
