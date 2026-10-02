unsafe:
  Ptr a = alloc(16)
  Ptr b = alloc(16)
  Ptr c = alloc(20)
  print as_int(b) - as_int(a)
  print as_int(c) - as_int(b)
  *a = 111
  *c = 222
  print *a + *c
  Ptr big = alloc(16777216)
  print big == null
  Ptr big2 = alloc(16777216)
  print big2 == null
print "ok"
