sq = lambda x: x * x
print sq(7)
add = lambda a, b: a + b
print add(3, 4)
def apply(f, v):
  return f(v)
print apply(lambda n: n + 100, 5)
def make_adder(k):
  return lambda x: x + k
a5 = make_adder(5)
print a5(10)
curried = lambda x: lambda y: x * 10 + y
print curried(4)(2)
fs = []
i = 0
while i < 3:
  append(fs, lambda z: z + 1)
  i = i + 1
print len(fs)
print fs[2](41)
def compose(f, g):
  return lambda x: f(g(x))
inc = lambda x: x + 1
dbl = lambda x: x * 2
print compose(inc, dbl)(5)
def mapl(f, xs):
  out = []
  for x in xs:
    append(out, f(x))
  return out
print mapl(lambda s: s + "!", ["a", "b"])
nop = lambda: 7
print nop()
r9 = (lambda x: x + 1)(9)
print r9
vals = [lambda: 1, lambda: 2]
print vals[1]()
r8 = 1 + (lambda q: q * 2)(4)
print r8
