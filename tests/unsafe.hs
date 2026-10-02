unsafe:
  Ptr p = alloc(16)
  *p = 4660
  print *p
  store8(p + 8, 255)
  store32(p + 12, 51966)
  print load8(p + 8)
  print load32(p + 12)
  I64 n = 10
  I64 total = 0
  while n > 0:
    total = total + n
    n = n - 1
  print total
  Ptr io = as_ptr(1016)
  print as_int(io)
  print p == null
  print io != null
  U64 big = 4000000000
  print big + 1
  print 7 / 2
  print 7 % 3
  print -7 / 2
print "done"
result = 0
unsafe:
  result = 123
print result
