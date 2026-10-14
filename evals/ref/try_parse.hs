for a in argv():
  try:
    print int(a) + 1
  except as e:
    print "bad"
