abc = "abcdefghijklmnopqrstuvwxyz"
k = int(argv()[1])
out = ""
for ch in argv()[0]:
  i = find(abc, ch)
  if i < 0:
    out = out + ch
  else:
    out = out + abc[(i + k) % 26]
print out
