l = []
l.append("a,b")
l.append("c")
parts = l[0].split(",")
print parts
print ",".join(parts)
print l[1].find("c")
print "x y  z".split()
# nested receivers and chained calls
rows = ["1,2", "3,4"]
total = 0
for r in rows:
  for x in r.split(","):
    total = total + int(x)
print total
print "a-b-c".split("-")[1]
