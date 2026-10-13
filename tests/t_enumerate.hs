for i, x in enumerate(["a", "b", "c"]):
  print i, x
for a, b in [[1, 2], [3, 4]]:
  print a + b
def f(ps):
  t = 0
  for k, v in ps:
    t = t + k * v
  return t
print f([[1, 2], [3, 4]])
print [p[0] + p[1] for p in enumerate([5, 6, 7])]
for k, v, z in [[1, 2, 3]]:
  print k + v + z
print len(enumerate([]))
