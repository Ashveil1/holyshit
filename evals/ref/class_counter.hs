class Counter:
  def __init__(self):
    self.n = 0
  def inc(self):
    self.n = self.n + 1
  def get(self):
    return self.n

c = Counter()
for i in range(int(argv()[0])):
  c.inc()
print c.get()
