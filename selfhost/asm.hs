# asm.hs - x86-64 assembler in holyshit: the integer subset of x64.py, with
# the same encodings (tests/test_asm.py compares them byte for byte).
# import asm; asm.reset(); asm.mov_ri32("rax", 1); asm.syscall(); asm.resolve()
REG = {"rax": 0, "rcx": 1, "rdx": 2, "rbx": 3, "rsp": 4, "rbp": 5, "rsi": 6, "rdi": 7, "r8": 8, "r9": 9, "r10": 10, "r11": 11, "r12": 12, "r13": 13, "r14": 14, "r15": 15}
CC = {"o": 0, "no": 1, "b": 2, "ae": 3, "e": 4, "ne": 5, "be": 6, "a": 7, "s": 8, "ns": 9, "p": 10, "np": 11, "l": 12, "ge": 13, "le": 14, "g": 15}
A = {"code": [], "labels": {}, "fix": []}

def reset():
  A["code"] = []
  A["labels"] = {}
  A["fix"] = []

def pos():
  return len(A["code"])

def b1(x):
  append(A["code"], x & 255)

def bn(xs):
  for x in xs:
    append(A["code"], x & 255)

def le32(v):
  bn([v, v >> 8, v >> 16, v >> 24])

def le64(v):
  i = 0
  while i < 8:
    b1(v >> (8 * i))
    i = i + 1

def regn(r):
  return REG[r]

def label(name):
  if name in A["labels"]:
    raise "dup label " + name
  A["labels"][name] = len(A["code"])

def rel32(name):
  append(A["fix"], [len(A["code"]), name])
  le32(0)

def rex(w, r, x, b):
  v = 64 + w * 8 + r * 4 + x * 2 + b
  if v != 64:
    b1(v)

def modrm(mod, reg, rm):
  b1((mod << 6) | ((reg & 7) << 3) | (rm & 7))

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
    xb = (xi >> 3) & 1
    sc = 0
    if scale == 2:
      sc = 1
    elif scale == 4:
      sc = 2
    elif scale == 8:
      sc = 3
    sib = (sc << 6) | ((xi & 7) << 3) | (bb & 7)
    has_sib = true
    rmf = 4
  elif (bb & 7) == 4:
    sib = 32 | (bb & 7)
    has_sib = true
    rmf = 4
  mod = 2
  if disp == 0 and (bb & 7) != 5:
    mod = 0
  elif disp >= 0 - 128 and disp <= 127:
    mod = 1
  rex(1, (r >> 3) & 1, xb, (bb >> 3) & 1)
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
  rex(1, (r >> 3) & 1, 0, 0)
  b1(opcode)
  modrm(0, r & 7, 5)
  rel32(lab)

def push_r(r):
  n = regn(r)
  if n >= 8:
    b1(65)
  b1(80 + (n & 7))

def pop_r(r):
  n = regn(r)
  if n >= 8:
    b1(65)
  b1(88 + (n & 7))

def mov_rr(d, s):
  dn = regn(d)
  sn = regn(s)
  rex(1, (dn >> 3) & 1, 0, (sn >> 3) & 1)
  b1(139)
  modrm(3, dn & 7, sn & 7)

def mov_ri32(d, imm):
  dn = regn(d)
  rex(1, 0, 0, (dn >> 3) & 1)
  b1(199)
  modrm(3, 0, dn & 7)
  le32(imm)

def mov_ri64(d, imm):
  dn = regn(d)
  rex(1, 0, 0, (dn >> 3) & 1)
  b1(184 + (dn & 7))
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
  bb = (bnum >> 3) & 1
  rn = s8 & 7
  rb = (s8 >> 3) & 1
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
  rex(1, (sn >> 3) & 1, 0, (dn >> 3) & 1)
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
  rex(1, 0, 0, (dn >> 3) & 1)
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
  rex(1, (dn >> 3) & 1, 0, (sn >> 3) & 1)
  bn([15, 175])
  modrm(3, dn & 7, sn & 7)

def cqo():
  bn([72, 153])

def f7(ext, r):
  n = regn(r)
  rex(1, 0, 0, (n >> 3) & 1)
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
  rex(1, 0, 0, (n >> 3) & 1)
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
  rex(1, 0, 0, (n >> 3) & 1)
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
  db = (dn >> 3) & 1
  bb = (bnum >> 3) & 1
  xb = (xn >> 3) & 1
  if bb == 1 or xb == 1 or db == 1:
    b1(64 | (db << 2) | (xb << 1) | bb)
  bn([15, 182])
  small = disp >= 0 - 128 and disp <= 127
  if small:
    modrm(1, dn & 7, 4)
  else:
    modrm(2, dn & 7, 4)
  b1((sc << 6) | ((xn & 7) << 3) | (bnum & 7))
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

def nop():
  b1(144)

def setcc_al(cc):
  bn([15, 144 + CC[cc], 192])

def movzx_eax_al():
  bn([15, 182, 192])

def resolve():
  out = A["code"][0:len(A["code"])]
  for f in A["fix"]:
    if not (f[1] in A["labels"]):
      raise "undefined label " + f[1]
    rel = A["labels"][f[1]] - (f[0] + 4)
    out[f[0]] = rel & 255
    out[f[0] + 1] = (rel >> 8) & 255
    out[f[0] + 2] = (rel >> 16) & 255
    out[f[0] + 3] = (rel >> 24) & 255
  return out
