def fail(n):
  if n < 0:
    raise "negative!"
  return n

print fail(5)
try:
  print fail(-3)
except as e:
  print e

try:
  raise "boom"
except:
  print "caught"

try:
  try:
    raise "inner"
  except:
    raise
except as e:
  print e

try:
  unsafe:
    raise "unsafe-boom"
except as e:
  print e

print "done"
