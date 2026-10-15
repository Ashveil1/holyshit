# ramdisk loader — unpacks a KRFS image (multiboot module 0, usually from
# QEMU -initrd) into kvfs. KRFS v1, all little-endian, every field padded
# to 4 bytes so only load32 is needed (alignment-safe on every backend):
#   "KRFS" | u32 count
#   per entry: u32 type (0 = file, 1 = dir) | u32 path_len | path bytes +
#              pad | u32 size | data bytes + pad
# Helpers come before their users. Returns entries loaded, or -1.

import kmb
import kvfs

def pad4(n):
  # round up to a multiple of 4 with integer division (safe `/` is Float)
  unsafe:
    I64 x = n
    return (x + 3) / 4 * 4

def load_module(idx):
  if kmb.mods_count() <= idx:
    return -1
  base = kmb.mod_start(idx)
  if base == 0 or kmb.mod_len(idx) < 8:
    return -1
  if read_mem(base, 4) != "KRFS":
    return -1
  n = kmb.rd32(base + 4)
  if n < 0 or n > 4096:
    return -1
  off = base + 8
  stop = base + kmb.mod_len(idx)
  loaded = 0
  i = 0
  while i < n:
    if off + 12 > stop:
      return -1
    t = kmb.rd32(off)
    plen = kmb.rd32(off + 4)
    if t != 0 and t != 1:
      return -1
    if plen < 0 or plen > 1024:
      return -1
    path = read_mem(off + 8, plen)
    sizeoff = off + 8 + pad4(plen)
    if sizeoff + 4 > stop:
      return -1
    size = kmb.rd32(sizeoff)
    if size < 0:
      return -1
    data_off = sizeoff + 4
    if data_off + size > stop:
      return -1
    full = "/" + path
    if t == 1:
      if not kvfs.mkdirs(full):
        return -1
    else:
      if not kvfs.mkdirs(kvfs.split_parent(full)[0]):
        return -1
      if not kvfs.write(full, read_mem(data_off, size)):
        return -1
    loaded = loaded + 1
    off = data_off + pad4(size)
    i = i + 1
  return loaded

def load():
  return load_module(0)