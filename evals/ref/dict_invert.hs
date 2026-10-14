a = argv()
d = {}
i = 0
while i + 1 < len(a):
  d[a[i]] = a[i + 1]
  i = i + 2
for k in keys(d):
  print d[k] + "=" + k
