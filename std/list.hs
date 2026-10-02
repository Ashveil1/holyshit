# std.list — higher-order list helpers (pure hs, closure showcase)
def map(f, xs):
  out = []
  for x in xs:
    append(out, f(x))
  return out

def filter(f, xs):
  out = []
  for x in xs:
    if f(x):
      append(out, x)
  return out

def fold(f, acc, xs):
  for x in xs:
    acc = f(acc, x)
  return acc

def any(f, xs):
  for x in xs:
    if f(x):
      return true
  return false

def all(f, xs):
  for x in xs:
    if not f(x):
      return false
  return true
