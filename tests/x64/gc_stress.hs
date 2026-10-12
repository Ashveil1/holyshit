# GC stress: live data must survive many collections while garbage churns.
# Output must match interp.py exactly (differential test).
keep = []
d = {}
i = 0
while i < 2000:
  append(keep, "item" + str(i))
  d["k" + str(i)] = [i, "v" + str(i)]
  i = i + 1

def churn(n):
  j = 0
  t = 0
  while j < n:
    s = "garbage-string-" + str(j) + "-" + str(j * 7)
    l = [s, s + "x", [j, j + 1]]
    t = t + len(l[1])
    j = j + 1
  return t

def build(depth):
  if depth == 0:
    return [0]
  inner = build(depth - 1)
  junk = "pad" + str(depth) + "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
  return [depth, inner, len(junk)]

def make_counter(start):
  count = [start]
  def inc():
    count[0] = count[0] + 1
    return count[0]
  return inc

c = make_counter(10)
total = 0
round = 0
while round < 6:
  total = total + churn(60000)
  tree = build(40)
  total = total + c()
  round = round + 1

# verify everything is intact
bad = 0
i = 0
while i < 2000:
  if keep[i] != "item" + str(i):
    bad = bad + 1
  e = d["k" + str(i)]
  if e[0] != i or e[1] != "v" + str(i):
    bad = bad + 1
  i = i + 1
print total
print bad
print len(keep)
print len(d)
print tree[0]
print c()
big = []
k = 0
while k < 200000:
  append(big, "x" + str(k))
  k = k + 1
print len(big)
print big[199999]
print churn(80000)
print big[12345]
