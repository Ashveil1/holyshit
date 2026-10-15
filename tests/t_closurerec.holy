# a nested def that calls itself: the Func captures its own name, which is
# only bound after the closure object exists. (Mutual recursion between
# nested defs is a documented native limitation, so only self-recursion
# belongs in the shared corpus.)
def factw():
  def fact(n):
    if n <= 1:
      return 1
    return n * fact(n - 1)
  return fact(5)

print factw()

# the self-capture sits next to a normal capture of an outer local
def make(start):
  def walk(n):
    if n <= 0:
      return start
    return walk(n - 1)
  return walk(4)

print make(99)

def deep():
  a = 1
  def bump():
    return a + 1
  def again():
    return bump() * 10
  return again()

print deep()