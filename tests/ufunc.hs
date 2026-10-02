def get_eight():
  v = 0
  unsafe:
    Ptr p = alloc(8)
    *p = 8
    v = *p
  return v

print get_eight()
unsafe:
  I64 g = 7
print g * 2
