class Point:
  def __init__(self, x, y):
    self.x = x
    self.y = y
  def add(self, o):
    return Point(self.x + o.x, self.y + o.y)
  def norm2(self):
    return self.x * self.x + self.y * self.y
  def move(self, dx):
    self.x = self.x + dx
class Counter:
  def __init__(self):
    self.n = 0
  def inc(self):
    self.n = self.n + 1
    return self.n
p = Point(3, 4)
q = Point(1, 2)
r = p.add(q)
print r.x, r.y
print p.norm2()
p.move(10)
print p.x
c = Counter()
c.inc()
c.inc()
print c.inc()
print c.n
items = []
for i in range(3):
  items.append(Point(i, i * 2))
total = 0
for it in items:
  total = total + it.norm2()
print total
print f"point {p.x},{p.y}"
class Empty:
  pass
e = Empty()
print len(e)
