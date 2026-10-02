#!/usr/bin/env python3
"""x64: minimal x86-64 assembler + static ELF64 writer for holyshit.

No gcc/as/ld involved. Supports exactly the instructions the hs backend
emits (plus a few extras). 64-bit operand size throughout unless noted.
"""
import struct

REG = {"rax": 0, "rcx": 1, "rdx": 2, "rbx": 3, "rsp": 4, "rbp": 5,
       "rsi": 6, "rdi": 7, "r8": 8, "r9": 9, "r10": 10, "r11": 11,
       "r12": 12, "r13": 13, "r14": 14, "r15": 15}

# condition codes for jcc/setcc: (short suffix, opcode byte)
CC = {"o": 0x0, "no": 0x1, "b": 0x2, "ae": 0x3, "e": 0x4, "ne": 0x5,
      "be": 0x6, "a": 0x7, "s": 0x8, "ns": 0x9, "p": 0xA, "np": 0xB,
      "l": 0xC, "ge": 0xD, "le": 0xE, "g": 0xF}


def _rn(r):
    if isinstance(r, str):
        r = REG[r]
    return r & 7, (r >> 3) & 1


class Asm:
    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.fixups = []  # (pos, label, kind) kind in ("rel32", "riprel")
        self.data = bytearray()
        self.data_labels = {}

    # -- plumbing --
    def pos(self):
        return len(self.code)

    def label(self, name):
        if name in self.labels:
            raise ValueError(f"dup label {name}")
        self.labels[name] = len(self.code)

    def _rel32(self, label):
        self.fixups.append((len(self.code), label, "rel32"))
        self.code += b"\0\0\0\0"

    def _rex(self, w, r=0, x=0, b=0):
        v = 0x40 | (8 if w else 0) | (r << 2) | (x << 1) | b
        if v != 0x40:
            self.code.append(v)

    def _modrm(self, mod, reg, rm):
        self.code.append((mod << 6) | ((reg & 7) << 3) | (rm & 7))

    def _rm(self, opcode, reg_field, base, disp=0, index=None, scale=1, rip_label=None):
        """Emit rex + opcode + modrm [+sib] [+disp] for r64 <-> mem."""
        rn, rb = _rn(reg_field)
        if base == "rip":
            assert index is None
            self._rex(True, r=rb)
            self.code.append(opcode)
            self._modrm(0, rn, 5)
            self.fixups.append((len(self.code), rip_label, "riprel"))
            self.code += b"\0\0\0\0"
            return
        bn, bb = _rn(base)
        xb = 0
        sib = None
        if index is not None:
            xn, xb = _rn(index)
            assert scale in (1, 2, 4, 8)
            sc = {1: 0, 2: 1, 4: 2, 8: 3}[scale]
            sib = (sc << 6) | ((xn & 7) << 3) | bn
            rm = 4
        elif bn == 4:  # rsp/r12 need SIB even without index
            sib = (4 << 3) | bn
            rm = 4
        else:
            rm = bn
        if disp == 0 and bn != 5:
            mod, db = 0, b""
        elif -128 <= disp <= 127:
            mod, db = 1, struct.pack("b", disp)
        else:
            mod, db = 2, struct.pack("<i", disp)
        self._rex(True, r=rb, x=xb, b=bb)
        self.code.append(opcode)
        self._modrm(mod, rn, rm)
        if sib is not None:
            self.code.append(sib)
        self.code += db

    # -- data movement --
    def push_r(self, r):
        rn, rb = _rn(r)
        if rb:
            self.code.append(0x41)
        self.code.append(0x50 + rn)

    def pop_r(self, r):
        rn, rb = _rn(r)
        if rb:
            self.code.append(0x41)
        self.code.append(0x58 + rn)

    def mov_rr(self, d, s):
        dn, db = _rn(d)
        sn, sb = _rn(s)
        self._rex(True, r=db, b=sb)
        self.code.append(0x8B)
        self._modrm(3, dn, sn)

    def mov_ri32(self, d, imm):
        dn, db = _rn(d)
        self._rex(True, b=db)
        self.code.append(0xC7)
        self._modrm(3, 0, dn)
        self.code += struct.pack("<i", imm)

    def mov_ri64(self, d, imm):
        dn, db = _rn(d)
        self._rex(True, b=db)
        self.code.append(0xB8 + dn)
        self.code += struct.pack("<q", imm)

    def mov_rm(self, d, base, disp=0):
        self._rm(0x8B, d, base, disp)

    def mov_rmx(self, d, base, index, scale, disp=0):
        self._rm(0x8B, d, base, disp, index, scale)

    def mov_mr(self, base, s, disp=0):
        self._rm(0x89, s, base, disp)

    def mov_mr8(self, base, s8, disp=0):
        # s8: 0=al,1=cl,2=dl,3=bl (+4=spl,6=sil,8+=r8b.. need REX)
        import struct as _st
        bn, bb = _rn(base)
        rn, rb = (s8 & 7), ((s8 >> 3) & 1)
        need_rex = rb or bb or s8 in (4, 5, 6, 7)
        if need_rex:
            self.code.append(0x40 | (rb << 2) | bb)
        self.code.append(0x88)
        if bn == 4:
            if disp == 0:
                self._modrm(0, rn, 4)
            elif -128 <= disp <= 127:
                self._modrm(1, rn, 4)
                self.code.append(disp & 0xFF)
            else:
                self._modrm(2, rn, 4)
                self.code += _st.pack("<i", disp)
            self.code.append((4 << 3) | bn)
        else:
            if disp == 0 and bn != 5:
                self._modrm(0, rn, bn)
            elif -128 <= disp <= 127:
                self._modrm(1, rn, bn)
                self.code.append(disp & 0xFF)
            else:
                self._modrm(2, rn, bn)
                self.code += _st.pack("<i", disp)

    def and_ri32(self, d, imm):
        self._alu_ri32(4, d, imm)

    def add_ri8(self, d, imm):
        dn, db = _rn(d)
        self._rex(True, b=db)
        self.code.append(0x80)
        self._modrm(3, 0, dn)
        self.code.append(imm & 0xFF)

    def mov_mrx(self, base, index, scale, disp, s):
        self._rm(0x89, s, base, disp, index, scale)

    def lea_rip(self, d, label):
        self._rm(0x8D, d, "rip", rip_label=label)

    def lea_m(self, d, base, disp=0, index=None, scale=1):
        self._rm(0x8D, d, base, disp, index, scale)

    # -- arithmetic --
    def _alu_rr(self, op, d, s):
        dn, db = _rn(d)
        sn, sb = _rn(s)
        self._rex(True, r=sb, b=db)
        self.code.append(op)
        self._modrm(3, sn, dn)

    def add_rr(self, d, s):
        self._alu_rr(0x01, d, s)

    def sub_rr(self, d, s):
        self._alu_rr(0x29, d, s)

    def cmp_rr(self, d, s):
        self._alu_rr(0x39, d, s)

    def and_rr(self, d, s):
        self._alu_rr(0x21, d, s)

    def or_rr(self, d, s):
        self._alu_rr(0x09, d, s)

    def xor_rr(self, d, s):
        self._alu_rr(0x31, d, s)

    def _alu_ri32(self, op_ext, d, imm):
        dn, db = _rn(d)
        self._rex(True, b=db)
        self.code.append(0x81)
        self._modrm(3, op_ext, dn)
        self.code += struct.pack("<i", imm)

    def add_ri32(self, d, imm):
        self._alu_ri32(0, d, imm)

    def sub_ri32(self, d, imm):
        self._alu_ri32(5, d, imm)

    def cmp_ri32(self, d, imm):
        self._alu_ri32(7, d, imm)

    def and_ri32(self, d, imm):
        self._alu_ri32(4, d, imm)

    def imul_rr(self, d, s):
        dn, db = _rn(d)
        sn, sb = _rn(s)
        self._rex(True, r=db, b=sb)
        self.code += bytes([0x0F, 0xAF])
        self._modrm(3, dn, sn)

    def cqo(self):
        self.code += bytes([0x48, 0x99])

    def idiv_r(self, r):
        rn, rb = _rn(r)
        self._rex(True, b=rb)
        self.code.append(0xF7)
        self._modrm(3, 7, rn)

    def div_r(self, r):
        rn, rb = _rn(r)
        self._rex(True, b=rb)
        self.code.append(0xF7)
        self._modrm(3, 6, rn)

    def not_r(self, r):
        rn, rb = _rn(r)
        self._rex(True, b=rb)
        self.code.append(0xF7)
        self._modrm(3, 2, rn)

    def neg_r(self, r):
        rn, rb = _rn(r)
        self._rex(True, b=rb)
        self.code.append(0xF7)
        self._modrm(3, 3, rn)

    def _shift_ri8(self, ext, d, imm):
        dn, db = _rn(d)
        self._rex(True, b=db)
        self.code.append(0xC1)
        self._modrm(3, ext, dn)
        self.code.append(imm & 0xFF)

    def shl_ri8(self, d, imm):
        self._shift_ri8(4, d, imm)

    def shr_ri8(self, d, imm):
        self._shift_ri8(5, d, imm)

    def sar_ri8(self, d, imm):
        self._shift_ri8(7, d, imm)

    def test_rr(self, d, s):
        dn, db = _rn(d)
        sn, sb = _rn(s)
        self._rex(True, r=sb, b=db)
        self.code.append(0x85)
        self._modrm(3, sn, dn)

    # -- control --
    def jmp(self, label):
        self.code.append(0xE9)
        self._rel32(label)

    def jcc(self, cc, label):
        self.code += bytes([0x0F, 0x80 + CC[cc]])
        self._rel32(label)

    def call(self, label):
        self.code.append(0xE8)
        self._rel32(label)

    def call_rax(self):
        self.code += bytes([0xFF, 0xD0])

    def ret(self):
        self.code.append(0xC3)

    def syscall(self):
        self.code += bytes([0x0F, 0x05])

    def nop(self):
        self.code.append(0x90)

    def setcc_al(self, cc):
        self.code += bytes([0x0F, 0x90 + CC[cc], 0xC0])

    def movzx_eax_al(self):
        self.code += bytes([0x0F, 0xB6, 0xC0])

    # -- resolve --
    def resolve(self, text_vaddr, data_vaddr):
        out = bytearray(self.code)
        for pos, label, kind in self.fixups:
            if label in self.labels:
                target = text_vaddr + self.labels[label]
                base = text_vaddr
            elif label in self.data_labels:
                target = data_vaddr + self.data_labels[label]
                base = text_vaddr
            else:
                raise ValueError(f"undefined label {label}")
            if kind == "rel32":
                rel = target - (base + pos + 4)
                out[pos:pos + 4] = struct.pack("<i", rel)
            elif kind == "riprel":
                rel = target - (base + pos + 4)
                out[pos:pos + 4] = struct.pack("<i", rel)
        return bytes(out)

    # -- data section --
    def data_label(self, name):
        if name in self.data_labels:
            raise ValueError(f"dup data label {name}")
        self.data_labels[name] = len(self.data)

    def data_qword(self, v=0):
        self.data += struct.pack("<q", v)

    def data_bytes(self, b):
        self.data += b


BASE = 0x400000


def layout(text_len, data_len):
    ehsize, phentsize, nph = 64, 56, 2
    text_off = ehsize + nph * phentsize
    text_vaddr = BASE + text_off
    data_off = (text_off + text_len + 0xFFF) & ~0xFFF
    data_vaddr = BASE + data_off
    return {"ehsize": ehsize, "phentsize": phentsize, "nph": nph,
            "text_off": text_off, "text_vaddr": text_vaddr,
            "data_off": data_off, "data_vaddr": data_vaddr}


def pack(code, data, entry_off, lo):
    eh = struct.pack("<16sHHIQQQIHHHHHH",
                      b"\x7fELF\x02\x01\x01" + b"\0" * 9,
                      2, 62, 1, lo["text_vaddr"] + entry_off, lo["ehsize"],
                      0, 0, lo["ehsize"], lo["phentsize"], lo["nph"], 0, 0, 0)
    ph1 = struct.pack("<IIQQQQQQ", 1, 5, lo["text_off"], lo["text_vaddr"],
                      lo["text_vaddr"], len(code), len(code), 0x1000)
    ph2 = struct.pack("<IIQQQQQQ", 1, 6, lo["data_off"], lo["data_vaddr"],
                      lo["data_vaddr"], len(data), len(data), 0x1000)
    img = bytearray()
    img += eh + ph1 + ph2
    assert len(img) == lo["text_off"]
    img += code
    img += b"\0" * (lo["data_off"] - len(img))
    img += data
    return bytes(img)


def link_elf(code, data=b"", entry_off=0, ro_extra=None):
    """Build a static ELF64 with RX text (+rodata) and RW data segments."""
    text = bytes(code) + (bytes(ro_extra) if ro_extra else b"")
    lo = layout(len(text), len(data))
    img = pack(text, bytes(data), entry_off, lo)
    return img, {"text_vaddr": lo["text_vaddr"], "data_vaddr": lo["data_vaddr"],
                 "entry": lo["text_vaddr"] + entry_off}
