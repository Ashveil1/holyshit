# scall(nr, a1..a6): raw syscalls on hosted Linux, same ABI the kernel
# serves in ring 3 (write=1, mmap=9, unknown nr -> -ENOSYS like Linux).
# Buffers come from alloc (no Str involved): addresses pass through as
# plain hs Ints.
def wbuf():
  unsafe:
    Ptr p = alloc(8)
    store8(p, 104)
    store8(p + 1, 105)
    store8(p + 2, 10)
    return as_int(p)

# write(1, "hi\n", 3) straight through the kernel, no hs print involved
r = scall(1, 1, wbuf(), 3, 0, 0, 0)
print "write returned", r

# mmap anonymous 1 page, then use it through unsafe
base = scall(9, 0, 4096, 3, 34, -1, 0)
print "mmap nonzero", base != 0
unsafe:
  Ptr q = as_ptr(base)
  store8(q, 65)
  store8(q + 4095, 90)
  print load8(q), load8(q + 4095)

# bogus number: Linux says -ENOSYS (-38), same value our kernel returns
print scall(9999, 0, 0, 0, 0, 0, 0)
print "ok scall"