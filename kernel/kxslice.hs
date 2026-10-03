# slicing + split/find/join on the freestanding kernel (no OS, no libc)
s = "hello, world"
print s[0:5]
print s[7:]
print split("a b  c")
print split("x,,y", ",")
print find("hello", "ll")
print find("hello", "z")
print join("-", ["a", "b"])
l = [10, 20, 30, 40]
print l[1:3]
print l[-2:]
print "kslice-done"
