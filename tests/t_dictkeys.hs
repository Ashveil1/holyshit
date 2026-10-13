# dict keys may be Str or Int
d = {}
d[1] = "one"
d[2] = "two"
d["k"] = "kay"
d[-5] = "neg"
print d[1]
print d[2]
print d["k"]
print d[-5]
print len(d)
d[1] = "uno"
print d[1]
print d
e = {10: "a", 20: "b", "z": 3}
print e[20]
for k in e:
  print k
total = 0
sq = {}
i = 0
while i < 20:
  sq[i] = i * i
  i = i + 1
for k in sq:
  total = total + sq[k]
print total
print len(sq)
print sq[19]
print d == {1: "uno", 2: "two", "k": "kay", -5: "neg"}
print {1: 2} == {1: 3}
print {"a": 2} == {"a": 3}
print {1: 2} == {1: 3}
print {1: 2} == {1: 2}
print {"a": "x", "b": [1, 2]} == {"a": "x", "b": [1, 2]}
print {"a": "x", "b": [1, 2]} == {"a": "x", "b": [1, 3]}
print {"a": 1} == {"b": 1}
print {} == {}
big = {}
n = 0
while n < 5000:
  big[n * 7 - 100] = n
  big["s" + str(n)] = -n
  n = n + 1
print len(big)
print big[-100]
print big[7 * 4999 - 100]
print big["s4999"]
print big[0 - 93]
sum = 0
for k in big:
  sum = sum + big[k]
print sum
big[-100] = 77
print big[-100]
print len(big)
