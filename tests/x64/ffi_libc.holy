extern:
  I64 puts(Str s)
  U64 strlen(Str s)
  Ptr malloc(U64 n)
  U0 free(Ptr p)
  Str getenv(Str n)
  I64 abs(I64 x)
  I64 atoi(Str s)
  Str strchr(Str s, I64 c)
puts("from-ffi")
print strlen("hello")
p = malloc(16)
print p == 0
free(p)
print "freed"
print abs(-42)
print atoi("1234") + 1
print getenv("NOPE_XYZ_HS")
print strchr("hello world", 119)
print strchr("hello", 122)
def twice(s):
  return strlen(s) * 2
print twice("abcd")
f = abs
print f(-7)
