x = 7
name = "hs"
print f"hello {name}!"
print f"{x} + {x} = {x + x}"
print f"{{braces}} {x}"
print f"plain"
print f"{x}"
print f"{name}{x}{name}"
l = [1, 2, 3]
print f"len={len(l)} first={l[0]} sum={l[0] + l[1]}"
d = {"a": 1}
print f"{d}"
print f"{1.5} {true} {null}"
def sq(n):
  return n * n
print f"sq={sq(5)} tab\there"
print len(f"abc{x}")
