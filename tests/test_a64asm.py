#!/usr/bin/env python3
"""selfhost/a64/asm.holy (AArch64 assembler in hs) must emit exactly the bytes
of a64shim.py's Asm for the shared op subset: every register pair, memory
forms, immediate forms, float ops, labels/fixups, data."""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import a64shim  # noqa: E402

REGS = list(a64shim.REGMAP)[:16]
DISPS = [0, 8, -8, 127, 128, -128, -129, 1000, -70000, 4095, 4096, 32760]
lines = []

def L(*w):
    lines.append(" ".join(str(x) for x in w))

for r in REGS:
    L("push_r", r); L("pop_r", r)
    for op in ("not_r", "neg_r", "idiv_r", "div_r", "shl_cl", "shr_cl", "sar_cl"):
        if op in ("idiv_r", "div_r") and r in ("rax", "rdx"):
            continue  # a64shim.div_r forbids rax/rdx (quotient/remainder regs)
        L(op, r)
    for imm in (0, 1, 63):
        for op in ("shl_ri8", "shr_ri8", "sar_ri8"):
            L(op, r, imm)
    for imm in (0, 5, -5, 100000, -100000):
        for op in ("mov_ri32", "add_ri32", "sub_ri32", "cmp_ri32", "and_ri32"):
            L(op, r, imm)
    for imm in (0, 1, -1, 4294967296, 65535, 65536, 0x1234567890AB):
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
                    L("movzx_rm8x", r, b, ix, sc, d)
for x in range(8):
    for y in range(8):
        for op in ("addsd", "subsd", "mulsd", "divsd", "ucomisd"):
            L(op, x, y)
    for r in REGS:
        L("cvtsi2sd", x, r); L("movq_xr", x, r)
        L("cvttsd2si", r, x); L("movq_rx", r, x)
for r in REGS:
    for s in ("rax", "r9", "r13"):
        L("bsr_rr", r, s)
    for imm in (0, 1, 127, -1):
        L("or_ri32", r, imm)
    for imm in (0, 7, -3, 100000):
        L("xor_ri32", r, imm); L("adc_ri32", r, imm)
    L("mul_r", r)
for b in REGS:
    for d in DISPS:
        for x in range(0, 16, 5):
            L("movq_xm", x % 8, b, d)
        L("movzx_eax_m8", b, d)
        L("jmp_m", b, d)
        L("push_m", b, d)
        L("mov_mr8", b, 3, d)
for b in ("rax", "r9", "r13"):
    for ix in ("rcx", "r10"):
        L("mov_mrx", b, ix, 8, 40, "rdx")
        L("movzx_eax_mx", b, ix, 1, 300)
L("call_r11"); L("call_rax"); L("cqo"); L("nop")
L("movzx_eax_al"); L("movzx_edx_mx", "rax", "rcx", 4, 9)
L("test_al_imm8", 7)
L("xchg_rip", "rcx", "dd"); L("inc_mrip", "dd"); L("dec_mrip", "dd")
L("data_label", "dd"); L("data_qword", -5); L("data_qword", 1 << 40)
L("lea_rip", "rcx", "dd")
for cc in ("e", "ne", "b", "ae", "s", "ns", "l", "ge", "le", "g", "o", "no", "a", "be"):
    L("setcc_al", cc)
    L("jcc", cc, "back")
    L("jcc", cc, "fwd")
L("ucomisd", 0, 1)
for cc in ("e", "ne", "b", "ae", "be", "a", "p", "np"):
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
L("ret"); L("syscall")
L("fmod_trunc_m24"); L("repe_cmpsb")
L("label", "fwd")
L("ret")

def py_asm():
    a = a64shim.Asm()
    for ln in lines:
        w = ln.split()
        op, args = w[0], w[1:]
        conv = [int(x) if x.lstrip("-").isdigit() else x for x in args]
        getattr(a, op if op != "label" else "label")(*conv)
    return a.resolve(0x400000, 0x500000)

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "s.txt")
    open(p, "w").write("\n".join(lines) + "\n")
    env = dict(os.environ)
    env["HSPATH"] = os.pathsep.join([os.path.join(ROOT, "selfhost", "a64"),
                                     os.path.join(ROOT, "selfhost")])
    r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "run",
                        os.path.join(ROOT, "selfhost", "a64", "asm_run.holy"),
                        "--backend", "interp", p], capture_output=True, text=True, env=env)
want = py_asm().hex()
got = r.stdout.strip()
ok = r.returncode == 0 and got == want
if not ok:
    print("FAIL a64/asm.holy vs a64shim.py", r.returncode, r.stderr[-300:])
    n = next((i for i in range(min(len(got), len(want))) if got[i] != want[i]), None)
    print("first diff at hex offset", n, len(got), len(want))
else:
    print(f"ok   a64/asm.holy == a64shim.py on {len(lines)} instructions ({len(want) // 2} bytes)")
print("1/1 passed" if ok else "0/1 passed")
sys.exit(0 if ok else 1)
