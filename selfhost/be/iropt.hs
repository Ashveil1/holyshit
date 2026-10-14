import pyrt
LIM = 1 << 60
def _isint(v):
  return pyrt.py_type(v) == "int"
def _fold(op, a, b):
  if op == "+":
    return bounded_add(a, b)
  elif op == "-":
    return bounded_sub(a, b)
  elif op == "*":
    return bounded_mul(a, b)
  elif op == "<":
    return a < b
  elif op == ">":
    return a > b
  elif op == "<=":
    return a <= b
  elif op == ">=":
    return a >= b
  elif op == "==":
    return a == b
  elif op == "!=":
    return a != b
  else:
    return null
  return r if 0 - LIM < r and r < LIM else null
def _walk(v, out):
  if pyrt.py_isinstance(v, ["str"]):
    if pyrt.py_startswith(v, "%"):
      pyrt.py_add(out, v)
  elif pyrt.py_isinstance(v, ["list", "tuple"]):
    for x in v:
      _walk(x, out)
  elif pyrt.py_isinstance(v, ["dict"]):
    for x in pyrt.py_values(v):
      _walk(x, out)
def _uses(ins, out):
  for k, v in pyrt.py_items(ins):
    if k != "dest":
      _walk(v, out)
def optimize_func(fn):
  consts = {}
  n_fold = 0
  for b in fn["blocks"]:
    for ii, ins in pyrt.py_enumerate(b["instrs"]):
      if ins["op"] == "const":
        consts[ins["dest"]] = ins["val"]
      elif ins["op"] == "bin":
        _t52 = [pyrt.py_get(consts, ins["l"], null), pyrt.py_get(consts, ins["r"], null)]
        l = _t52[0]
        r = _t52[1]
        if ins["l"] in consts and ins["r"] in consts and _isint(l) and _isint(r):
          v = _fold(ins["binop"], l, r)
          if v != null:
            d = ins["dest"]
            line = ins["line"]
            b["instrs"][ii] = {"op": "const", "line": line, "dest": d, "val": v}
            consts[d] = v
            n_fold = n_fold + 1
  while true:
    used = pyrt.py_set(null)
    for b in fn["blocks"]:
      for ins in b["instrs"]:
        _uses(ins, used)
      tm = b["term"]
      if tm != null:
        _uses(tm, used)
    dropped = 0
    for b in fn["blocks"]:
      keep = []
      for ins in b["instrs"]:
        if ins["op"] == "const" and not (ins["dest"] in used):
          dropped = dropped + 1
        else:
          append(keep, ins)
      b["instrs"] = keep
    if not dropped:
      break
  return n_fold
def optimize_module(m):
  if env("HS_NOOPT"):
    return 0
  total = 0
  for fn in pyrt.py_values(m["funcs"]):
    total = total + optimize_func(fn)
  return total
def bounded_add(a, b):
  if b > 0 and a >= LIM - b:
    return null
  if b < 0 and a <= 0 - LIM - b:
    return null
  r = a + b
  if r <= 0 - LIM or r >= LIM:
    return null
  return r
def bounded_sub(a, b):
  if b > 0 and a <= 0 - LIM + b:
    return null
  if b < 0 and a >= LIM + b:
    return null
  r = a - b
  if r <= 0 - LIM or r >= LIM:
    return null
  return r
def bounded_mul(a, b):
  if a == 0 or b == 0:
    return 0
  if a <= 0 - LIM or a >= LIM or b <= 0 - LIM or b >= LIM:
    return null
  neg = false
  if a < 0:
    neg = not neg
  if b < 0:
    neg = not neg
  if a < 0:
    a = 0 - a
  if b < 0:
    b = 0 - b
  r = 0
  while b > 0:
    if b & 1:
      if r >= LIM - a:
        return null
      r = r + a
    b = b >> 1
    if b > 0:
      if a >= LIM - a:
        return null
      a = a + a
  return 0 - r if neg else r
