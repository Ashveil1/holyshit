# Parser normalization, matching interp.parse_program(raw=False).
import parselib
import lexlib
import pyrt
import prelude_data
def clone(x):
  return json_parse(json_str(x))
def defaults_find(x, table):
  if pyrt.py_type(x) == "dict":
    if pyrt.py_get(x, "t", null) == "def" and has(x, "defaults"):
      name = x["name"]
      if not has(table, name):
        table[name] = []
      append(table[name], x)
    for v in values(x):
      defaults_find(v, table)
  elif pyrt.py_islist(x):
    for v in x:
      defaults_find(v, table)
def defaults_fill(x, table):
  if pyrt.py_type(x) == "dict":
    if pyrt.py_get(x, "t", null) == "call" and x["fn"]["t"] == "var":
      name = x["fn"]["name"]
      if has(table, name) and len(table[name]) == 1:
        d = table[name][0]
        n = len(d["params"])
        k = len(d["defaults"])
        na = len(x["args"])
        if na >= n - k and na < n:
          x["args"] = x["args"] + clone(d["defaults"][na - (n - k):k])
    for v in values(x):
      defaults_fill(v, table)
  elif pyrt.py_islist(x):
    for v in x:
      defaults_fill(v, table)
def strip_defaults(x):
  if pyrt.py_type(x) == "dict":
    out = {}
    for k in keys(x):
      if k != "defaults":
        out[k] = strip_defaults(x[k])
    return out
  if pyrt.py_islist(x):
    out = []
    for v in x:
      append(out, strip_defaults(v))
    return out
  return x
def stamp(x, ln):
  if pyrt.py_type(x) == "dict":
    if has(x, "line"):
      x["line"] = ln
    for v in values(x):
      stamp(v, ln)
  elif pyrt.py_islist(x):
    for v in x:
      stamp(v, ln)
def step_for(x):
  if pyrt.py_type(x) != "dict" or pyrt.py_get(x, "t", null) != "for":
    return false
  it = x["iter"]
  return it["t"] == "call" and it["fn"]["t"] == "var" and it["fn"]["name"] == "range" and len(it["args"]) == 3 and not has(x, "tup")
def steps(x, counter):
  if pyrt.py_type(x) == "dict":
    for k in keys(x):
      x[k] = steps(x[k], counter)
    return x
  if pyrt.py_islist(x):
    out = []
    for child in x:
      f = steps(child, counter)
      if step_for(f):
        counter[0] = counter[0] + 1
        n = str(counter[0])
        ln = f["line"]
        args = f["iter"]["args"]
        for i, stem in [[0, "a"], [1, "b"], [2, "s"]]:
          append(out, {"t": "set", "line": ln, "name": "_r" + stem + n, "val": args[i]})
        tmpl = parselib.parse(pyrt.py_replace(prelude_data.RANGE_STEP_SRC, "N", n))
        stamp(tmpl, ln)
        loop = tmpl[3]
        first = loop["body"][0]
        first["name"] = f["var"]
        loop["body"] = [first] + f["body"]
        for st in tmpl[0:3]:
          append(out, st)
        append(out, loop)
      else:
        append(out, f)
    return out
  return x
def prelude_walk(x, calls, defs):
  if pyrt.py_islist(x):
    for v in x:
      prelude_walk(v, calls, defs)
    return null
  if pyrt.py_type(x) != "dict":
    return null
  t = pyrt.py_get(x, "t", null)
  if t == "call" and x["fn"]["t"] == "var" and x["fn"]["name"] in prelude_data.USER:
    append(calls, x)
  elif t == "def":
    defs[x["name"]] = true
  elif t == "extern":
    for d in x["decls"]:
      defs[d["name"]] = true
  for v in values(x):
    prelude_walk(v, calls, defs)
def prelude_add(nm, need):
  if nm in need:
    return null
  for dep in prelude_data.PRELUDE[nm][1]:
    prelude_add(dep, need)
  append(need, nm)
def inject_prelude(body, src):
  calls = []
  defs = {}
  prelude_walk(body, calls, defs)
  if len(calls) == 0:
    return body
  toks = lexlib.lex(src)
  assigned = {}
  for i in range(len(toks) - 1):
    tk = toks[i]
    nt = toks[i + 1]
    if tk[0] == "ID" and tk[1] in prelude_data.USER and nt[0] == "OP" and nt[1] == "=":
      assigned[tk[1]] = true
  found = {}
  for c in calls:
    nm = c["fn"]["name"]
    if has(defs, nm) or has(assigned, nm):
      continue
    if (nm == "min" or nm == "max") and len(c["args"]) == 2:
      nm = "_" + nm + "2"
      c["fn"]["name"] = nm
    found[nm] = true
  need = []
  for nm in pyrt.py_sorted(keys(found), null):
    prelude_add(nm, need)
  pre = []
  for nm in need:
    for st in parselib.parse(prelude_data.PRELUDE[nm][0]):
      st["prelude"] = true
      append(pre, st)
  return pre + body
def parse(src):
  body = parselib.parse(src)
  table = {}
  defaults_find(body, table)
  defaults_fill(body, table)
  defaults_fill(body, table)
  body = strip_defaults(body)
  body = steps(body, [0])
  return inject_prelude(body, src)
