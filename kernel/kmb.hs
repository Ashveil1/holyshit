# boot information — abstracts the bootloader's memory map.
#
# Two layouts are supported and detected by validation, not by trust:
#
#   spec (multiboot specification, GRUB and friends):
#     +0 total_size, +8 flags (bit0 = map present),
#     +52 mmap_length, +56 mmap_entry_size, +60 first entry
#     entry: +0 base (u64), +8 length (u64), +16 type (u32)
#
#   qemu (QEMU's own 88-byte boot info, *not* the spec layout):
#     +0 flags (bit6 = map present), +4 mem_lower, +8 mem_upper,
#     +12 boot_device, +48 map address
#     entry: +0 entry size (=20), +4 base (u64), +12 length (u64), +20 type
#
# Helpers come before their users: the x64 backend resolves module names
# statically. Every function returns a normal (tagged) Int.

ABI_NONE = 0
ABI_SPEC = 1
ABI_QEMU = 2

FRAME_BYTES = 4096

# the runtime's own bump allocator window, mirrored from x64gen.KHEAP_BASE /
# x64gen.KHEAP_SIZE. alloc() (and with it every Str/List payload, every
# new_table() and the frame bitmap) is served from here, so the physical
# memory manager must treat it as occupied.
RUNTIME_BUMP_BASE = 0x2000000
RUNTIME_BUMP_SIZE = 16 << 20

TYPE_USABLE = 1

SPEC_MMAP_LEN = 52
SPEC_MMAP_ENT = 56
SPEC_MMAP_FIRST = 60

QEMU_MMAP_ADDR = 48
QEMU_ENT_BYTES = 24

detected = 0
n_entries = 0
ent_bytes = 0

def rd32(addr):
  unsafe:
    return load32(as_ptr(addr))

def rd64(addr):
  # 64-bit field, returned as a tagged Int so safe code can use it
  unsafe:
    I64 v = load64(as_ptr(addr))
    return v

def info():
  return mb_info()

def magic():
  return mb_magic()

def detect():
  # returns the ABI, validating whatever the loader gave us
  global detected, ent_bytes, n_entries
  p = info()
  if p == 0:
    detected = ABI_NONE
    return ABI_NONE
  # QEMU: map pointer at +48 pointing at a plausible entry list
  qmap = rd32(p + QEMU_MMAP_ADDR)
  if qmap != 0:
    if rd32(qmap) == 20 or rd32(qmap) == QEMU_ENT_BYTES:
      t = rd32(qmap + 20)
      if t >= 1 and t <= 5:
        detected = ABI_QEMU
        ent_bytes = QEMU_ENT_BYTES
        return ABI_QEMU
  # spec: flags at +8 with the map bit set
  flags = rd32(p + 8)
  if flags & 1 != 0:
    mlen = rd32(p + SPEC_MMAP_LEN)
    esz = rd32(p + SPEC_MMAP_ENT)
    if mlen > 0 and esz >= 16:
      detected = ABI_SPEC
      ent_bytes = esz
      return ABI_SPEC
  detected = ABI_NONE
  return ABI_NONE

def abi():
  if detected == 0:
    detect()
  return detected

def usable():
  # true when a memory map was found
  return abi() != ABI_NONE

def count_entries():
  global n_entries
  a = abi()
  if a == ABI_QEMU:
    # no length field: the map is a list of fixed-size entries terminated by a
    # zero entry, inside the loader's reserved 0x500-byte area
    base = rd32(info() + QEMU_MMAP_ADDR)
    n = 0
    while n < 64:
      p = base + n * QEMU_ENT_BYTES
      if rd32(p) != 20:
        break
      if rd64(p + 4) > 0xFFFFFFFF:
        break
      n = n + 1
    n_entries = n
    return n
  if a == ABI_SPEC:
    mlen = rd32(info() + SPEC_MMAP_LEN)
    esz = rd32(info() + SPEC_MMAP_ENT)
    n = int(mlen / esz)
    n_entries = n
    return n
  n_entries = 0
  return 0

def entry_addr(i):
  a = abi()
  if a == ABI_QEMU:
    return rd32(info() + QEMU_MMAP_ADDR) + i * QEMU_ENT_BYTES
  if a == ABI_SPEC:
    return info() + SPEC_MMAP_FIRST + i * rd32(info() + SPEC_MMAP_ENT)
  return 0

def entry_base(p):
  if abi() == ABI_QEMU:
    return rd64(p + 4)
  return rd64(p)

def entry_len(p):
  if abi() == ABI_QEMU:
    return rd64(p + 12)
  return rd64(p + 8)

def entry_type(p):
  if abi() == ABI_QEMU:
    return rd32(p + 20)
  return rd32(p + 16)

def map_base(i):
  return entry_base(entry_addr(i))

def map_len(i):
  return entry_len(entry_addr(i))

def map_type(i):
  return entry_type(entry_addr(i))

def mem_lower():
  # KiB below 1 MiB, 0 when the loader does not say
  if abi() == ABI_QEMU:
    return rd32(info() + 4)
  if abi() == ABI_SPEC:
    return rd32(info() + 12)
  return 0

def mem_upper():
  # KiB above 1 MiB, 0 when the loader does not say
  if abi() == ABI_QEMU:
    return rd32(info() + 8)
  if abi() == ABI_SPEC:
    return rd32(info() + 16)
  return 0

def mods_count():
  # multiboot modules (QEMU -initrd lands here); 0 when none
  if abi() == ABI_QEMU:
    return rd32(info() + 20)
  if abi() == ABI_SPEC:
    return rd32(info() + 28)
  return 0

def mod_addr(i):
  if abi() == ABI_QEMU:
    return rd32(info() + 24) + i * 16
  if abi() == ABI_SPEC:
    return rd32(info() + 32) + i * 16
  return 0

def mod_start(i):
  return rd32(mod_addr(i))

def mod_end(i):
  return rd32(mod_addr(i) + 4)

def mod_len(i):
  return mod_end(i) - mod_start(i)
