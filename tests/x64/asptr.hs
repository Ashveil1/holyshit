# as_ptr / as_int must convert exactly once: a raw pointer whose low bits
# are not 00 used to be unboxed a second time (shifted right by 2, or worse,
# rejected as "not an Int")
def roundtrip(n):
  unsafe:
    Ptr p = alloc(n)
    store8(p, 104)
    store8(p + n - 1, 122)
    store8(p + 54, 90)
    return as_int(p)

def at(addr, off):
  unsafe:
    Ptr q = as_ptr(addr + off)
    return load8(q)

def offset_ok(addr, off):
  unsafe:
    Ptr q = as_ptr(addr + off)
    return q == as_ptr(addr) + off

base = roundtrip(64)
print at(base, 0), at(base, 63)
print at(base, 1), at(base, 2), at(base, 3), at(base, 7)
print at(base, 54), offset_ok(base, 54), offset_ok(base, 1), offset_ok(base, 0)

# raw unsafe locals hold machine words already: no unboxing at all
unsafe:
  Ptr s = alloc(32)
  Ptr t = s + 5
  print as_int(t) == as_int(s) + 5
  print load8(as_ptr(as_int(t)))