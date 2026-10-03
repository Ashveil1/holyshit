import mod_m
import mod_useside

print mod_m.double(21)
print mod_m.PI
mod_m.PI = 4
print mod_m.PI
print mod_m.greet("hs")
print mod_m.bump()
print mod_m.bump()
print mod_m.get()
print mod_m.ITEMS
append(mod_m.ITEMS, 4)
print mod_m.ITEMS
print mod_useside.plusone(10)
print mod_useside.mod_side.VAL
print mod_m

def f():
  import mod_m
  return mod_m.double(8)

print f()
print f()
import mod_m
print mod_m.PI
