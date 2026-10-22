#!/usr/bin/env python3
"""A64 (AArch64) assembler and static ELF64 writer for the holyshit arm64 port.

Own encoder, no external assembler. Covers the integer subset the IR lowerer
needs: moves, ALU, shifts, multiply/divide, compare, conditional select,
loads/stores (immediate, register, pair), branches, svc. Registers are x0..x30,
sp and xzr (number 31 by context). Labels resolve in finish().
"""
import struct

SP = 31
XZR = 31
LR = 30
FP = 29

CONDS = {"eq": 0, "ne": 1, "hs": 2, "cs": 2, "lo": 3, "cc": 3, "mi": 4, "pl": 5,
         "vs": 6, "vc": 7, "hi": 8, "ls": 9, "ge": 10, "lt": 11, "gt": 12, "le": 13}


def _check(v, lo, hi, what):
    if not lo <= v <= hi:
        raise ValueError(f"{what} {v} out of range {lo}..{hi}")


class Asm:
    def __init__(self):
        self.words = []
        self.labels = {}
        self.fixups = []   # (word index, label, kind)

    # ---- plumbing
    def pos(self):
        return len(self.words) * 4

    def emit(self, w):
        self.words.append(w & 0xFFFFFFFF)

    def label(self, name):
        if name in self.labels:
            raise ValueError(f"duplicate label {name}")
        self.labels[name] = self.pos()

    def _ref(self, label, kind):
        self.fixups.append((len(self.words), label, kind))

    def finish(self):
        for idx, label, kind in self.fixups:
            if label not in self.labels:
                raise ValueError(f"undefined label {label}")
            off = self.labels[label] - idx * 4
            w = self.words[idx]
            if kind == "b26":       # b, bl
                _check(off % 4 + 0, 0, 0, "branch alignment")
                _check(off >> 2, -(1 << 25), (1 << 25) - 1, "b offset")
                w |= (off >> 2) & 0x3FFFFFF
            elif kind == "b19":     # b.cond, cbz, cbnz
                _check(off >> 2, -(1 << 18), (1 << 18) - 1, "cond offset")
                w |= ((off >> 2) & 0x7FFFF) << 5
            elif kind == "adr":     # adr rd, label (+-1MiB)
                _check(off, -(1 << 20), (1 << 20) - 1, "adr offset")
                w |= ((off & 3) << 29) | (((off >> 2) & 0x7FFFF) << 5)
            else:
                raise ValueError(kind)
            self.words[idx] = w & 0xFFFFFFFF
        return b"".join(struct.pack("<I", w) for w in self.words)

    # ---- moves
    def movz(self, rd, imm16, shift=0):
        _check(imm16, 0, 0xFFFF, "imm16")
        self.emit(0xD2800000 | ((shift // 16) << 21) | (imm16 << 5) | rd)

    def movk(self, rd, imm16, shift=0):
        _check(imm16, 0, 0xFFFF, "imm16")
        self.emit(0xF2800000 | ((shift // 16) << 21) | (imm16 << 5) | rd)

    def movn(self, rd, imm16, shift=0):
        _check(imm16, 0, 0xFFFF, "imm16")
        self.emit(0x92800000 | ((shift // 16) << 21) | (imm16 << 5) | rd)

    def mov_imm(self, rd, value):
        v = value & 0xFFFFFFFFFFFFFFFF
        if value < 0 and value >= -0x10000:
            self.movn(rd, (~value) & 0xFFFF)
            return
        parts = [(v >> s) & 0xFFFF for s in (0, 16, 32, 48)]
        first = True
        for i, p in enumerate(parts):
            if p == 0 and not (first and i == 3):
                continue
            if first:
                self.movz(rd, p, i * 16)
                first = False
            else:
                self.movk(rd, p, i * 16)
        if first:
            self.movz(rd, 0)

    def mov(self, rd, rm):
        if rd == SP or rm == SP:
            self.add_imm(rd, rm, 0)
        else:
            self.orr(rd, XZR, rm)

    # ---- ALU register
    def _alu(self, base, rd, rn, rm, shift=0):
        self.emit(base | (rm << 16) | ((shift & 63) << 10) | (rn << 5) | rd)

    def add(self, rd, rn, rm):  self._alu(0x8B000000, rd, rn, rm)
    def sub(self, rd, rn, rm):  self._alu(0xCB000000, rd, rn, rm)
    def adds(self, rd, rn, rm): self._alu(0xAB000000, rd, rn, rm)
    def subs(self, rd, rn, rm): self._alu(0xEB000000, rd, rn, rm)
    def and_(self, rd, rn, rm): self._alu(0x8A000000, rd, rn, rm)
    def orr(self, rd, rn, rm):  self._alu(0xAA000000, rd, rn, rm)
    def eor(self, rd, rn, rm):  self._alu(0xCA000000, rd, rn, rm)
    def ands(self, rd, rn, rm): self._alu(0xEA000000, rd, rn, rm)
    def cmp(self, rn, rm):      self.subs(XZR, rn, rm)
    def tst(self, rn, rm):      self.ands(XZR, rn, rm)
    def neg(self, rd, rm):      self.sub(rd, XZR, rm)
    def mvn(self, rd, rm):      self._alu(0xAA200000, rd, XZR, rm)

    # ---- ALU immediate (12-bit, optional lsl 12)
    def _alu_imm(self, base, rd, rn, imm):
        sh = 0
        if imm > 0xFFF and imm & 0xFFF == 0 and imm >> 12 <= 0xFFF:
            imm >>= 12
            sh = 1
        _check(imm, 0, 0xFFF, "imm12")
        self.emit(base | (sh << 22) | (imm << 10) | (rn << 5) | rd)

    def add_imm(self, rd, rn, imm):  self._alu_imm(0x91000000, rd, rn, imm)
    def sub_imm(self, rd, rn, imm):  self._alu_imm(0xD1000000, rd, rn, imm)
    def subs_imm(self, rd, rn, imm): self._alu_imm(0xF1000000, rd, rn, imm)
    def adds_imm(self, rd, rn, imm): self._alu_imm(0xB1000000, rd, rn, imm)
    def cmp_imm(self, rn, imm):      self.subs_imm(XZR, rn, imm)

    # ---- shifts, multiply, divide
    def lslv(self, rd, rn, rm): self.emit(0x9AC02000 | (rm << 16) | (rn << 5) | rd)
    def lsrv(self, rd, rn, rm): self.emit(0x9AC02400 | (rm << 16) | (rn << 5) | rd)
    def asrv(self, rd, rn, rm): self.emit(0x9AC02800 | (rm << 16) | (rn << 5) | rd)

    def lsl_imm(self, rd, rn, n):
        _check(n, 0, 63, "shift")
        self.emit(0xD3400000 | (((-n) & 63) << 16) | ((63 - n) << 10) | (rn << 5) | rd)

    def lsr_imm(self, rd, rn, n):
        _check(n, 0, 63, "shift")
        self.emit(0xD340FC00 | (n << 16) | (rn << 5) | rd)

    def asr_imm(self, rd, rn, n):
        _check(n, 0, 63, "shift")
        self.emit(0x9340FC00 | (n << 16) | (rn << 5) | rd)

    def mul(self, rd, rn, rm):   self.emit(0x9B007C00 | (rm << 16) | (rn << 5) | rd)
    def smulh(self, rd, rn, rm): self.emit(0x9B407C00 | (rm << 16) | (rn << 5) | rd)
    def sdiv(self, rd, rn, rm):  self.emit(0x9AC00C00 | (rm << 16) | (rn << 5) | rd)
    def udiv(self, rd, rn, rm):  self.emit(0x9AC00800 | (rm << 16) | (rn << 5) | rd)

    def msub(self, rd, rn, rm, ra):
        self.emit(0x9B008000 | (rm << 16) | (ra << 10) | (rn << 5) | rd)

    def madd(self, rd, rn, rm, ra):
        self.emit(0x9B000000 | (rm << 16) | (ra << 10) | (rn << 5) | rd)

    # ---- conditional
    def csel(self, rd, rn, rm, cond):
        self.emit(0x9A800000 | (rm << 16) | (CONDS[cond] << 12) | (rn << 5) | rd)

    def cset(self, rd, cond):
        inv = CONDS[cond] ^ 1
        self.emit(0x9A9F07E0 | (inv << 12) | rd)

    # ---- loads / stores (unsigned scaled immediate; register offset)
    def _ldst(self, base, rt, rn, off, scale):
        _check(off, 0, 0xFFF * scale, "mem offset")
        if off % scale:
            raise ValueError("unaligned mem offset")
        self.emit(base | ((off // scale) << 10) | (rn << 5) | rt)

    def ldr(self, rt, rn, off=0):  self._ldst(0xF9400000, rt, rn, off, 8)
    def str_(self, rt, rn, off=0): self._ldst(0xF9000000, rt, rn, off, 8)
    def ldrb(self, rt, rn, off=0): self._ldst(0x39400000, rt, rn, off, 1)
    def strb(self, rt, rn, off=0): self._ldst(0x39000000, rt, rn, off, 1)
    def ldrw(self, rt, rn, off=0): self._ldst(0xB9400000, rt, rn, off, 4)
    def strw(self, rt, rn, off=0): self._ldst(0xB9000000, rt, rn, off, 4)

    def ldur(self, rt, rn, off):
        _check(off, -256, 255, "ldur offset")
        self.emit(0xF8400000 | ((off & 0x1FF) << 12) | (rn << 5) | rt)

    def stur(self, rt, rn, off):
        _check(off, -256, 255, "stur offset")
        self.emit(0xF8000000 | ((off & 0x1FF) << 12) | (rn << 5) | rt)

    def ldr_reg(self, rt, rn, rm, scaled=False):
        self.emit(0xF8606800 | (rm << 16) | ((1 if scaled else 0) << 12) | (rn << 5) | rt)

    def str_reg(self, rt, rn, rm, scaled=False):
        self.emit(0xF8206800 | (rm << 16) | ((1 if scaled else 0) << 12) | (rn << 5) | rt)

    def ldrb_reg(self, rt, rn, rm): self.emit(0x38606800 | (rm << 16) | (rn << 5) | rt)
    def strb_reg(self, rt, rn, rm): self.emit(0x38206800 | (rm << 16) | (rn << 5) | rt)

    def _pair(self, base, rt, rt2, rn, off):
        _check(off, -512, 504, "pair offset")
        if off % 8:
            raise ValueError("unaligned pair offset")
        self.emit(base | (((off // 8) & 0x7F) << 15) | (rt2 << 10) | (rn << 5) | rt)

    def stp(self, rt, rt2, rn, off):       self._pair(0xA9000000, rt, rt2, rn, off)
    def ldp(self, rt, rt2, rn, off):       self._pair(0xA9400000, rt, rt2, rn, off)
    def stp_pre(self, rt, rt2, rn, off):   self._pair(0xA9800000, rt, rt2, rn, off)
    def ldp_post(self, rt, rt2, rn, off):  self._pair(0xA8C00000, rt, rt2, rn, off)

    # ---- branches
    def b(self, label):
        self._ref(label, "b26")
        self.emit(0x14000000)

    def bl(self, label):
        self._ref(label, "b26")
        self.emit(0x94000000)

    def b_cond(self, cond, label):
        self._ref(label, "b19")
        self.emit(0x54000000 | CONDS[cond])

    def cbz(self, rt, label):
        self._ref(label, "b19")
        self.emit(0xB4000000 | rt)

    def cbnz(self, rt, label):
        self._ref(label, "b19")
        self.emit(0xB5000000 | rt)

    def br(self, rn):   self.emit(0xD61F0000 | (rn << 5))
    def blr(self, rn):  self.emit(0xD63F0000 | (rn << 5))
    def ret(self):      self.emit(0xD65F03C0)
    def svc(self, imm=0): self.emit(0xD4000001 | (imm << 5))
    def nop(self):      self.emit(0xD503201F)

    def adr(self, rd, label):
        self._ref(label, "adr")
        self.emit(0x10000000 | rd)


def elf_exec(code, data=b"", entry_off=0, base=0x400000):
    """Static ET_EXEC for EM_AARCH64: one RX segment (headers + code + data)."""
    hdr = 64 + 56
    img = code + data
    total = hdr + len(img)
    ehdr = (b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\0" * 8 +
            struct.pack("<HHIQQQIHHHHHH", 2, 183, 1, base + hdr + entry_off,
                        64, 0, 0, 64, 56, 1, 0, 0, 0))
    phdr = struct.pack("<IIQQQQQQ", 1, 7, 0, base, base, total, total, 0x1000)
    return ehdr + phdr + img
