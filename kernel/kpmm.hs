# kernel physical memory manager — a real frame allocator built from the
# bootloader's memory map (see kmb for the supported layouts), in plain .hs.
#
# Layout:
#   - a bitmap with one bit per 4K frame (bit i set = frame i is in use)
#   - frames come from the usable (type 1) regions only
#   - the kernel image, low memory and the bitmap itself are reserved
#   - the pool is the largest usable region, which keeps allocation cheap and
#     makes one bitmap enough
#
# Helpers come before their users: x64 resolves module names statically.
import std.bitmap
import kmb

FRAME_BYTES = kmb.FRAME_BYTES

mmap_addr = 0
nregions = 0
pool_base = 0
pool_frames = 0
bitmap_addr = 0
bitmap_bytes = 0
reserved_frames = 0
ready_flag = false

def allocate_bitmap():
  # one zeroed, page-aligned block for the frame bitmap
  nbytes = (pool_frames + 7) / 8 + 8
  unsafe:
    Ptr t = alloc(nbytes + 8192)
    I64 a = as_int(t)
    I64 p = (a + 4095) & ~0xFFF
    I64 i = 0
    while i < nbytes:
      store8(as_ptr(p + i), 0)
      i = i + 1
    return p

def reserve(lo, hi):
  # mark every frame inside [lo, hi) as used
  if hi <= lo:
    return 0
  first = (lo - pool_base) / FRAME_BYTES
  last = (hi - pool_base + FRAME_BYTES - 1) / FRAME_BYTES
  if first < 0:
    first = 0
  if last > pool_frames:
    last = pool_frames
  i = first
  while i < last:
    std.bitmap.bit_set(bitmap_addr, i)
    i = i + 1
  return last - first

def scan():
  # count usable regions, remember the biggest one and where the map lives
  global nregions, pool_base, pool_frames, mmap_addr
  n = kmb.count_entries()
  mmap_addr = kmb.info()
  nregions = 0
  pool_base = 0
  pool_frames = 0
  i = 0
  while i < n:
    if kmb.map_type(i) == kmb.TYPE_USABLE:
      len = kmb.map_len(i) / FRAME_BYTES
      if len > pool_frames:
        pool_frames = len
        pool_base = kmb.map_base(i)
      nregions = nregions + 1
    i = i + 1
  return nregions

def init():
  # build the pool; returns the number of frames it manages
  global bitmap_addr, bitmap_bytes, reserved_frames, ready_flag
  if not kmb.usable():
    return 0
  if scan() == 0:
    return 0
  bitmap_bytes = (pool_frames + 7) / 8 + 8
  bitmap_addr = allocate_bitmap()
  # everything below the pool is off limits: boot structures, kernel image,
  # page tables and stack (the loader places its own data right after the
  # image, so the image end is the honest boundary)
  reserved_frames = reserve(0, pool_base)
  reserved_frames = reserved_frames + reserve(pool_base, image_end())
  # the bitmap lives in the kernel heap, so reserve it too
  reserved_frames = reserved_frames + reserve(bitmap_addr, bitmap_addr + bitmap_bytes)
  ready_flag = true
  return pool_frames

def ready():
  return ready_flag

def regions():
  return nregions

def total():
  return pool_frames

def used():
  if not ready_flag:
    return 0
  return std.bitmap.bit_count_used(bitmap_addr, pool_frames)

def available():
  return pool_frames - used()

def reserved():
  return reserved_frames

def base():
  return pool_base

def alloc(nframes):
  # contiguous run of nframes; page-aligned physical address, or 0
  if nframes < 1:
    return 0
  if not ready_flag:
    return 0
  i = std.bitmap.bit_take(bitmap_addr, pool_frames, 0, nframes)
  if i < 0:
    return 0
  return pool_base + i * FRAME_BYTES

def alloc_one():
  return alloc(1)

def free(paddr):
  # release a frame (or the first frame of a run) previously returned by alloc
  if not ready_flag:
    return false
  if paddr < pool_base:
    return false
  i = (paddr - pool_base) / FRAME_BYTES
  if i < 0 or i >= pool_frames:
    return false
  std.bitmap.bit_clear(bitmap_addr, i)
  return true

def free_run(paddr, nframes):
  # release nframes starting at paddr
  if not ready_flag:
    return false
  if paddr < pool_base:
    return false
  if nframes < 1:
    return false
  i = (paddr - pool_base) / FRAME_BYTES
  if i < 0 or i + nframes > pool_frames:
    return false
  std.bitmap.bit_release(bitmap_addr, i, nframes)
  return true