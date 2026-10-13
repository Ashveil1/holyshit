print abs(0 - 5), abs(3), abs(0 - 2.5)
print min([3, 1, 2]), max([3, 1, 2]), min(4, 9), max(4, 9)
print min(["b", "a"]), max("x", "y")
print sum([1, 2, 3]), sum([])
print sorted([5, 2, 9, 1, 2]), sorted(["b", "c", "a"]), sorted([])
print reversed([1, 2, 3])
print upper("Hello, World 42"), lower("Hello, World 42")
xs = [3, 1, 2]
ys = sorted(xs)
print xs, ys
big = []
i = 0
while i < 200:
  append(big, i * 37 % 101)
  i = i + 1
s = sorted(big)
ok = true
i = 1
while i < len(s):
  if s[i - 1] > s[i]:
    ok = false
  i = i + 1
print ok, len(s), s[0], s[199]
print max(sorted(big)) - min(big)
