def failer():
  return nosuchvar

try:
  print "ok1"
except:
  print "bad1"

try:
  x = 1 + "a"
  print "bad2"
except as e:
  print e

try:
  failer()
except as e:
  print e

try:
  try:
    y = [1][5]
  except as e:
    print e
  print "inner-done"
except:
  print "bad3"

n = 0
while n < 3:
  try:
    if n == 1:
      break
    print n
  except:
    print "never"
  n = n + 1
print "loop-done"
