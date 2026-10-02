# Str / Bool / Null values in the x64 backend (tagged representation)
def fib(k):
  if k < 2:
    return k
  return fib(k - 1) + fib(k - 2)

s = "ab"
print s
print len(s)
t = s + "cd"
print t
print len(t)
print t == "abcd"
print t == "ab"
print t < "abce"
print t > "abb"
print s + t
print ""
b = 3 < 4
print b
print not b
print b and 7
print 0 or 12
print null
print true
print false
print str(1234)
print str(-99)
print str(true)
print str(null)
n = 0
if n:
  print "bad"
else:
  print "zero is false"
e = ""
if e:
  print "bad2"
else:
  print "empty str is false"
print fib(12)
print len(str(fib(10)))
