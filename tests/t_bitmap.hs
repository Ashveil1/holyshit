# std.bitmap — unit tests (runs on interp, native and x64)
import std.bitmap

def fresh(nbits):
  nbytes = std.bitmap.bitmap_bytes(nbits)
  unsafe:
    I64 n = nbytes
    Ptr mem = alloc(4096)
    I64 i = 0
    while i < n:
      store8(mem + i, 0)
      i = i + 1
    return as_int(mem)

# sizes
print std.bitmap.bitmap_bytes(1), std.bitmap.bitmap_bytes(8)
print std.bitmap.bitmap_bytes(9), std.bitmap.bitmap_bytes(4096)

b = fresh(64)
print std.bitmap.bit_count_used(b, 64)

# single bits across byte boundaries
std.bitmap.bit_set(b, 0)
std.bitmap.bit_set(b, 7)
std.bitmap.bit_set(b, 8)
std.bitmap.bit_set(b, 63)
print std.bitmap.bit_get(b, 0), std.bitmap.bit_get(b, 7)
print std.bitmap.bit_get(b, 8), std.bitmap.bit_get(b, 63)
print std.bitmap.bit_get(b, 1), std.bitmap.bit_get(b, 62)
print std.bitmap.bit_count_used(b, 64)

# toggle and clear
std.bitmap.bit_toggle(b, 0)
print std.bitmap.bit_get(b, 0)
std.bitmap.bit_clear(b, 63)
print std.bitmap.bit_get(b, 63)
print std.bitmap.bit_count_used(b, 64)

# first free / full behaviour
b2 = fresh(16)
print std.bitmap.bit_find(b2, 16)
std.bitmap.bit_reserve(b2, 0, 16)
print std.bitmap.bit_find(b2, 16)
print std.bitmap.bit_count_used(b2, 16)
std.bitmap.bit_release(b2, 8, 8)
print std.bitmap.bit_find(b2, 16)
print std.bitmap.bit_count_used(b2, 16)

# find from an offset
b3 = fresh(32)
std.bitmap.bit_reserve(b3, 0, 10)
std.bitmap.bit_reserve(b3, 12, 5)
print std.bitmap.bit_find_from(b3, 32, 0)
print std.bitmap.bit_find_from(b3, 32, 10)
print std.bitmap.bit_find_from(b3, 32, 17)

# contiguous runs: this is what a PMM needs
b4 = fresh(64)
print std.bitmap.bit_alloc_run(b4, 64, 4, 0)
std.bitmap.bit_take(b4, 64, 0, 4)
print std.bitmap.bit_alloc_run(b4, 64, 4, 0)
print std.bitmap.bit_alloc_run(b4, 64, 4, 5)
print std.bitmap.bit_run_free(b4, 4, 8)
std.bitmap.bit_reserve(b4, 8, 1)
print std.bitmap.bit_run_free(b4, 4, 8)

# alloc_run cannot span a hole smaller than the run
b5 = fresh(32)
std.bitmap.bit_reserve(b5, 6, 1)
print std.bitmap.bit_alloc_run_any(b5, 32, 4)
print std.bitmap.bit_alloc_run(b5, 32, 4, 7)
print std.bitmap.bit_alloc_run(b5, 32, 7, 0)
print std.bitmap.bit_alloc_run(b5, 32, 0, 0)

# a frame allocator loop: 8 frames out, all distinct, then exhausted
b6 = fresh(8)
got = []
i = 0
while i < 8:
  idx = std.bitmap.bit_take(b6, 8, 0, 1)
  append(got, idx)
  i = i + 1
print got
print std.bitmap.bit_take(b6, 8, 0, 1)
std.bitmap.bit_release(b6, 3, 1)
print std.bitmap.bit_take(b6, 8, 0, 1)
