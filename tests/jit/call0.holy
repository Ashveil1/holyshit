extern:
  I64 mmap(Ptr addr, U64 size, I64 prot, I64 flags, I64 fd, I64 off)
  I64 mprotect(Ptr addr, U64 size, I64 prot)
  I64 munmap(Ptr addr, U64 size)
ptr = mmap(0, 4096, 3, 34, -1, 0)
assert ptr != -1
unsafe:
  Ptr p = as_ptr(ptr)
  # mov rax, -42; ret
  store8(p, 72)
  store8(p + 1, 199)
  store8(p + 2, 192)
  store32(p + 3, -42)
  store8(p + 7, 195)
assert mprotect(ptr, 4096, 5) == 0
unsafe:
  I64 result = call0(p)
  print result
# Repeat through a nested function: entry must maintain stack alignment.
def invoke(addr):
  unsafe:
    I64 result = call0(as_ptr(addr))
    print result
invoke(ptr)
assert munmap(ptr, 4096) == 0
try:
  unsafe:
    I64 bad = call0(as_ptr(0))
except:
  print "null rejected"
