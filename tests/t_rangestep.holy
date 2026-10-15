# range(a, b, step): a parse-time desugar, so every backend agrees.
t = []
for i in range(0, 10, 3):
  append(t, i)
print t
t = []
for i in range(10, 0, -3):
  append(t, i)
print t
t = []
for i in range(5, 5, 1):
  append(t, i)
print t
t = []
for i in range(5, 0, 1):
  append(t, i)
print t
t = []
for i in range(0, 5, -1):
  append(t, i)
print t
t = []
for i in range(0, 7, 7):
  append(t, i)
print t
t = []
for i in range(1, 8, 2):
  append(t, i)
print t
step = 4
t = []
for i in range(2, 20, step):
  append(t, i)
print t
step = 0 - 4
t = []
for i in range(20, 2, step):
  if i == 12:
    continue
  if i < 5:
    break
  append(t, i)
print t
tot = 0
for i in range(0, 20, 5):
  for j in range(i, 0, -2):
    tot = tot + j
print tot
def f(n):
  s = 0
  for k in range(n, 0, -1):
    s = s + k
  return s
print f(10)
for last in range(3, 12, 4):
  pass
print last
