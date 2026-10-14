best = argv()[0]
for a in argv():
  if len(a) > len(best):
    best = a
print best
