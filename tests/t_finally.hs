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

n = 0
while n < 3:
  try:
    n = n + 1
    if n == 2:
      break
    print n
  finally:
    print "iter"
print "loop-done"

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

# same, but the handler raises a runtime error instead of raise
try:
  try:
    raise "boom"
  except as e:
    print "saw", e
    x = 1 + "a"
  finally:
    print "fin-before-typeerror"
except as e:
  print "outer saw", e
print "end"
