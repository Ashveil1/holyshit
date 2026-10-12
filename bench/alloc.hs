i = 0
n = 0
while i < 5000000:
  s = "abc" + str(i)
  n = n + len(s)
  i = i + 1
print n
