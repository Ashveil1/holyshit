extern:
  I64 puts(Str s)
  U64 strlen(Str s)
  Ptr malloc(U64 n)
  U0 free(Ptr p)

extern from "m":
  F64 sin(F64 x)

extern from "ffic.c":
  I64 hs_add3(I64 a, I64 b, I64 c)

puts("from-ffi")
print strlen("hello")
print sin(0.0)
print hs_add3(1, 2, 3)
p = malloc(16)
print p == 0
free(p)
print "freed"
