# user program: runs in ring 3, talks to the kernel only through syscalls
def greet(name):
  print "hello from ring 3, " + name

xs = []
i = 0
while i < 4:
  append(xs, "user line " + str(i))
  i = i + 1
print join("\n", xs)

greet("holyshit")
print "user arithmetic:", 6 * 7