extern from "m":
  F64 sin(F64 x)
  F64 pow(F64 a, F64 b)
  F64 floor(F64 x)
  F64 ldexp(F64 x, I64 e)

extern:
  I64 printf(Str f, I64 n)
  I64 strlen(Str s)

print sin(0.0)
print pow(2.0, 10.0)
print pow(2, 3)
print floor(3.7)
print pow(2.0, 0.5) > 1.41
printf("n=%d\n", 42)
print strlen("abc") + 1
print ldexp(1.5, 4)
