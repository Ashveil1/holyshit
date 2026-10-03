s = "hello, world"
print s[0:5]
print s[7:]
print s[:5]
print s[:]
print s[-5:-1]
print s[20:30]
print s[3:3]
print s[5:2]
l = [10, 20, 30, 40, 50]
print l[1:3]
print l[:-1]
print l[2:]
print l[:]
print l[1:100]
print l[-100:2]
print s[1:4] + "!"
print len(s[2:5])
t = s[0:4]
print t == "hell"
u = l[1:3]
u[0] = 99
print u
print l

def head3(x):
  return x[:3]

print head3("abcdef")
print head3([7, 8, 9, 10])
w = ""
print w[:]
print w[0:5]
e = []
print e[0:9]
