# tour 04: ฟังก์ชัน — closure, ค่า default ไม่มี, global
# รัน: python3 interp.py examples/04_functions.hs

def fib(n):
  if n < 2:
    return n
  return fib(n - 1) + fib(n - 2)

print fib(20)

# closure: จำค่าตอน def (ทั้ง interp และ native)
def counter(start):
  def step():
    return start + 1
  return step

add_one = counter(10)
print add_one()

def mul(a):
  def by(x):
    return a * x
  return by

print mul(3)(4)
print mul(10)(4)

# ฟังก์ชันเป็นค่าได้ ส่งต่อเป็น argument
def apply_twice(f, x):
  return f(f(x))

def inc(x):
  return x + 1

print apply_twice(inc, 5)

# global: เขียนชื่อระดับ module จากในฟังก์ชัน
hits = 0

def bump():
  global hits
  hits = hits + 1

bump()
bump()
print hits

# bare return ให้ Null
def nothing():
  return

print nothing()
