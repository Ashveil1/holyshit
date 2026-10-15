# try/except/finally/raise on the freestanding kernel (no OS, no libc)
try:
  print "k-try"
except:
  print "bad"

try:
  x = 1 + "a"
except as e:
  print e

try:
  raise "k-boom"
except as e:
  print e

try:
  print "k-body"
finally:
  print "k-fin"

def f(n):
  try:
    if n == 0:
      return "k-zero"
    raise "k-neg"
  except as e:
    print e
  finally:
    print "k-clean"
  return "k-after"

print f(0)
print f(1)

i = 0
while i < 3:
  i = i + 1
  try:
    if i == 2:
      continue
    print i
  finally:
    print "k-it"
print "ktry-done"

# error inside an except must still run that try's finally before unwinding
try:
  try:
    raise "k-inner"
  except as e:
    print e
    raise "k-outer"
  finally:
    print "k-fin-before-rethrow"
except as e:
  print e

try:
  try:
    raise "k-inner2"
  except as e:
    print e
    y = 1 + "a"
  finally:
    print "k-fin-before-typeerror"
except as e:
  print e
print "k-end"
