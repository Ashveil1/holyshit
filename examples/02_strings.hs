# tour 02: Str — ตัด ต่อ หา แยก ชิ้น
# รัน: python3 interp.py examples/02_strings.hs

s = "  hello, holyshit  "
print "[" + s + "]"
print len(s)

# Str อินเดกซ์คือ byte — a[i] ได้ตัวอักษร 1 ตัว
print s[2]
print s[0] + s[1]

# แยก/ต่อ
clean = "a,b,c,d"
parts = split(clean, ",")
print len(parts)
print parts[0]
print parts[3]
print join("-", ["x", "y", "z"])
print find("hello", "ll")
print find("hello", "zz")

# slicing: [a:b] เหมือน Python (ปล่อยข้างไว้ได้)
print "hello"[1:4]
print "hello"[0:1] + "..."
print "abcdef"[4:]
print "abcdef"[:-2]

# str() แปลงค่าใด ๆ
print str(123) + "!"
print str(7 * 6)
print str([1, 2, 3])
print str(true)

# ต่อได้เฉพาะ Str + Str — ต้องแปลงเอง ไม่มี implicit
n = 7
print "n=" + str(n)
