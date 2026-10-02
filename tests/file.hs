f = open("/tmp/opencode/hs_test.txt", "w")
n = write(f, "hello file")
close(f)
print n
g = open("/tmp/opencode/hs_test.txt", "r")
print read(g)
close(g)
