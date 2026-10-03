PI = 3

def double(x):
  return x * 2

def greet(name):
  return "hi " + name

N = 0

def bump():
  global N
  N = N + 1
  return N

def get():
  return N

ITEMS = [1, 2, 3]
