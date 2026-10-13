def greet(name, greeting="hello", punct="!"):
  return greeting + ", " + name + punct
print greet("a")
print greet("b", "hi")
print greet("c", "yo", "?")
def area(w, h=w2()):
  return w * h
def w2():
  return 3
print area(4), area(4, 5)
def f(x, y=1 + 2):
  return x * y
print f(2), f(2, 10), f(f(1))
