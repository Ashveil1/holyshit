# Self-hosted parser (core grammar). Reads a .hs file, prints the AST as JSON,
# which must equal `python3 selfhost/dump_parse.py FILE` (interp.parse_program).
# Not yet covered: class, extern, unsafe, lambda, f-strings (prints
# "unsupported" and fails).
import lexlib

KEYWORDS = ["def", "if", "elif", "else", "while", "for", "in", "return", "break", "continue", "global", "and", "or", "not", "true", "false", "null", "pass", "import", "try", "except", "as", "extern", "raise", "lambda", "class"]
METHODS = ["split", "find", "join", "append"]
P = {"t": [], "i": 0, "mods": {}}

def N(t, line, d):
  d["t"] = t
  d["line"] = line
  return d

def peek():
  return P["t"][P["i"]]

def nxt():
  x = P["t"][P["i"]]
  P["i"] = P["i"] + 1
  return x

def at(k):
  return peek()[0] == k

def atv(k, v):
  x = peek()
  return x[0] == k and x[1] == v

def pyrepr(v):
  return "'" + v + "'"

def expect(k):
  x = nxt()
  if x[0] != k:
    raise "expected " + k + ", got " + pyrepr(x[1]) + " at line " + str(x[2])
  return x

def expectv(k, v):
  x = nxt()
  if x[0] != k or x[1] != v:
    raise "expected " + v + ", got " + pyrepr(x[1]) + " at line " + str(x[2])
  return x

def skip_nl():
  while at("NEWLINE"):
    nxt()

def unsupported(what):
  raise "unsupported: " + what

def parse_body(top):
  body = []
  skip_nl()
  while not at("EOF") and not at("DEDENT"):
    if at("INDENT"):
      t = nxt()
      raise "unexpected indent at line " + str(t[2])
    append(body, parse_stmt())
    skip_nl()
  if not top:
    if at("DEDENT"):
      nxt()
    else:
      raise "expected indented block at line " + str(peek()[2])
  return body

def parse_block(line):
  if not at("NEWLINE"):
    raise "expected ':' then a new line at line " + str(line)
  nxt()
  if not at("INDENT"):
    raise "expected indented block at line " + str(peek()[2])
  nxt()
  return parse_body(false)

def end_of_stmt():
  return at("NEWLINE") or at("EOF") or at("DEDENT")

def valid_name(s):
  if len(s) == 0:
    return false
  if s[0] in lexlib.DIG:
    return false
  i = 0
  while i < len(s):
    if not (s[i] in lexlib.IDS or s[i] in lexlib.DIG):
      return false
    i = i + 1
  return true

def parse_stmt():
  t = peek()
  k = t[0]
  v = t[1]
  ln = t[2]
  if k == "ID":
    if v == "def":
      return parse_def()
    if v == "class" or v == "extern" or v == "unsafe" or v == "lambda":
      unsupported(v)
    if v == "if":
      return parse_if()
    if v == "while":
      nxt()
      c = parse_expr()
      expectv("OP", ":")
      return N("while", ln, {"cond": c, "body": parse_block(ln)})
    if v == "for":
      nxt()
      var = expect("ID")
      if var[1] in KEYWORDS:
        raise "bad loop variable '" + var[1] + "' at line " + str(var[2])
      it = expect("ID")
      if it[1] != "in":
        raise "expected 'in', got " + pyrepr(it[1]) + " at line " + str(it[2])
      e = parse_expr()
      expectv("OP", ":")
      return N("for", ln, {"var": var[1], "iter": e, "body": parse_block(ln)})
    if v == "return" or v == "raise":
      nxt()
      e = null
      if not end_of_stmt():
        e = parse_expr()
      return N(v, ln, {"val": e})
    if v == "break" or v == "continue" or v == "pass":
      nxt()
      return N(v, ln, {})
    if v == "global":
      nxt()
      names = [expect("ID")[1]]
      while atv("OP", ","):
        nxt()
        append(names, expect("ID")[1])
      return N("global", ln, {"names": names})
    if v == "print":
      return parse_print()
    if v == "import":
      nxt()
      name = expect("ID")
      if name[1] in KEYWORDS or not valid_name(name[1]):
        raise "bad module name '" + name[1] + "' at line " + str(name[2])
      full = name[1]
      while atv("OP", "."):
        nxt()
        part = expect("ID")
        if part[1] in KEYWORDS or not valid_name(part[1]):
          raise "bad module name '" + full + "." + part[1] + "' at line " + str(part[2])
        full = full + "." + part[1]
      first = split(full, ".")[0]
      P["mods"][first] = true
      return N("import", ln, {"name": full})
    if v == "try":
      nxt()
      expectv("OP", ":")
      body = parse_block(ln)
      ename = null
      ebody = null
      fbody = null
      if atv("ID", "except"):
        nxt()
        if atv("ID", "as"):
          nxt()
          ename = expect("ID")[1]
        expectv("OP", ":")
        ebody = parse_block(ln)
      if atv("ID", "finally"):
        nxt()
        expectv("OP", ":")
        fbody = parse_block(ln)
      if ebody == null and fbody == null:
        raise "try without except or finally at line " + str(peek()[2])
      return N("try", ln, {"body": body, "ename": ename, "ebody": ebody, "fbody": fbody})
    if v == "elif" or v == "else" or v == "except":
      raise "stray '" + v + "' at line " + str(ln)
  e = parse_expr()
  if e["t"] == "str" and not atv("OP", "="):
    return N("print", ln, {"args": [e]})
  if atv("OP", "="):
    nxt()
    rhs = parse_expr()
    if e["t"] == "var":
      if rhs["t"] == "var" and has(P["mods"], rhs["name"]):
        P["mods"][e["name"]] = true
      return N("set", ln, {"name": e["name"], "val": rhs})
    if e["t"] == "index":
      dot = null
      if has(e, "dot"):
        dot = e["dot"]
      return N("setindex", ln, {"obj": e["obj"], "idx": e["idx"], "val": rhs, "dot": dot})
    if e["t"] == "attr":
      return N("setattr", ln, {"obj": e["obj"], "name": e["name"], "val": rhs})
    raise "cannot assign to this at line " + str(ln)
  return N("expr", ln, {"val": e})

def parse_def():
  t = expect("ID")
  name = expect("ID")[1]
  expectv("OP", "(")
  params = []
  if not atv("OP", ")"):
    while true:
      a = expect("ID")[1]
      if a in params:
        raise "duplicate param '" + a + "' at line " + str(t[2])
      append(params, a)
      if atv("OP", ","):
        nxt()
        continue
      break
  expectv("OP", ")")
  expectv("OP", ":")
  return N("def", t[2], {"name": name, "params": params, "body": parse_block(t[2])})

def parse_if():
  t = expect("ID")
  c = parse_expr()
  expectv("OP", ":")
  then = parse_block(t[2])
  elifs = []
  els = []
  while atv("ID", "elif"):
    nxt()
    ec = parse_expr()
    expectv("OP", ":")
    append(elifs, [ec, parse_block(t[2])])
  if atv("ID", "else"):
    nxt()
    expectv("OP", ":")
    els = parse_block(t[2])
  return N("if", t[2], {"cond": c, "then": then, "elifs": elifs, "els": els})

def parse_args_until(close):
  args = []
  if not atv("OP", close):
    while true:
      append(args, parse_expr())
      if atv("OP", ","):
        nxt()
        continue
      break
  return args

def parse_print():
  t = expect("ID")
  args = []
  if end_of_stmt():
    return N("print", t[2], {"args": args})
  if atv("OP", "("):
    nxt()
    args = parse_args_until(")")
    expectv("OP", ")")
    return N("print", t[2], {"args": args})
  while true:
    append(args, parse_expr())
    if atv("OP", ","):
      nxt()
      continue
    break
  return N("print", t[2], {"args": args})

def parse_expr():
  return parse_or()

def parse_or():
  l = parse_and()
  while atv("ID", "or"):
    t = nxt()
    l = N("bin", t[2], {"op": "or", "l": l, "r": parse_and()})
  return l

def parse_and():
  l = parse_not()
  while atv("ID", "and"):
    t = nxt()
    l = N("bin", t[2], {"op": "and", "l": l, "r": parse_not()})
  return l

def parse_not():
  if atv("ID", "not"):
    t = nxt()
    return N("not", t[2], {"val": parse_not()})
  return parse_cmp()

def cmp_node(op, l, r, ln):
  if op == "in":
    return N("call", ln, {"fn": N("var", ln, {"name": "contains"}), "args": [r, l], "inop": true})
  if op == "not in":
    return N("not", ln, {"val": cmp_node("in", l, r, ln), "notin": true})
  return N("bin", ln, {"op": op, "l": l, "r": r})

def is_cmp_op(v):
  return v == "==" or v == "!=" or v == "<" or v == ">" or v == "<=" or v == ">="

def parse_cmp():
  l = parse_add()
  ops = []
  while true:
    x = peek()
    if x[0] == "OP" and is_cmp_op(x[1]):
      nxt()
      append(ops, [x[1], parse_add(), x[2]])
    elif x[0] == "ID" and x[1] == "in":
      nxt()
      append(ops, ["in", parse_add(), x[2]])
    elif x[0] == "ID" and x[1] == "not" and P["t"][P["i"] + 1][0] == "ID" and P["t"][P["i"] + 1][1] == "in":
      nxt()
      nxt()
      append(ops, ["not in", parse_add(), x[2]])
    else:
      break
  if len(ops) == 0:
    return l
  if len(ops) == 1:
    return cmp_node(ops[0][0], l, ops[0][1], ops[0][2])
  out = null
  prev = l
  for o in ops:
    one = cmp_node(o[0], prev, o[1], o[2])
    if out == null:
      out = one
    else:
      out = N("bin", o[2], {"op": "and", "l": out, "r": one})
    prev = o[1]
  return out

def parse_bits():
  l = parse_mul()
  while at("OP") and peek()[1] in ["<<", ">>", "&", "|", "^"]:
    t = nxt()
    l = N("bin", t[2], {"op": t[1], "l": l, "r": parse_mul()})
  return l

def parse_add():
  l = parse_bits()
  while at("OP") and peek()[1] in ["+", "-"]:
    t = nxt()
    l = N("bin", t[2], {"op": t[1], "l": l, "r": parse_bits()})
  return l

def parse_mul():
  l = parse_un()
  while at("OP") and peek()[1] in ["*", "/", "%"]:
    t = nxt()
    l = N("bin", t[2], {"op": t[1], "l": l, "r": parse_un()})
  return l

def parse_un():
  if atv("OP", "~"):
    t = nxt()
    return N("unot", t[2], {"val": parse_un()})
  if atv("OP", "-"):
    t = nxt()
    return N("neg", t[2], {"val": parse_un()})
  return parse_post()

def pure_recv(e):
  while e["t"] == "index" and has(e, "dot"):
    e = e["obj"]
  return e["t"] == "var"

def is_modref(e):
  while e["t"] == "attr":
    e = e["obj"]
  return e["t"] == "var" and has(P["mods"], e["name"])

def parse_post():
  e = parse_atom()
  while true:
    if atv("OP", "("):
      t = nxt()
      args = parse_args_until(")")
      expectv("OP", ")")
      if e["t"] == "index" and has(e, "dot") and e["dot"] in METHODS:
        e = N("call", t[2], {"fn": N("var", t[2], {"name": e["dot"]}), "args": [e["obj"]] + args, "method": e["dot"]})
      elif e["t"] == "index" and has(e, "dot"):
        if not pure_recv(e["obj"]):
          raise "method receiver must be a name or a field (assign it to a variable first) at line " + str(t[2])
        e = N("call", t[2], {"fn": e, "args": [e["obj"]] + args, "mcall": e["dot"]})
      else:
        e = N("call", t[2], {"fn": e, "args": args})
    elif atv("OP", "["):
      t = nxt()
      start = null
      if not atv("OP", ":"):
        start = parse_expr()
      if atv("OP", ":"):
        nxt()
        stop = null
        if not atv("OP", "]"):
          stop = parse_expr()
        expectv("OP", "]")
        e = N("slice", t[2], {"obj": e, "start": start, "stop": stop})
      else:
        expectv("OP", "]")
        e = N("index", t[2], {"obj": e, "idx": start})
    elif atv("OP", "."):
      t = nxt()
      nm = expect("ID")
      if is_modref(e):
        e = N("attr", t[2], {"obj": e, "name": nm[1]})
      else:
        e = N("index", t[2], {"obj": e, "idx": N("str", t[2], {"val": nm[1]}), "dot": nm[1]})
    else:
      return e

def hexval(s):
  n = 0
  i = 2
  while i < len(s):
    c = s[i]
    d = find("0123456789abcdef", c)
    if d < 0:
      d = find("ABCDEF", c) + 10
    n = n * 16 + d
    i = i + 1
  return n

def num_node(x):
  s = x[1]
  if len(s) > 1 and (s[1] == "x" or s[1] == "X"):
    return N("num", x[2], {"val": hexval(s), "raw": s})
  if find(s, ".") >= 0 or find(s, "e") >= 0 or find(s, "E") >= 0:
    return N("num", x[2], {"val": float(s), "raw": s})
  return N("num", x[2], {"val": int(s), "raw": null})

def parse_atom():
  t = peek()
  k = t[0]
  v = t[1]
  if k == "NUM":
    nxt()
    return num_node(t)
  if k == "STR":
    nxt()
    return N("str", t[2], {"val": v})
  if k == "FSTR":
    unsupported("f-string")
  if k == "ID" and (v == "true" or v == "false" or v == "null"):
    nxt()
    val = null
    if v == "true":
      val = true
    if v == "false":
      val = false
    return N("num", t[2], {"val": val})
  if k == "ID" and v == "print":
    raise "print is a statement, use: print ... at line " + str(t[2])
  if k == "ID" and v == "lambda":
    unsupported("lambda")
  if k == "ID":
    nxt()
    return N("var", t[2], {"name": v})
  if k == "OP" and v == "(":
    nxt()
    e = parse_expr()
    expectv("OP", ")")
    return e
  if k == "OP" and v == "[":
    nxt()
    items = parse_args_until("]")
    expectv("OP", "]")
    return N("list", t[2], {"items": items})
  if k == "OP" and v == "{":
    nxt()
    pairs = []
    if not atv("OP", "}"):
      while true:
        key = parse_expr()
        expectv("OP", ":")
        val = parse_expr()
        append(pairs, [key, val])
        if atv("OP", ","):
          nxt()
          continue
        break
    expectv("OP", "}")
    return N("dict", t[2], {"pairs": pairs})
  raise "expression expected, got " + pyrepr(v) + " at line " + str(t[2])

try:
  P["t"] = lexlib.lex(read_text(argv()[0]))
  body = parse_body(true)
  expect("EOF")
  print json_str(body)
except as e:
  print "error: " + e
  raise "parse failed"
