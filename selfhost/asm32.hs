# Boot assembler. Byte encodings match x64.Asm32; no external assembler.
import elf
CC = {"o": 0, "no": 1, "b": 2, "ae": 3, "e": 4, "ne": 5, "be": 6, "a": 7, "s": 8, "ns": 9, "p": 10, "np": 11, "l": 12, "ge": 13, "le": 14, "g": 15}
class Asm32:
  def __init__(self):
    self.code = []
    self.labels = {}
    self.fixups = []
  def pos(self):
    return len(self.code)
  def label(self, name):
    if has(self.labels, name):
      raise "dup label " + name
    self.labels[name] = len(self.code)
  def rel32(self, name):
    append(self.fixups, [len(self.code), name, "rel32"])
    self.code = self.code + [0, 0, 0, 0]
  def abs32(self, name):
    append(self.fixups, [len(self.code), name, "abs32"])
    self.code = self.code + [0, 0, 0, 0]
  def modrm(self, mod, reg, rm):
    append(self.code, (mod << 6) | ((reg & 7) << 3) | (rm & 7))
  def cli(self):
    append(self.code, 250)
  def hlt(self):
    append(self.code, 244)
  def nop(self):
    append(self.code, 144)
  def mov_ri32(self, rd, imm):
    self.code = self.code + [184 + (rd & 7)] + elf.u32(imm)
  def mov_ri32_abs(self, rd, name):
    append(self.code, 184 + (rd & 7))
    self.abs32(name)
  def mov_rr(self, d, s):
    append(self.code, 139)
    self.modrm(3, d, s)
  def mov_cr(self, cr, rs):
    self.code = self.code + [15, 34]
    self.modrm(3, cr, rs)
  def mov_rcr(self, rd, cr):
    self.code = self.code + [15, 32]
    self.modrm(3, cr, rd)
  def or_ri32(self, rd, imm):
    append(self.code, 129)
    self.modrm(3, 1, rd)
    self.code = self.code + elf.u32(imm)
  def xor_rr(self, d, s):
    append(self.code, 49)
    self.modrm(3, d, s)
  def add_ri32(self, rd, imm):
    append(self.code, 129)
    self.modrm(3, 0, rd)
    self.code = self.code + elf.u32(imm)
  def add_ri8(self, rd, imm):
    append(self.code, 131)
    self.modrm(3, 0, rd)
    append(self.code, imm & 255)
  def dec_r(self, rd):
    append(self.code, 72 + (rd & 7))
  def mov_mr_abs(self, name, rs):
    append(self.code, 137)
    self.modrm(0, rs, 5)
    self.abs32(name)
  def mov_rm_abs(self, rd, name):
    append(self.code, 139)
    self.modrm(0, rd, 5)
    self.abs32(name)
  def lgdt_abs(self, name):
    self.code = self.code + [15, 1]
    self.modrm(0, 2, 5)
    self.abs32(name)
  def ltr(self, sel):
    self.mov_ri32(0, sel)
    self.code = self.code + [15, 0]
    self.modrm(3, 3, 0)
  def rdmsr(self):
    self.code = self.code + [15, 50]
  def wrmsr(self):
    self.code = self.code + [15, 48]
  def jmp_far(self, sel, name):
    append(self.code, 234)
    self.abs32(name)
    self.code = self.code + elf.u16(sel)
  def jmp_far_abs(self, sel, addr):
    self.code = self.code + [234] + elf.u32(addr) + elf.u16(sel)
  def jmp(self, name):
    append(self.code, 233)
    self.rel32(name)
  def jcc(self, cc, name):
    self.code = self.code + [15, 128 + CC[cc]]
    self.rel32(name)
  def resolve(self, base_addr):
    out = self.code[0:len(self.code)]
    for fix in self.fixups:
      pos = fix[0]
      name = fix[1]
      if not has(self.labels, name):
        raise "undefined label " + name
      value = self.labels[name]
      if fix[2] == "rel32":
        value = value - (pos + 4)
      else:
        value = value + base_addr
      bs = elf.u32(value)
      for i in range(4):
        out[pos + i] = bs[i]
    return out
