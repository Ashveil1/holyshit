f = str
print f(65)
print f
print f == f
g = str
print f == g
n = len
print n("abc")
print n([1, 2])
p = append
l = []
p(l, 1)
p(l, "two")
print l
r = range
print r(3)
print r(2, 5)
s = split
print s("a,b")
j = join
print j("-", ["x", "y"])
def apply(fn, v):
  return fn(v)
print apply(f, 7)