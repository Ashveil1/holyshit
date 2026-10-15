# read_mem(ptr, nbytes): raw memory -> Str, on every backend
def poke3():
  unsafe:
    Ptr p = alloc(64)
    store8(p, 104)
    store8(p + 1, 105)
    store8(p + 2, 33)
    return as_int(p)

def poke_bin():
  unsafe:
    Ptr q = alloc(16)
    store8(q, 65)
    store8(q + 1, 0)
    store8(q + 2, 66)
    store8(q + 3, 255)
    return as_int(q)

p = poke3()
s = read_mem(p, 3)
print s
print s == "hi!"
print len(s)

# embedded NULs and high bytes survive (byte-preserving)
q = poke_bin()
t = read_mem(q, 4)
print len(t)
print t == read_mem(q, 4)
print find(t, "B")

# empty read is fine, offsets work
print read_mem(p, 0) == ""
print read_mem(p + 1, 2) == "i!"

# errors keep interp wording on every backend
try:
  print read_mem(p, -1)
except as e:
  print e

# reachable from nested functions (closures) too
def nested(p):
  n = 2
  def mid():
    return read_mem(p, n)
  return mid

print nested(p)()
# NUL bytes survive a round trip through a closure too (not printed
# raw: native's print stops at the first NUL)
print len(nested(q)())
print nested(q)() == read_mem(q, 2)
