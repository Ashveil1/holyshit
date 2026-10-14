# Copy/concat must handle payloads at allocator alignment boundaries.
for n in [0, 1, 7, 8, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 128, 129]:
  a = ""
  i = 0
  while i < n:
    a = a + "x"
    i = i + 1
  b = "prefix" + a + "suffix"
  c = join("", split(b, "x"))
  print n, len(a), len(b), b[6:6 + n] == a, c
  print len(a + a), (a + "")[0:n] == a, ("" + a) == a
  print len(a + "\0" + a), len(a + "ก")
keep = []
i = 0
while i < 5000:
  append(keep, "v" + str(i))
  i = i + 1
j = 0
while j < 200000:
  garbage = "temporary" + str(j)
  j = j + 1
print keep[0], keep[4999], len(keep)
