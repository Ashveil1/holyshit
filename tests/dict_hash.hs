# dicts past 8 keys switch to a hash index: lookups, overwrites, growth,
# prefix keys, the empty key, equality and order must behave like the small case
d = {}
i = 0
while i < 300:
  d["k" + str(i)] = i
  i = i + 1
print len(d)
s = 0
i = 0
while i < 300:
  s = s + d["k" + str(i)]
  i = i + 1
print s
i = 0
while i < 300:
  d["k" + str(i)] = i * 2
  i = i + 3
print len(d)
print d["k0"]
print d["k1"]
print d["k3"]
print d["k297"]
e = {}
e[""] = 1
e["a"] = 2
e["ab"] = 3
e["abc"] = 4
e["b"] = 5
e["ba"] = 6
e["bab"] = 7
e["abcd"] = 8
e["abcde"] = 9
e["c"] = 10
print e[""] + e["a"] + e["ab"] + e["abc"] + e["b"] + e["ba"] + e["bab"] + e["abcd"] + e["abcde"] + e["c"]
print e
f = {}
for k in e:
  f[k] = e[k]
print f == e
f["zz"] = 1
print f == e
n = 0
for k in d:
  n = n + 1
print n
try:
  print d["nope"]
except as m:
  print m
try:
  print e["abcdef"]
except as m:
  print m
