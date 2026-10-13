extern:
  Ptr malloc(U64 n)
  U0 free(Ptr p)
  Ptr gmtime_r(Ptr t, Ptr out)
t = malloc(8)
tm = malloc(64)
unsafe:
  store64(as_ptr(t), 86400 * 365)
gmtime_r(t, tm)
unsafe:
  print load32(as_ptr(tm))
  print load32(as_ptr(as_int(as_ptr(tm)) + 4))
  print load32(as_ptr(as_int(as_ptr(tm)) + 12))
  print load32(as_ptr(as_int(as_ptr(tm)) + 20))
free(t)
free(tm)
