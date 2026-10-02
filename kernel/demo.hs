print "hs kernel boot"

def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print "fib:", fib(10)

unsafe:
  # VGA text buffer: write 'H' (72) with attribute 7, then read back
  Ptr vga = as_ptr(753664)
  store8(vga, 72)
  store8(vga + 1, 7)
  print load8(vga)
  I64 i = 0
  I64 s = 0
  while i < 10:
    s = s + i
    i = i + 1
  print s

print 7 / 2
print "halted"
