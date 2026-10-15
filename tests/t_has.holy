d = {"a": 1, "b": 2}
print has(d, "a"), has(d, "z")
e = {}
print has(e, "a")
n = {1: "x", 2: "y"}
print has(n, 1), has(n, 3)
big = {}
for i in range(20):
  big[i] = i * i
print has(big, 19), has(big, 20)
f = has
print f(d, "b")
def get(dd, k, dflt):
  if has(dd, k):
    return dd[k]
  return dflt
print get(d, "z", 7), get(d, "a", 7)
