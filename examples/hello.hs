print "hello"

for i in range(5):
  print i

f = open("/tmp/opencode/hs_demo.txt", "w")
write(f, "hi holyshit")
close(f)

g = open("/tmp/opencode/hs_demo.txt", "r")
print read(g)
close(g)
