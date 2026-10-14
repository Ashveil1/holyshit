seen = []
for a in argv():
  if not (a in seen):
    append(seen, a)
    print a
