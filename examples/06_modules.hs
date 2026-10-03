# tour 06: module + stdlib
# รัน: HSPATH=$PWD python3 interp.py examples/06_modules.hs
#
# import หาไฟล์จาก: โฟลเดอร์โปรแกรม -> HSPATH -> cwd
# std/ อยู่ในโฟลเดอร์ repo จึงต้องชี้ HSPATH ที่ตัว repo

import std.str
import std.list

def add(a, b):
  return a + b

def inc(x):
  return x + 1

def is_even(x):
  return x % 2 == 0

print std.str.trim("  padded  ")
print "[" + std.str.pad_left("7", 3) + "]"
print std.str.starts_with("holyshit", "holy")
print std.str.ends_with("holyshit", "shit")
print len(std.str.lines("a\nb\nc"))

xs = [1, 2, 3, 4]
print std.list.fold(add, 0, xs)
print std.list.map(inc, xs)
print std.list.filter(is_even, xs)
print std.list.any(inc, [0, 0, 1])
print std.list.all(inc, [1, 2, 3])

# closure ผ่านเข้า stdlib ได้
def adder(n):
  def add_n(x):
    return x + n
  return add_n

print std.list.map(adder(100), xs)
