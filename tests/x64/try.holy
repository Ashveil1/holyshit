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

try:
  print 1 / 0
except as e:
  print e

try:
  print 9(9)
except as e:
  print e

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

try:
  print "body"
finally:
  print "fin"

try:
  raise "x"
except as e:
  print e
finally:
  print "fin2"

def f(n):
  try:
    if n == 0:
      return "zero"
    print n
  finally:
    print "cleanup"
  return "after"

print f(0)
print f(1)

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

try:
  try:
    raise "deep"
  finally:
    print "inner-fin"
except as e:
  print e
print "done"

# a raise inside an except must still run that try's finally (interp parity)
try:
  try:
    raise "boom"
  except as e:
    print "saw", e
    raise "rethrown"
  finally:
    print "fin-before-rethrow"
except as e:
  print "outer saw", e

try:
  try:
    raise "boom"
  except as e:
    print "saw", e
    q = 1 + "a"
  finally:
    print "fin-before-typeerror"
except as e:
  print "outer saw", e
print "end"
