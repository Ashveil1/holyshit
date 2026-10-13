def pick(n):
  return "big" if n > 10 else "small"

def boom():
  print "boom evaluated"
  return 1

x = 5
print pick(3), pick(30)
print 1 if x > 3 else 0
y = 2 if x < 3 else 7 if x < 6 else 9
print y
print 10 + (1 if false else 2)
print "a" if true else boom()
print boom() if false else "skipped"
f = lambda n: n * 2 if n > 0 else 0 - n
print f(4), f(0 - 3)
z = null
print z if z else "none"
print "empty" if len([]) == 0 else "full"
print 0 if 0 else "zero-is-falsy"
