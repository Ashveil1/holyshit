#!/usr/bin/env python3
"""a64shim: x86-64 `x64.Asm` API implemented on top of A64 encodings.

The x64 backend (irx64/x64gen/gcrt) drives an assembler through a small
method API. This class implements the same names and emits AArch64, so the
existing code generator, runtime and GC retarget without a rewrite.

Model (see docs/portability.md):
  * x86 registers map onto x0..x28 (REGMAP). rsp is EMULATED in x28: push/pop,
    call/ret and rsp-relative accesses all use x28, so stack layout, frame
    walking and GC stack scanning stay identical to x86. Hardware sp is only
    read once in _start.
  * x16/x17 are shim scratch. x24..x27 save argument registers in the
    syscall stub. x30 is clobbered by the syscall stub only.
  * Flags: ALU ops use flag-setting forms. Logic ops follow with cmp #0 so
    Z/N match and C=1 (x86 CF=0). jcc maps x86 conditions on the kind of the
    last flag-setting op (sub/add/imul/fp).
  * call pushes the return address on the emulated stack; ret pops it.
  * syscall: x86 numbers are translated to arm64 at run time by a small stub.
"""
import struct

REGMAP = {"rax": 9, "rcx": 10, "rdx": 2, "rbx": 19, "rsp": 28, "rbp": 29,
          "rsi": 1, "rdi": 0, "r8": 4, "r9": 5, "r10": 3, "r11": 11,
          "r12": 20, "r13": 21, "r14": 22, "r15": 23,
          "ax": 9, "cx": 10, "dx": 2, "bx": 19, "sp": 28, "bp": 29,
          "si": 1, "di": 0}
NUM2NAME = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
            "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
T0, T1, XZR, SPR, LR = 16, 17, 31, 28, 30
M64 = (1 << 64) - 1

# x86 cc -> arm cond (default / after add / after imul / after fp compare)
C_SUB = {"e": 0, "ne": 1, "b": 3, "ae": 2, "be": 9, "a": 8, "s": 4, "ns": 5,
         "o": 6, "no": 7, "l": 11, "ge": 10, "le": 13, "g": 12}
C_ADD = dict(C_SUB, b=2, ae=3)
C_MUL = dict(C_SUB, o=1, no=0)
C_FP = dict(C_SUB, p=6, np=7, b=11, be=13, a=12, ae=10)


def R(r):
    if isinstance(r, int):
        r = NUM2NAME[r]
    return REGMAP[r]


class Asm:
    UC_RSP_OFF = 432       # ucontext_t.uc_mcontext.sp on arm64 Linux
    ARCH = "arm64"

    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.fixups = []        # (pos, label, kind)
        self.data = bytearray()
        self.data_labels = {}
        self.kind = "sub"
        self._sys_done = False
        self._n = 0

    # -- plumbing --
    def pos(self):
        return len(self.code)

    def w(self, word):
        assert len(self.code) % 4 == 0, "misaligned code (raw bytes mid-code?)"
        self.code += struct.pack("<I", word & 0xFFFFFFFF)

    def label(self, name):
        if name in self.labels:
            raise ValueError(f"dup label {name}")
        self.labels[name] = len(self.code)
        if name == "_start":
            self.w(0x910003E0 | SPR)        # mov x28, sp

    def tmp(self, p="L"):
        self._n += 1
        return f".{p}{self._n}"

    # -- encodings --
    def mov_x(self, d, s):
        self.w(0xAA0003E0 | (s << 16) | d)

    def movimm(self, d, v):
        v &= M64
        if v == 0:
            self.w(0xD2800000 | d)
            return
        hw = [(v >> (16 * i)) & 0xFFFF for i in range(4)]
        nz = [i for i in range(4) if hw[i]]
        ones = [i for i in range(4) if hw[i] != 0xFFFF]
        if len(ones) < len(nz):               # movn form
            first = ones[0] if ones else 0
            self.w(0x92800000 | (first << 21) | (((~hw[first]) & 0xFFFF) << 5) | d)
            for i in ones[1:]:
                self.w(0xF2800000 | (i << 21) | (hw[i] << 5) | d)
        else:
            self.w(0xD2800000 | (nz[0] << 21) | (hw[nz[0]] << 5) | d)
            for i in nz[1:]:
                self.w(0xF2800000 | (i << 21) | (hw[i] << 5) | d)

    def alu_rrr(self, base, d, n, m):
        self.w(base | (m << 16) | (n << 5) | d)

    def addi(self, d, n, imm):            # imm 0..4095
        self.w(0x91000000 | (imm << 10) | (n << 5) | d)

    def subi(self, d, n, imm):
        self.w(0xD1000000 | (imm << 10) | (n << 5) | d)

    def cmpz(self, r):                    # logic-op flags: Z/N from r, C=1, V=0
        self.w(0xF1000000 | (0 << 10) | (r << 5) | XZR)

    def ldst(self, op, size, rt, rn, off):
        """op: 'ld'|'st'; size 1|8 (bytes). off arbitrary."""
        if off >= 0 and off % size == 0 and off // size < 4096:
            base = {("ld", 8): 0xF9400000, ("st", 8): 0xF9000000,
                    ("ld", 1): 0x39400000, ("st", 1): 0x39000000}[(op, size)]
            self.w(base | ((off // size) << 10) | (rn << 5) | rt)
        elif -256 <= off <= 255:
            base = {("ld", 8): 0xF8400000, ("st", 8): 0xF8000000,
                    ("ld", 1): 0x38400000, ("st", 1): 0x38000000}[(op, size)]
            self.w(base | ((off & 0x1FF) << 12) | (rn << 5) | rt)
        else:
            self.movimm(T1, off)
            self.alu_rrr(0x8B000000, T1, rn, T1)
            self.ldst(op, size, rt, T1, 0)

    def ea(self, base, disp, index=None, scale=1):
        """-> (reg, off) addressing a memory operand."""
        b = R(base)
        if index is None:
            return b, disp
        sh = {1: 0, 2: 1, 4: 2, 8: 3}[scale]
        # add x17, base, index lsl sh
        self.w(0x8B000000 | (R(index) << 16) | (sh << 10) | (b << 5) | T1)
        return T1, disp

    # -- moves --
    def mov_rr(self, d, s):
        self.mov_x(R(d), R(s))

    def mov_ri32(self, d, imm):
        self.movimm(R(d), imm)

    def mov_ri64(self, d, imm):
        self.movimm(R(d), imm)

    def mov_ri16(self, d, imm):
        self.movimm(R(d), imm)

    def mov_rm(self, d, base, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("ld", 8, R(d), rn, off)

    def mov_rmx(self, d, base, index, scale, disp=0):
        rn, off = self.ea(base, disp, index, scale)
        self.ldst("ld", 8, R(d), rn, off)

    def mov_mr(self, base, s, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("st", 8, R(s), rn, off)

    def mov_mrx(self, base, index, scale, disp, s):
        rn, off = self.ea(base, disp, index, scale)
        self.ldst("st", 8, R(s), rn, off)

    def mov_mr8(self, base, s8, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("st", 1, R(s8), rn, off)

    def movzx_eax_m8(self, base, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("ld", 1, 9, rn, off)

    def movzx_rm8x(self, dst, base, index, scale, disp=0):
        rn, off = self.ea(base, disp, index, scale)
        self.ldst("ld", 1, R(dst), rn, off)

    def movzx_eax_mx(self, base, index, scale, disp=0):
        self.movzx_rm8x("rax", base, index, scale, disp)

    def movzx_edx_mx(self, base, index, scale, disp=0):
        self.movzx_rm8x("rdx", base, index, scale, disp)

    def movzx_eax_al(self):
        self.w(0xD3401C00 | (9 << 5) | 9)

    def lea_m(self, d, base, disp=0, index=None, scale=1):
        b = R(base)
        dd = R(d)
        if index is not None:
            sh = {1: 0, 2: 1, 4: 2, 8: 3}[scale]
            self.w(0x8B000000 | (R(index) << 16) | (sh << 10) | (b << 5) | dd)
            b = dd
        if disp == 0:
            if b != dd:
                self.mov_x(dd, b)
        elif 0 < disp < 4096:
            self.addi(dd, b, disp)
        elif -4096 < disp < 0:
            self.subi(dd, b, -disp)
        else:
            self.movimm(T0, disp)
            self.alu_rrr(0x8B000000, dd, b, T0)

    # rip-relative: adrp+add -> reg
    def _rip(self, reg, label):
        self.fixups.append((len(self.code), label, "adrp"))
        self.w(0x90000000 | reg)
        self.w(0x91000000 | (reg << 5) | reg)

    def lea_rip(self, d, label):
        self._rip(R(d), label)

    def mov_rm_rip(self, d, label):
        self._rip(T0, label)
        self.ldst("ld", 8, R(d), T0, 0)

    def mov_mr_rip(self, label, s):
        self._rip(T0, label)
        self.ldst("st", 8, R(s), T0, 0)

    def xchg_rip(self, d, label):
        self._rip(T0, label)
        self.ldst("ld", 8, T1, T0, 0)
        self.ldst("st", 8, R(d), T0, 0)
        self.mov_x(R(d), T1)

    def inc_mrip(self, label):
        self._rip(T0, label)
        self.ldst("ld", 8, T1, T0, 0)
        self.w(0xB1000400 | (T1 << 5) | T1)    # adds x17,x17,#1
        self.ldst("st", 8, T1, T0, 0)
        self.kind = "add"

    def dec_mrip(self, label):
        self._rip(T0, label)
        self.ldst("ld", 8, T1, T0, 0)
        self.w(0xF1000400 | (T1 << 5) | T1)    # subs x17,x17,#1
        self.ldst("st", 8, T1, T0, 0)
        self.kind = "sub"

    # -- stack --
    def push_r(self, r):
        self.w(0xF8000C00 | ((-8 & 0x1FF) << 12) | (SPR << 5) | R(r))   # str r,[x28,#-8]!

    def pop_r(self, r):
        self.w(0xF8400400 | (8 << 12) | (SPR << 5) | R(r))             # ldr r,[x28],#8

    def push_m(self, base, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("ld", 8, T0, rn, off)
        self.push_r_raw(T0)

    def push_r_raw(self, n):
        self.w(0xF8000C00 | ((-8 & 0x1FF) << 12) | (SPR << 5) | n)

    # -- ALU --
    def _rr(self, base, d, s):
        self.alu_rrr(base, R(d), R(d), R(s))

    def add_rr(self, d, s):
        self._rr(0xAB000000, d, s)
        self.kind = "add"

    def sub_rr(self, d, s):
        self._rr(0xEB000000, d, s)
        self.kind = "sub"

    def cmp_rr(self, d, s):
        self.alu_rrr(0xEB000000, XZR, R(d), R(s))
        self.kind = "sub"

    def adc_rr(self, d, s):
        self._rr(0xBA000000, d, s)
        self.kind = "add"

    def _logic_rr(self, base, d, s):
        self._rr(base, d, s)
        self.cmpz(R(d))
        self.kind = "sub"

    def and_rr(self, d, s):
        self._logic_rr(0x8A000000, d, s)

    def or_rr(self, d, s):
        self._logic_rr(0xAA000000, d, s)

    def xor_rr(self, d, s):
        self._logic_rr(0xCA000000, d, s)

    def test_rr(self, d, s):
        self.alu_rrr(0x8A000000, T0, R(d), R(s))
        self.cmpz(T0)
        self.kind = "sub"

    def _imm_alu(self, base, d, imm, flags_add=False):
        self.movimm(T0, imm)
        self.alu_rrr(base, R(d), R(d), T0)

    def add_ri32(self, d, imm):
        if 0 <= imm < 4096:
            self.w(0xB1000000 | (imm << 10) | (R(d) << 5) | R(d))
        else:
            self._imm_alu(0xAB000000, d, imm)
        self.kind = "add"

    add_ri8 = add_ri32

    def sub_ri32(self, d, imm):
        if 0 <= imm < 4096:
            self.w(0xF1000000 | (imm << 10) | (R(d) << 5) | R(d))
        else:
            self._imm_alu(0xEB000000, d, imm)
        self.kind = "sub"

    def cmp_ri32(self, d, imm):
        if 0 <= imm < 4096:
            self.w(0xF1000000 | (imm << 10) | (R(d) << 5) | XZR)
        else:
            self.movimm(T0, imm)
            self.alu_rrr(0xEB000000, XZR, R(d), T0)
        self.kind = "sub"

    def adc_ri32(self, d, imm):
        self.movimm(T0, imm)
        self.alu_rrr(0xBA000000, R(d), R(d), T0)
        self.kind = "add"

    def _logic_ri(self, base, d, imm):
        self.movimm(T0, imm)
        self.alu_rrr(base, R(d), R(d), T0)
        self.cmpz(R(d))
        self.kind = "sub"

    def and_ri32(self, d, imm):
        self._logic_ri(0x8A000000, d, imm)

    def or_ri32(self, d, imm):
        self._logic_ri(0xAA000000, d, imm)

    or_ri8 = or_ri32

    def xor_ri32(self, d, imm):
        self._logic_ri(0xCA000000, d, imm)

    def test_al_imm8(self, imm):
        self.movimm(T0, imm & 0xFF)
        self.alu_rrr(0x8A000000, T0, 9, T0)
        self.cmpz(T0)
        self.kind = "sub"

    def imul_rr(self, d, s):
        dd, ss = R(d), R(s)
        self.alu_rrr(0x9B407C00, T0, dd, ss)       # smulh x16
        self.alu_rrr(0x9B007C00, dd, dd, ss)       # mul
        self.w(0xEB800000 | (dd << 16) | (63 << 10) | (T0 << 5) | XZR)   # cmp hi, lo asr 63
        self.kind = "imul"

    def mul_r(self, r):
        self.alu_rrr(0x9BC07C00, 2, 9, R(r))       # umulh rdx
        self.alu_rrr(0x9B007C00, 9, 9, R(r))

    def cqo(self):
        self.w(0x937FFC00 | (9 << 5) | 2)          # asr x2, x9, #63

    def idiv_r(self, r):
        self.alu_rrr(0x9AC00C00, T0, 9, R(r))      # sdiv x16
        self.w(0x9B008000 | (R(r) << 16) | (9 << 10) | (T0 << 5) | 2)  # msub rdx = rax - q*r
        self.mov_x(9, T0)

    def div_r(self, r):
        self.alu_rrr(0x9AC00800, T0, 9, R(r))      # udiv
        self.w(0x9B008000 | (R(r) << 16) | (9 << 10) | (T0 << 5) | 2)
        self.mov_x(9, T0)

    def bsr_rr(self, d, s):
        self.w(0xDAC01000 | (R(s) << 5) | T0)      # clz x16
        self.movimm(T1, 63)
        self.alu_rrr(0xCB000000, R(d), T1, T0)

    def not_r(self, r):
        self.w(0xAA2003E0 | (R(r) << 16) | R(r))

    not_rr = not_r

    def neg_r(self, r):
        self.alu_rrr(0xEB000000, R(r), XZR, R(r))
        self.kind = "sub"

    def shl_ri8(self, d, n):
        self.w(0xD3400000 | (((-n) % 64) << 16) | ((63 - n) << 10) | (R(d) << 5) | R(d))

    def shr_ri8(self, d, n):
        self.w(0xD340FC00 | (n << 16) | (R(d) << 5) | R(d))

    def sar_ri8(self, d, n):
        self.w(0x9340FC00 | (n << 16) | (R(d) << 5) | R(d))

    def shl_cl(self, d):
        self.alu_rrr(0x9AC02000, R(d), R(d), 10)

    def shr_cl(self, d):
        self.alu_rrr(0x9AC02400, R(d), R(d), 10)

    def sar_cl(self, d):
        self.alu_rrr(0x9AC02800, R(d), R(d), 10)

    def bc(self, cond, label):
        self.fixups.append((len(self.code), label, "bcond19"))
        self.w(0x54000000 | cond)

    def fmod_trunc_m24(self):
        """[rbp-24] = trunc-remainder of [rbp-8] by [rbp-16] (exact, like fprem)."""
        L = {k: self.tmp("fm") for k in ("loop", "inner", "idone", "done", "nan", "pos", "st")}
        def ldur_d(d, off): self.w(0xFC400000 | ((off & 0x1FF) << 12) | (29 << 5) | d)
        ldur_d(16, -8)
        ldur_d(17, -16)
        self.w(0x1E60C000 | (16 << 5) | 18)          # fabs d18,d16
        self.w(0x1E60C000 | (17 << 5) | 17)          # fabs d17,d17
        self.w(0x1E602008 | (17 << 5))               # fcmp d17,#0
        self.bc(0, L["nan"])
        self.w(0x1E603800 | (18 << 16) | (18 << 5) | 21)   # fsub d21,d18,d18 (nan if inf/nan)
        self.w(0x1E602000 | (21 << 16) | (21 << 5))        # fcmp d21,d21
        self.bc(6, L["nan"])                               # unordered
        self.labels[L["loop"]] = len(self.code)
        self.w(0x1E602000 | (17 << 16) | (18 << 5))        # fcmp d18,d17
        self.bc(4, L["done"])                              # x < y
        self.w(0x1E604000 | (17 << 5) | 19)                # fmov d19,d17
        self.labels[L["inner"]] = len(self.code)
        self.w(0x1E602800 | (19 << 16) | (19 << 5) | 20)   # fadd d20,d19,d19
        self.w(0x1E602000 | (18 << 16) | (20 << 5))        # fcmp d20,d18
        self.bc(12, L["idone"])                            # 2t > x
        self.w(0x1E604000 | (20 << 5) | 19)                # fmov d19,d20
        self.fixups.append((len(self.code), L["inner"], "b26"))
        self.w(0x14000000)
        self.labels[L["idone"]] = len(self.code)
        self.w(0x1E603800 | (19 << 16) | (18 << 5) | 18)   # fsub d18,d18,d19
        self.fixups.append((len(self.code), L["loop"], "b26"))
        self.w(0x14000000)
        self.labels[L["nan"]] = len(self.code)
        self.movimm(T0, 0x7FF8000000000000)
        self.w(0x9E670000 | (T0 << 5) | 18)                # fmov d18,x16
        self.fixups.append((len(self.code), L["st"], "b26"))
        self.w(0x14000000)
        self.labels[L["done"]] = len(self.code)
        self.w(0x9E660000 | (16 << 5) | T0)                # fmov x16,d16
        self.fixups.append((len(self.code), L["st"], "tbz"))
        self.w(0xB6F80000 | T0)                            # tbz x16,#63,st
        self.w(0x1E614000 | (18 << 5) | 18)                # fneg d18,d18
        self.labels[L["st"]] = len(self.code)
        self.w(0xFC000000 | ((-24 & 0x1FF) << 12) | (29 << 5) | 18)   # stur d18,[x29,#-24]

    # -- fixed byte forms --
    def repe_cmpsb(self):
        loop, out = self.tmp("rc"), self.tmp("ro")
        self.w(0xEB1F03FF)                                       # cmp xzr,xzr (Z=1)
        self.labels[loop] = len(self.code)
        self.fixups.append((len(self.code), out, "cbz19"))
        self.w(0xB4000000 | 10)                                  # cbz rcx, out
        self.w(0x38401400 | (0 << 5) | T0)                       # ldrb w16,[rdi],#1
        self.w(0x38401400 | (1 << 5) | T1)                       # ldrb w17,[rsi],#1
        self.subi(10, 10, 1)
        self.w(0x6B11021F | (0 << 0))                            # cmp w16,w17
        self.fixups.append((len(self.code), loop, "bcond19"))
        self.w(0x54000000)                                       # b.eq loop
        self.labels[out] = len(self.code)
        self.kind = "sub"

    def xor_rax_8(self):
        self.xor_ri32("rax", 8)

    def ld8_rax(self):
        self.ldst("ld", 1, 9, 9, 0)

    def ld32_rax(self):
        self.w(0xB9400000 | (9 << 5) | 9)

    def ld64_rax(self):
        self.ldst("ld", 8, 9, 9, 0)

    def st8_rax_cl(self):
        self.ldst("st", 1, 10, 9, 0)

    def st32_rax_ecx(self):
        self.w(0xB9000000 | (9 << 5) | 10)

    def st64_rax_rcx(self):
        self.ldst("st", 8, 10, 9, 0)

    def cmp_al_dl(self):
        self.w(0xD3481C00 | (9 << 5) | T0)       # lsl x16,x9,#56 (ubfm)
        self.w(0xD3481C00 | (2 << 5) | T1)
        self.alu_rrr(0xEB000000, XZR, T0, T1)
        self.kind = "sub"

    # -- control --
    def jmp(self, label):
        self.fixups.append((len(self.code), label, "b26"))
        self.w(0x14000000)

    def jcc(self, cc, label):
        m = {"sub": C_SUB, "add": C_ADD, "imul": C_MUL, "fp": C_FP}[self.kind]
        c = m[cc]
        self.w(0x54000040 | (c ^ 1))               # b.!cc +8
        self.fixups.append((len(self.code), label, "b26"))
        self.w(0x14000000)

    def call(self, label):
        self.w(0x10000000 | ((12 >> 2) << 5) | T0)  # adr x16,.+12
        self.push_r_raw(T0)
        self.fixups.append((len(self.code), label, "b26"))
        self.w(0x14000000)

    def _call_reg(self, n):
        self.w(0x10000000 | ((12 >> 2) << 5) | T0)
        self.push_r_raw(T0)
        self.w(0xD61F0000 | (n << 5))

    def call_rax(self):
        self._call_reg(9)

    def call_r11(self):
        self._call_reg(11)

    def jmp_r(self, r):
        self.w(0xD61F0000 | (R(r) << 5))

    def jmp_m(self, base, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("ld", 8, T0, rn, off)
        self.w(0xD61F0000 | (T0 << 5))

    def ret(self):
        self.w(0xF8400400 | (8 << 12) | (SPR << 5) | T0)
        self.w(0xD61F0000 | (T0 << 5))

    def nop(self):
        self.w(0xD503201F)

    def setcc_al(self, cc):
        m = {"sub": C_SUB, "add": C_ADD, "imul": C_MUL, "fp": C_FP}[self.kind]
        c = m[cc] ^ 1
        self.w(0x9A9F07E0 | (c << 12) | 9)         # cset x9, cc

    # -- float --
    def movq_xr(self, x, r):
        self.w(0x9E670000 | (R(r) << 5) | x)       # fmov dX, xR

    def movq_rx(self, r, x):
        self.w(0x9E660000 | (x << 5) | R(r))       # fmov xR, dX

    def movq_xm(self, x, base, disp=0):
        rn, off = self.ea(base, disp)
        self.ldst("ld", 8, T0, rn, off)
        self.w(0x9E670000 | (T0 << 5) | x)

    def cvtsi2sd(self, x, r):
        self.w(0x9E620000 | (R(r) << 5) | x)       # scvtf d, x

    def cvttsd2si(self, r, x):
        self.w(0x9E780000 | (x << 5) | R(r))       # fcvtzs x, d

    def ucomisd(self, a, b):
        self.w(0x1E602000 | (b << 16) | (a << 5))  # fcmp da, db
        self.kind = "fp"

    def addsd(self, d, s):
        self.w(0x1E602800 | (s << 16) | (d << 5) | d)

    def subsd(self, d, s):
        self.w(0x1E603800 | (s << 16) | (d << 5) | d)

    def mulsd(self, d, s):
        self.w(0x1E600800 | (s << 16) | (d << 5) | d)

    def divsd(self, d, s):
        self.w(0x1E601800 | (s << 16) | (d << 5) | d)

    # -- syscall: translate x86-64 numbers to arm64 --
    SYS = {0: 63, 1: 64, 3: 57, 8: 62, 9: 222, 11: 215, 12: 214, 13: 134,
           15: 139, 59: 221, 60: 93, 61: 260, 131: 132, 217: 61, 231: 94,
           257: 56}
    SYS_AT = {21: 48, 83: 34}     # path-first calls become *at(AT_FDCWD, ...)

    def syscall(self):
        if not self._sys_done:
            self._sys_done = True
            skip = self.tmp("sk")
            self.jmp(skip)
            self.labels["__a64_sys"] = len(self.code)
            for i in range(4):
                self.mov_x(24 + i, i)
            def entry(nr, body_words):
                self.w(0xF1000000 | (nr << 10) | (9 << 5) | XZR)          # cmp x9,#nr
                self.w(0x54000001 | ((len(body_words) + 2) << 5))        # b.ne past body+jump
                for x in body_words:
                    self.w(x)
                self.fixups.append((len(self.code), "__a64_sysdo", "b26"))
                self.w(0x14000000)
            for x86, a in sorted(self.SYS.items()):
                entry(x86, [0xD2800000 | (a << 5) | 8])
            for x86, a in sorted(self.SYS_AT.items()):
                entry(x86, [0xD2800000 | (a << 5) | 8,
                            0xAA0003E0 | (25 << 16) | 2,                   # x2 = old x1
                            0xAA0003E0 | (24 << 16) | 1,                   # x1 = old x0
                            0x92800000 | (99 << 5)])                       # x0 = -100
            entry(57, [0xD2800000 | (220 << 5) | 8, 0xD2800000 | (17 << 5),
                       0xD2800001, 0xD2800002, 0xD2800003, 0xD2800004])    # fork = clone(SIGCHLD)
            self.w(0x92800000 | (37 << 5) | 9)                             # unknown: -ENOSYS
            self.fixups.append((len(self.code), "__a64_sysret", "b26"))
            self.w(0x14000000)
            self.labels["__a64_sysdo"] = len(self.code)
            self.w(0xD4000001)                                             # svc #0
            self.mov_x(9, 0)
            self.labels["__a64_sysret"] = len(self.code)
            for i in range(4):
                self.mov_x(i, 24 + i)
            self.w(0xD65F03C0)                                             # ret (x30)
            self.labels[skip] = len(self.code)
        self.fixups.append((len(self.code), "__a64_sys", "bl26"))
        self.w(0x94000000)

    def data_label(self, name):
        if name in self.data_labels:
            raise ValueError(f"dup data label {name}")
        self.data_labels[name] = len(self.data)

    def data_qword(self, v=0):
        self.data += struct.pack("<q", v)

    def data_bytes(self, b):
        self.data += b

    def resolve(self, text_vaddr, data_vaddr):
        out = bytearray(self.code)
        for pos, label, kind in self.fixups:
            if label in self.labels:
                tgt = text_vaddr + self.labels[label]
            elif label in self.data_labels:
                tgt = data_vaddr + self.data_labels[label]
            else:
                raise ValueError(f"undefined label {label}")
            pc = text_vaddr + pos
            w = struct.unpack_from("<I", out, pos)[0]
            if kind in ("b26", "bl26"):
                off = (tgt - pc) >> 2
                assert -(1 << 25) <= off < (1 << 25)
                w = (w & 0xFC000000) | (off & 0x3FFFFFF)
                struct.pack_into("<I", out, pos, w)
            elif kind == "tbz":
                off = (tgt - pc) >> 2
                struct.pack_into("<I", out, pos, (w & 0xFFF8001F) | ((off & 0x3FFF) << 5))
            elif kind == "cbz19":
                off = (tgt - pc) >> 2
                struct.pack_into("<I", out, pos, (w & 0xFF00001F) | ((off & 0x7FFFF) << 5))
            elif kind.startswith("bcond19"):
                off = (tgt - pc) >> 2
                struct.pack_into("<I", out, pos, (w & 0xFF00001F) | ((off & 0x7FFFF) << 5))
            elif kind == "adrp":
                pg = ((tgt >> 12) - (pc >> 12)) & 0x1FFFFF
                w = (w & 0x9F00001F) | ((pg & 3) << 29) | ((pg >> 2) << 5)
                struct.pack_into("<I", out, pos, w)
                w2 = struct.unpack_from("<I", out, pos + 4)[0]
                w2 = (w2 & ~(0xFFF << 10)) | ((tgt & 0xFFF) << 10)
                struct.pack_into("<I", out, pos + 4, w2 & 0xFFFFFFFF)
        return bytes(out)
