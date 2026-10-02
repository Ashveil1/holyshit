def counter():
  n = 0
  def inc():
    global seen
    seen = seen + 1
    return seen
  return inc

seen = 100
c = counter()
print c()
print c()
print seen

x = "outer"
def show():
  print x
show()

def add(a, b):
  return a + b
print add(3, 4)
print str([1, 2])
print int("42") + int(2.9)
print float("1.5") + 1
