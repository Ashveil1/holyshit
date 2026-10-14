# elf.hs - ELF64 image writer in holyshit: x64.py layout()/pack() for the
# static ET_EXEC image (tests/test_elf.py compares byte for byte).
BASE = 4194304
def u16(v):
  return [v & 255, v >> 8 & 255]
def u32(v):
  return [v & 255, v >> 8 & 255, v >> 16 & 255, v >> 24 & 255]
def u64(v):
  return u32(v & 4294967295) + u32(v >> 32 & 4294967295)
def layout(text_len):
  text_off = 64 + 2 * 56
  data_off = (text_off + text_len + 4095) & (0 - 4096)
  return {"text_off": text_off, "text_vaddr": BASE + text_off, "data_off": data_off, "data_vaddr": BASE + data_off}
def pack(code, data, entry_off, lo):
  img = [127, 69, 76, 70, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  img = img + u16(2) + u16(62) + u32(1) + u64(lo["text_vaddr"] + entry_off) + u64(64) + u64(0) + u32(0)
  img = img + u16(64) + u16(56) + u16(2) + u16(0) + u16(0) + u16(0)
  img = img + u32(1) + u32(5) + u64(lo["text_off"]) + u64(lo["text_vaddr"]) + u64(lo["text_vaddr"]) + u64(len(code)) + u64(len(code)) + u64(4096)
  img = img + u32(1) + u32(6) + u64(lo["data_off"]) + u64(lo["data_vaddr"]) + u64(lo["data_vaddr"]) + u64(len(data)) + u64(len(data)) + u64(4096)
  img = img + code
  while len(img) < lo["data_off"]:
    append(img, 0)
  return img + data
def layout_dyn(text_len, data_len):
  text_off = 64 + 5 * 56
  data_off = (text_off + text_len + 4095) & (0 - 4096)
  return {"text_off": text_off, "text_vaddr": BASE + text_off, "data_off": data_off, "data_vaddr": BASE + data_off}
def ph(kind, flags, off, va, sz, align):
  return u32(kind) + u32(flags) + u64(off) + u64(va) + u64(va) + u64(sz) + u64(sz) + u64(align)
def pack_dyn(code, data, entry_off, lo, libs, syms, got_off):
  d = data[0:len(data)]
  while len(d) % 8:
    append(d, 0)
  dv = lo["data_vaddr"]
  strtab = [0]
  interp = [47, 108, 105, 98, 54, 52, 47, 108, 100, 45, 108, 105, 110, 117, 120, 45, 120, 56, 54, 45, 54, 52, 46, 115, 111, 46, 50, 0]
  interp_off = len(d)
  d = d + interp
  while len(d) % 8:
    append(d, 0)
  needed = []
  symoff = []
  for names, offsets in [[libs, needed], [syms, symoff]]:
    for name in names:
      append(offsets, len(strtab))
      # Names are UTF-8 encoded by the shared byte helper.
      for b in encode_name(name):
        append(strtab, b)
      append(strtab, 0)
  str_off = len(d)
  d = d + strtab
  while len(d) % 8:
    append(d, 0)
  nsym = len(syms) + 1
  sym_off = len(d)
  for i in range(24):
    append(d, 0)
  for o in symoff:
    d = d + u32(o) + [18, 0] + u16(0) + u64(0) + u64(0)
  hash_off = len(d)
  d = d + u32(1) + u32(nsym) + u32(1 if nsym > 1 else 0)
  for i in range(nsym):
    d = d + u32(i + 1 if i > 0 and i < nsym - 1 else 0)
  while len(d) % 8:
    append(d, 0)
  rela_off = len(d)
  for i in range(len(syms)):
    d = d + u64(dv + got_off + 8 * i) + u64((i + 1) << 32 | 6) + u64(0)
  dyn_off = len(d)
  ent = []
  for n in needed:
    append(ent, [1, n])
  ent = ent + [[5, dv + str_off], [6, dv + sym_off], [10, len(strtab)], [11, 24], [4, dv + hash_off], [7, dv + rela_off], [8, 24 * len(syms)], [9, 24], [30, 8], [0, 0]]
  for tag, val in ent:
    d = d + u64(tag) + u64(val)
  dyn_len = len(d) - dyn_off
  img = [127, 69, 76, 70, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  img = img + u16(2) + u16(62) + u32(1) + u64(lo["text_vaddr"] + entry_off) + u64(64) + u64(0) + u32(0)
  img = img + u16(64) + u16(56) + u16(5) + u16(0) + u16(0) + u16(0)
  img = img + ph(1, 5, 0, BASE, lo["text_off"] + len(code), 4096)
  img = img + ph(1, 6, lo["data_off"], dv, len(d), 4096)
  img = img + ph(3, 4, lo["data_off"] + interp_off, dv + interp_off, len(interp), 1)
  img = img + ph(2, 6, lo["data_off"] + dyn_off, dv + dyn_off, dyn_len, 8)
  img = img + ph(1685382481, 6, 0, 0, 0, 16)
  img = img + code
  while len(img) < lo["data_off"]:
    append(img, 0)
  return img + d
def encode_name(s):
  # ELF library and symbol identifiers in this compiler are ASCII.
  out = []
  chars = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
  for c in s:
    n = find(chars, c)
    if n < 0:
      raise "ELF dynamic name must be ASCII"
    append(out, n + 32)
  return out
