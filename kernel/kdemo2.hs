print "t0:", ticks()
t = ticks()
while ticks() - t < 200:
  pass
print "t1:", ticks()

k = readkey()
while k == null:
  k = readkey()
print "key:", k

m0 = meminfo()
print m0
a = pmm_alloc(3)
print "alloc:", a
m1 = meminfo()
print m1
print "kdone"
