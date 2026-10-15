# std.bitmap — bit sets over raw bytes (physical frame allocators, GDT/IDT
# slots, dirty-bit maps, ...). One bit per unit, LSB first:
#   bit i  ->  byte i / 8,  mask 1 << (i % 8)
# Every function takes the bitmap base as an Int address (from alloc()).
# Works on every backend because it only uses load8/store8.
# NOTE: the x64 backend resolves module-level names statically, so helpers are
# defined before the functions that call them (order matters for xbuild).
def bit_get(base, i):
  unsafe:
    I64 b = load8(as_ptr(base) + i / 8)
    return b >> (i % 8) & 1
def bit_set(base, i):
  unsafe:
    Ptr p = as_ptr(base) + i / 8
    I64 b = load8(p)
    store8(p, b | (1 << (i % 8)))
def bit_clear(base, i):
  unsafe:
    Ptr p = as_ptr(base) + i / 8
    I64 b = load8(p)
    store8(p, b & ~(1 << (i % 8)))
def bit_toggle(base, i):
  unsafe:
    Ptr p = as_ptr(base) + i / 8
    I64 b = load8(p)
    store8(p, b ^ (1 << (i % 8)))
def bit_reserve(base, start, count):
  i = start
  stop = start + count
  while i < stop:
    bit_set(base, i)
    i = i + 1
def bit_release(base, start, count):
  i = start
  stop = start + count
  while i < stop:
    bit_clear(base, i)
    i = i + 1
def bit_count_used(base, nbits):
  n = 0
  i = 0
  while i < nbits:
    if bit_get(base, i) == 1:
      n = n + 1
    i = i + 1
  return n
def bit_find(base, nbits):
  i = 0
  while i < nbits:
    if bit_get(base, i) == 0:
      return i
    i = i + 1
  return -1
def bit_find_from(base, nbits, start):
  i = start
  while i < nbits:
    if bit_get(base, i) == 0:
      return i
    i = i + 1
  return -1
def bit_alloc(base, nbits):
  return bit_find(base, nbits)
def bit_run_free(base, start, want):
  n = 0
  i = start
  stop = start + want
  while i < stop:
    if bit_get(base, i) == 1:
      break
    n = n + 1
    i = i + 1
  return n
def bit_alloc_run(base, nbits, want, start):
  if want < 1:
    return -1
  i = start
  last = nbits - want
  while i <= last:
    if bit_run_free(base, i, want) == want:
      return i
    i = i + 1
  return -1
def bit_alloc_run_any(base, nbits, want):
  return bit_alloc_run(base, nbits, want, 0)
def bit_take(base, nbits, start, want):
  i = bit_alloc_run(base, nbits, want, start)
  if i < 0:
    return -1
  bit_reserve(base, i, want)
  return i
def bitmap_bytes(nbits):
  unsafe:
    I64 n = nbits
    return (n + 7) / 8