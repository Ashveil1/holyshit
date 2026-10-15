print "hs xkernel boot"

def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print "fib:", fib(10)
unsafe:
  I64 i = 0
  I64 s = 0
  while i < 10:
    s = s + i
    i = i + 1
  print s
  Ptr p = alloc(32)
  *p = 7
  print *p
print "halted"
