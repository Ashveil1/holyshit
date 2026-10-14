# asm.hs - x86-64 assembler in holyshit: the integer subset of x64.py, with
# the same encodings (tests/test_asm.py compares them byte for byte).
# import asm; asm.reset(); asm.mov_ri32("rax", 1); asm.syscall(); asm.resolve()
REG = {"rax": 0, "rcx": 1, "rdx": 2, "rbx": 3, "rsp": 4, "rbp": 5, "rsi": 6, "rdi": 7, "r8": 8, "r9": 9, "r10": 10, "r11": 11, "r12": 12, "r13": 13, "r14": 14, "r15": 15}
CC = {"o": 0, "no": 1, "b": 2, "ae": 3, "e": 4, "ne": 5, "be": 6, "a": 7, "s": 8, "ns": 9, "p": 10, "np": 11, "l": 12, "ge": 13, "le": 14, "g": 15}
S = {"code": [], "labels": {}, "fixups": [], "data": [], "data_labels": {}}
def reset():
  S["code"] = []
  S["labels"] = {}
  S["fixups"] = []
def pos():
  return len(S["code"])
def b1(x):
  append(S["code"], x & 255)
def bn(xs):
  for x in xs:
    append(S["code"], x & 255)
def le32(v):
  bn([v, v >> 8, v >> 16, v >> 24])
def le64(v):
  i = 0
  while i < 8:
    b1(v >> (8 * i))
    i = i + 1
def regn(r):
  if find("0123456789", str(r)[0]) >= 0:
    return r
  return REG[r]
def state():
  return S
def label(name):
  if name in S["labels"]:
    raise "dup label " + name
  S["labels"][name] = len(S["code"])
def rel32(name):
  append(S["fixups"], [len(S["code"]), name])
  le32(0)
def rex(w, r, x, b):
  v = 64 + w * 8 + r * 4 + x * 2 + b
  if v != 64:
    b1(v)
def modrm(mod, reg, rm):
  b1(mod << 6 | (reg & 7 << 3) | (rm & 7))
def rm_mem(opcode, reg, base, disp, index, scale):
  r = regn(reg)
  bb = regn(base)
  xr = 0
  has_sib = false
  sib = 0
  rmf = bb & 7
  xb = 0
  if index != null:
    xi = regn(index)
    xb = xi >> 3 & 1
    sc = 0
    if scale == 2:
      sc = 1
    elif scale == 4:
      sc = 2
    elif scale == 8:
      sc = 3
    sib = sc << 6 | (xi & 7 << 3) | (bb & 7)
    has_sib = true
    rmf = 4
  elif bb & 7 == 4:
    sib = 32 | (bb & 7)
    has_sib = true
    rmf = 4
  mod = 2
  if disp == 0 and bb & 7 != 5:
    mod = 0
  elif disp >= 0 - 128 and disp <= 127:
    mod = 1
  rex(1, r >> 3 & 1, xb, bb >> 3 & 1)
  b1(opcode)
  modrm(mod, r & 7, rmf)
  if has_sib:
    b1(sib)
  if mod == 1:
    b1(disp)
  elif mod == 2:
    le32(disp)
def rm_rip(opcode, reg, lab):
  r = regn(reg)
  rex(1, r >> 3 & 1, 0, 0)
  b1(opcode)
  modrm(0, r & 7, 5)
  rel32(lab)
def push_r(r):
  n = regn(r)
  if n >= 8:
    b1(65)
  b1(80 + n & 7)
def pop_r(r):
  n = regn(r)
  if n >= 8:
    b1(65)
  b1(88 + n & 7)
def mov_rr(d, s):
  dn = regn(d)
  sn = regn(s)
  rex(1, dn >> 3 & 1, 0, sn >> 3 & 1)
  b1(139)
  modrm(3, dn & 7, sn & 7)
def mov_ri32(d, imm):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(199)
  modrm(3, 0, dn & 7)
  le32(imm)
def mov_ri64(d, imm):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(184 + dn & 7)
  le64(imm)
def mov_rm(d, base, disp):
  rm_mem(139, d, base, disp, null, 1)
def mov_rmx(d, base, index, scale, disp):
  rm_mem(139, d, base, disp, index, scale)
def mov_mr(base, s, disp):
  rm_mem(137, s, base, disp, null, 1)
def lea_m(d, base, disp):
  rm_mem(141, d, base, disp, null, 1)
def lea_mx(d, base, index, scale, disp):
  rm_mem(141, d, base, disp, index, scale)
def lea_rip(d, lab):
  rm_rip(141, d, lab)
def mov_rm_rip(d, lab):
  rm_rip(139, d, lab)
def mov_mr_rip(lab, s):
  rm_rip(137, s, lab)
def mov_mr8(base, s8, disp):
  bnum = regn(base)
  bb = bnum >> 3 & 1
  rn = s8 & 7
  rb = s8 >> 3 & 1
  bl = bnum & 7
  if rb == 1 or bb == 1 or s8 == 4 or s8 == 5 or s8 == 6 or s8 == 7:
    b1(64 | (rb << 2) | bb)
  b1(136)
  mod = 2
  if disp == 0 and bl != 5:
    mod = 0
  elif disp >= 0 - 128 and disp <= 127:
    mod = 1
  if bl == 4:
    modrm(mod, rn, 4)
    b1(32 | bl)
  else:
    modrm(mod, rn, bl)
  if mod == 1:
    b1(disp)
  elif mod == 2:
    le32(disp)
def alu_rr(op, d, s):
  dn = regn(d)
  sn = regn(s)
  rex(1, sn >> 3 & 1, 0, dn >> 3 & 1)
  b1(op)
  modrm(3, sn & 7, dn & 7)
def add_rr(d, s):
  alu_rr(1, d, s)
def sub_rr(d, s):
  alu_rr(41, d, s)
def cmp_rr(d, s):
  alu_rr(57, d, s)
def and_rr(d, s):
  alu_rr(33, d, s)
def or_rr(d, s):
  alu_rr(9, d, s)
def xor_rr(d, s):
  alu_rr(49, d, s)
def test_rr(d, s):
  alu_rr(133, d, s)
def alu_ri32(ext, d, imm):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(129)
  modrm(3, ext, dn & 7)
  le32(imm)
def add_ri32(d, imm):
  alu_ri32(0, d, imm)
def sub_ri32(d, imm):
  alu_ri32(5, d, imm)
def cmp_ri32(d, imm):
  alu_ri32(7, d, imm)
def and_ri32(d, imm):
  alu_ri32(4, d, imm)
def imul_rr(d, s):
  dn = regn(d)
  sn = regn(s)
  rex(1, dn >> 3 & 1, 0, sn >> 3 & 1)
  bn([15, 175])
  modrm(3, dn & 7, sn & 7)
def xmm_rr(pre, opc, xd, xs):
  b1(pre)
  b1(15)
  b1(opc)
  modrm(3, xd, xs)
def addsd(xd, xs):
  xmm_rr(242, 88, xd, xs)
def subsd(xd, xs):
  xmm_rr(242, 92, xd, xs)
def mulsd(xd, xs):
  xmm_rr(242, 89, xd, xs)
def divsd(xd, xs):
  xmm_rr(242, 94, xd, xs)
def xorpd(xd, xs):
  xmm_rr(102, 87, xd, xs)
def ucomisd(xa, xb):
  xmm_rr(102, 46, xa, xb)
def cvtsi2sd(xd, rs):
  rn = regn(rs)
  b1(242)
  rex(1, 0, 0, rn >> 3 & 1)
  bn([15, 42])
  modrm(3, xd, rn & 7)
def cvttsd2si(rd, xs):
  dn = regn(rd)
  b1(242)
  rex(1, 0, 0, dn >> 3 & 1)
  bn([15, 44])
  modrm(3, xs, dn & 7)
def movq_xr(xd, rs):
  rn = regn(rs)
  b1(102)
  rex(1, 0, 0, rn >> 3 & 1)
  bn([15, 110])
  modrm(3, xd, rn & 7)
def movq_rx(rd, xs):
  dn = regn(rd)
  b1(102)
  rex(1, 0, 0, dn >> 3 & 1)
  bn([15, 126])
  modrm(3, xs, dn & 7)
def call_rax():
  bn([255, 208])
def cqo():
  bn([72, 153])
def f7(ext, r):
  n = regn(r)
  rex(1, 0, 0, n >> 3 & 1)
  b1(247)
  modrm(3, ext, n & 7)
def idiv_r(r):
  f7(7, r)
def div_r(r):
  f7(6, r)
def not_r(r):
  f7(2, r)
def neg_r(r):
  f7(3, r)
def shift_ri8(ext, d, imm):
  n = regn(d)
  rex(1, 0, 0, n >> 3 & 1)
  b1(193)
  modrm(3, ext, n & 7)
  b1(imm)
def shl_ri8(d, imm):
  shift_ri8(4, d, imm)
def shr_ri8(d, imm):
  shift_ri8(5, d, imm)
def sar_ri8(d, imm):
  shift_ri8(7, d, imm)
def shift_cl(ext, d):
  n = regn(d)
  rex(1, 0, 0, n >> 3 & 1)
  b1(211)
  modrm(3, ext, n & 7)
def shl_cl(d):
  shift_cl(4, d)
def shr_cl(d):
  shift_cl(5, d)
def sar_cl(d):
  shift_cl(7, d)
def movzx_rm8x(dst, base, index, scale, disp):
  dn = regn(dst)
  bnum = regn(base)
  xn = regn(index)
  sc = 0
  if scale == 2:
    sc = 1
  elif scale == 4:
    sc = 2
  elif scale == 8:
    sc = 3
  db = dn >> 3 & 1
  bb = bnum >> 3 & 1
  xb = xn >> 3 & 1
  if bb == 1 or xb == 1 or db == 1:
    b1(64 | (db << 2) | (xb << 1) | bb)
  bn([15, 182])
  small = disp >= 0 - 128 and disp <= 127
  if small:
    modrm(1, dn & 7, 4)
  else:
    modrm(2, dn & 7, 4)
  b1(sc << 6 | (xn & 7 << 3) | (bnum & 7))
  if small:
    b1(disp)
  else:
    le32(disp)
def jmp(lab):
  b1(233)
  rel32(lab)
def jcc(cc, lab):
  bn([15, 128 + CC[cc]])
  rel32(lab)
def call(lab):
  b1(232)
  rel32(lab)
def ret():
  b1(195)
def syscall():
  bn([15, 5])
def jmp_r(r):
  rn = regn(r)
  if rn >= 8:
    b1(65)
  b1(255)
  b1(192 | (4 << 3) | (rn & 7))
def nop():
  b1(144)
def setcc_al(cc):
  bn([15, 144 + CC[cc], 192])
def movzx_eax_al():
  bn([15, 182, 192])
def resolve():
  out = S["code"][0:len(S["code"])]
  for f in S["fixups"]:
    if not (f[1] in S["labels"]):
      raise "undefined label " + f[1]
    rel = S["labels"][f[1]] - (f[0] + 4)
    out[f[0]] = rel & 255
    out[f[0] + 1] = rel >> 8 & 255
    out[f[0] + 2] = rel >> 16 & 255
    out[f[0] + 3] = rel >> 24 & 255
  return out
def bsr_rr(d, s):
  dn = regn(d)
  sn = regn(s)
  rex(1, dn >> 3 & 1, 0, sn >> 3 & 1)
  bn([15, 189])
  modrm(3, dn & 7, sn & 7)
def call_r11():
  bn([65, 255, 211])
def mov_mrx(base, index, scale, disp, s):
  rm_mem(137, s, base, disp, index, scale)
def not_rr(d):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(247)
  modrm(3, 2, dn & 7)
def or_ri8(d, imm):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(131)
  modrm(3, 1, dn & 7)
  b1(imm)
def movq_xm(xd, base, disp):
  bnum = regn(base)
  b1(243)
  rex(1, 0, 0, bnum >> 3 & 1)
  bn([15, 126])
  if disp == 0 and bnum & 7 != 5:
    modrm(0, xd, bnum & 7)
  elif disp >= 0 - 128 and disp <= 127:
    modrm(1, xd, bnum & 7)
    b1(disp)
  else:
    modrm(2, xd, bnum & 7)
    le32(disp)
def movzx_eax_mx(base, index, scale, disp):
  movzx_rm8x("rax", base, index, scale, disp)
# -- data section + final layout (hosted ELF image) --
def data_reset():
  S["data"] = []
  S["data_labels"] = {}
def data_label(name):
  if name in S["data_labels"]:
    raise "dup data label " + name
  S["data_labels"][name] = len(S["data"])
def data_qword(v):
  i = 0
  while i < 8:
    append(S["data"], v >> (8 * i) & 255)
    i = i + 1
def data_bytes(xs):
  for x in xs:
    append(S["data"], x & 255)
def resolve_at(text_vaddr, data_vaddr):
  out = S["code"][0:len(S["code"])]
  for f in S["fixups"]:
    if f[1] in S["labels"]:
      target = text_vaddr + S["labels"][f[1]]
    elif f[1] in S["data_labels"]:
      target = data_vaddr + S["data_labels"][f[1]]
    else:
      raise "undefined label " + f[1]
    rel = target - (text_vaddr + f[0] + 4)
    out[f[0]] = rel & 255
    out[f[0] + 1] = rel >> 8 & 255
    out[f[0] + 2] = rel >> 16 & 255
    out[f[0] + 3] = rel >> 24 & 255
  return out
def or_ri32(d, imm):
  alu_ri32(1, d, imm)
def xor_ri32(d, imm):
  alu_ri32(6, d, imm)
def adc_ri32(d, imm):
  alu_ri32(2, d, imm)
def cli():
  b1(250)
def hlt():
  b1(244)
def sti():
  b1(251)
def sahf():
  b1(158)
def iretq():
  bn([72, 207])
def sysret():
  bn([72, 15, 7])
def in_al_dx():
  b1(236)
def out_dx_al():
  b1(238)
def in_ax_dx():
  bn([102, 237])
def in_eax_dx():
  b1(237)
def out_dx_ax():
  bn([102, 239])
def out_dx_eax():
  b1(239)
def mov_ri16(d, imm):
  dn = regn(d)
  b1(102)
  if dn >> 3 & 1:
    b1(65)
  b1(184 + dn & 7)
  bn([imm, imm >> 8])
def mov_ax_imm16(imm):
  bn([102, 184, imm, imm >> 8])
def mov_seg16(seg, r):
  bn([102, 142])
  modrm(3, seg, r)
def add_ri8(d, imm):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(128)
  modrm(3, 0, dn & 7)
  b1(imm)
def xchg_rip(d, lab):
  rm_rip(135, d, lab)
def mov_rcr64(rd, cr):
  b1(72)
  bn([15, 32])
  modrm(3, cr & 7, regn(rd) & 7)
def mov_cr64(cr, rs):
  b1(72)
  bn([15, 34])
  modrm(3, cr & 7, regn(rs) & 7)
def mul_r(r):
  rn = regn(r)
  rex(1, 0, 0, rn >> 3 & 1)
  b1(247)
  modrm(3, 4, rn & 7)
def x87_mem(op, ext, base, disp):
  bnum = regn(base)
  if bnum >> 3 & 1:
    raise "x87 needs a low register base"
  b1(op)
  if disp == 0 and bnum & 7 != 5:
    modrm(0, ext, bnum & 7)
  elif disp >= 0 - 128 and disp <= 127:
    modrm(1, ext, bnum & 7)
    b1(disp)
  else:
    modrm(2, ext, bnum & 7)
    le32(disp)
def fld_m64(base, disp):
  x87_mem(221, 0, base, disp)
def fstp_m64(base, disp):
  x87_mem(221, 3, base, disp)
def fprem():
  bn([217, 248])
def fnstsw_ax():
  bn([223, 224])
def fstp_st1():
  bn([221, 217])
def movzx_eax_m8(base, disp):
  bnum = regn(base)
  if bnum >> 3 & 1:
    b1(65)
  bn([15, 182])
  if bnum & 7 == 4:
    if disp == 0:
      modrm(0, 0, 4)
    elif disp >= 0 - 128 and disp <= 127:
      modrm(1, 0, 4)
      b1(disp)
    else:
      modrm(2, 0, 4)
      le32(disp)
    b1(32 | (bnum & 7))
  else:
    if disp == 0 and bnum & 7 != 5:
      modrm(0, 0, bnum & 7)
    elif disp >= 0 - 128 and disp <= 127:
      modrm(1, 0, bnum & 7)
      b1(disp)
    else:
      modrm(2, 0, bnum & 7)
      le32(disp)
def movzx_edx_mx(base, index, scale, disp):
  movzx_rm8x("rdx", base, index, scale, disp)
def test_al_imm8(imm):
  bn([168, imm])
def rip_mem(op, ext, lab):
  bn([72, op])
  modrm(0, ext, 5)
  rel32(lab)
def lidt_rip(lab):
  bn([15, 1])
  modrm(0, 3, 5)
  rel32(lab)
def inc_mrip(lab):
  rip_mem(255, 0, lab)
def dec_mrip(lab):
  rip_mem(255, 1, lab)
def jmp_m(base, disp):
  rm_mem(255, 4, base, disp, null, 1)
def push_m(base, disp):
  rm_mem(255, 6, base, disp, null, 1)
def mov_ri64_bytes(d, bs):
  dn = regn(d)
  rex(1, 0, 0, dn >> 3 & 1)
  b1(184 + dn & 7)
  bn(bs)
def mov_tagged_int(d, v):
  # Tag via bytes: compiler arithmetic itself may have only 62 payload bits.
  bs = []
  for i in range(8):
    append(bs, v >> (8 * i) & 255)
  carry = 1
  for i in range(8):
    n = bs[i] * 4 + carry
    bs[i] = n & 255
    carry = n >> 8
  mov_ri64_bytes(d, bs)
