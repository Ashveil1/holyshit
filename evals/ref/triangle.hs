n = int(argv()[0])
for i in range(1, n + 1):
  line = ""
  for j in range(i):
    line = line + "*"
  print line
