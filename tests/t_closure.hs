def make(n):
  def add(x):
    return x + n
  return add

f = make(10)
print f(5)
print f(7)

def outer():
  a = 1
  b = 2
  def inner():
    return a + b
  return inner()

print outer()

def factw():
  def fact(n):
    if n <= 1:
      return 1
    return n * fact(n - 1)
  return fact(5)

print factw()

def mkv():
  v = 100
  def get():
    return v
  return get

g = mkv()
try:
  print g()
  print nosuchvar
except as e:
  print g()
  print "caught"
