import std.heap

std.heap.heap_init(4096)
print std.heap.heap_free()
print std.heap.heap_nblocks()
a = std.heap.malloc(16)
print std.heap.heap_free()
b = std.heap.malloc(16)
print std.heap.heap_free()
print std.heap.malloc(99999999)
unsafe:
  store8(as_ptr(a), 65)
  print load8(as_ptr(a))
std.heap.free(a)
print std.heap.heap_free()
std.heap.free(b)
print std.heap.heap_free()
print std.heap.heap_nblocks()
