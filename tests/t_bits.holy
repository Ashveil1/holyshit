# bitwise operators: Ints only, in safe code and inside unsafe:
# precedence: bitwise binds tighter than + - but looser than * /
# variables and reuse
# shift by a variable, and the boundaries
# type errors and range errors keep interp wording
def show(label, v):
  print label, v
print 6 & 3
print 6 | 3
print 6 ^ 3
print ~0
print ~6
print 1 << 10
print 1024 >> 3
print 0x83 & ~0x10
print 0x83 | 0x10
print 0xFF ^ 0x0F
print ((1 + 2) << 2 | 1)
print 7 & 3 == 3
print -8 >> 1
print 5 & 3 + 1
print 255 & 0xF0 | 0x0F
print 1 + 2 & 6
print 12 & (6 * 2)
print 1 << 3 == 8
n = 6
print n & 3, n | 8, n ^ 3
n = n & 15
print n
s = 4
print 1 << s
print 1024 >> s
print 1 << 62 > 0
print 1 << 61 > 0
try:
  print 1 & "a"
except as e:
  print e
try:
  print "a" | 1
except as e:
  print e
try:
  print 1 << 100
except as e:
  print e
try:
  print 1 >> -1
except as e:
  print e
try:
  print ~"a"
except as e:
  print e
try:
  print true & 1
except as e:
  print e
unsafe:
  U64 mask = 0xFF
  U64 v = 0x1234
  print v & mask
  print v | 0xF0
  print v ^ 0xFFFF
  print ~v & 0xFFFF
  print v << 4
  print v >> 2
  Ptr p = as_ptr(0x1000)
  print as_int(p) & 0xFFF == 0