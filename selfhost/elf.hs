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
