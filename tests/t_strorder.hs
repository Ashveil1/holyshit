# string ordering: a longer string can still sort before a shorter one, so
# the comparator has to scan the shared prefix before falling back to the
# length. x_str_cmp used to decide on length alone, which also made `ls`
# reverse its result.
print "ab" < "b"
print "b" < "ab"
print "abc" < "abd"
print "abd" < "abc"
print "a" < "ab"
print "ab" < "a"
print "abc" < "abcd"
print "x" < "y"
print "y" < "x"
print "" < "a"
print "a" < ""
# sorting shows up through ls, which sorts like sorted(os.listdir())
base = "/tmp/opencode/hs_strsort"
mkdir(base)
names = ["m.txt", "a.txt", "z.txt", "b.txt", "aa.txt", "ab.txt"]
for n in names:
  write_text(base + "/" + n, "x")
print ls(base)
# a prefix key and a longer key must both resolve in a Dict
d = {"ab": 1, "b": 2, "abc": 3, "": 4}
print d["ab"]
print d["b"]
print d["abc"]
print d[""]
print len(d)