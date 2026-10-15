# Self-hosted parser library: parse(src) -> AST (same dicts as interp.parse_program).
import lexlib

KEYWORDS = ["def", "if", "elif", "else", "while", "for", "in", "return", "break", "continue", "global", "and", "or", "not", "true", "false", "null", "pass", "import", "try", "except", "as", "extern", "raise", "lambda", "class", "assert"]
METHODS = ["split", "find", "join", "append"]
FFTYPE = ["U0", "I64", "U64", "F64", "Str", "Ptr"]
UTYPES = ["I64", "U64", "Ptr"]
# names a struct may not take (keep in sync with interp.BUILTINS)
BUILTINS = ["alloc", "append", "append_text", "argv", "as_int", "as_ptr", "close", "contains", "env", "exists", "find", "float", "has", "http_get", "input", "int", "join", "json_load", "json_parse", "json_save", "json_str", "keys", "len", "load32", "load64", "load8", "ls", "meminfo", "mkdir", "open", "pmm_alloc", "print", "range", "read", "read_mem", "read_text", "readkey", "split", "store32", "store64", "store8", "str", "system", "tcp_accept", "tcp_close", "tcp_connect", "tcp_listen", "tcp_recv", "tcp_send", "ticks", "values", "write", "write_text"]
P = {"unsafe": 0, "structs": {}, "t": [], "i": 0, "mods": {}, "hoist": [], "nlam": 0, "classes": {}}

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

def parse_body(top):
  body = []
  skip_nl()
  while not at("EOF") and not at("DEDENT"):
    if at("INDENT"):
      t = nxt()
      raise "unexpected indent at line " + str(t[2])
    outer = P["hoist"]
    P["hoist"] = []
    st = null
    if P["unsafe"] > 0:
      st = parse_ustmt()
    else:
      st = parse_stmt()
    for h in P["hoist"]:
      append(body, h)
    P["hoist"] = outer
    append(body, st)
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
    if v == "unsafe":
      return parse_unsafe()
    if v == "class":
      return parse_class()
    if v == "extern":
      return parse_extern()
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
      names = [var[1]]
      while atv("OP", ","):
        nxt()
        v2 = expect("ID")
        if v2[1] in KEYWORDS:
          raise "bad loop variable '" + v2[1] + "' at line " + str(v2[2])
        append(names, v2[1])
      it = expect("ID")
      if it[1] != "in":
        raise "expected 'in', got " + pyrepr(it[1]) + " at line " + str(it[2])
      e = parse_expr()
      expectv("OP", ":")
      body = parse_block(ln)
      if len(names) == 1:
        return N("for", ln, {"var": var[1], "iter": e, "body": body})
      P["nlam"] = P["nlam"] + 1
      tv = "_t" + str(P["nlam"])
      pre = []
      k = 0
      for nm in names:
        append(pre, N("set", ln, {"name": nm, "val": N("index", ln, {"obj": N("var", ln, {"name": tv}), "idx": N("num", ln, {"val": k, "raw": null})})}))
        k = k + 1
      return N("for", ln, {"var": tv, "iter": e, "body": pre + body, "tup": names})
    if v == "return" or v == "raise":
      nxt()
      e = null
      if not end_of_stmt():
        e = parse_expr()
      return N(v, ln, {"val": e})
    if v == "assert":
      nxt()
      c = parse_expr()
      m = null
      if atv("OP", ","):
        nxt()
        m = parse_expr()
      msg = m
      if m == null:
        msg = N("str", ln, {"val": "assertion failed"})
      return N("if", ln, {"cond": N("not", ln, {"val": c}), "then": [N("raise", ln, {"val": msg})], "elifs": [], "els": [], "asrt": true, "c": c, "m": m})
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

def parse_unsafe():
  t = expect("ID")
  if P["unsafe"] > 0:
    raise "unsafe inside unsafe at line " + str(t[2])
  expectv("OP", ":")
  if not at("NEWLINE"):
    raise "expected ':' then a new line at line " + str(t[2])
  nxt()
  if not at("INDENT"):
    raise "expected indented block at line " + str(peek()[2])
  nxt()
  P["unsafe"] = P["unsafe"] + 1
  body = []
  skip_nl()
  while not at("EOF") and not at("DEDENT"):
    if at("INDENT"):
      u = nxt()
      raise "unexpected indent at line " + str(u[2])
    append(body, parse_ustmt())
    skip_nl()
  if at("DEDENT"):
    nxt()
  else:
    raise "expected indented block at line " + str(peek()[2])
  P["unsafe"] = P["unsafe"] - 1
  return N("unsafe", t[2], {"body": body})

def parse_struct():
  t = expect("ID")
  nm = expect("ID")
  if nm[1] in KEYWORDS or nm[1] in UTYPES or nm[1] in FFTYPE or nm[1] in BUILTINS:
    raise "bad struct name '" + nm[1] + "' at line " + str(nm[2])
  expectv("OP", ":")
  if not at("NEWLINE"):
    raise "expected ':' then a new line at line " + str(t[2])
  nxt()
  if not at("INDENT"):
    raise "expected indented block at line " + str(peek()[2])
  nxt()
  fields = {}
  off = 0
  skip_nl()
  while not at("EOF") and not at("DEDENT"):
    if at("INDENT"):
      u = nxt()
      raise "unexpected indent at line " + str(u[2])
    ft = expect("ID")
    ftype = ""
    if ft[1] in UTYPES:
      ftype = ft[1]
    elif has(P["structs"], ft[1]) or ft[1] == nm[1]:
      ftype = ft[1]
    else:
      raise "bad field type '" + ft[1] + "' at line " + str(ft[2])
    if atv("OP", "*"):
      if ftype in UTYPES:
        raise "scalar type '" + ft[1] + "' cannot use '*' at line " + str(ft[2])
      nxt()
      ftype = "Ptr:" + ftype
    fn = expect("ID")
    if fn[1] in KEYWORDS:
      raise "bad field name '" + fn[1] + "' at line " + str(fn[2])
    if has(fields, fn[1]):
      raise "duplicate field '" + fn[1] + "' at line " + str(fn[2])
    count = 1
    if atv("OP", "["):
      nxt()
      cn = expect("NUM")
      cv = num_node(cn)["val"]
      if find(cn[1], ".") >= 0 or cv <= 0:
        raise "array size must be a positive integer at line " + str(cn[2])
      count = cv
      expectv("OP", "]")
    fields[fn[1]] = [ftype, off, count]
    off = off + 8 * count
    skip_nl()
  if at("DEDENT"):
    nxt()
  else:
    raise "expected indented block at line " + str(peek()[2])
  if len(fields) == 0:
    raise "struct needs at least one field at line " + str(t[2])
  lay = {"fields": fields, "size": off}
  if has(P["structs"], nm[1]) and P["structs"][nm[1]] != lay:
    raise "struct '" + nm[1] + "' redefined with a different layout at line " + str(nm[2])
  P["structs"][nm[1]] = lay
  return N("struct", t[2], {"name": nm[1]})

def parse_ustmt():
  t = peek()
  k = t[0]
  v = t[1]
  ln = t[2]
  if k == "ID" and v == "struct":
    return parse_struct()
  if k == "ID" and (v in UTYPES or has(P["structs"], v)) and P["i"] + 1 < len(P["t"]) and (P["t"][P["i"] + 1][0] == "ID" or has(P["structs"], v)):
    typ = nxt()[1]
    utype = typ
    if has(P["structs"], typ):
      expectv("OP", "*")
      utype = "Ptr:" + typ
    name = expect("ID")[1]
    init = null
    if atv("OP", "="):
      nxt()
      init = parse_expr()
    return N("udecl", ln, {"utype": utype, "name": name, "init": init})
  if k == "OP" and v == "*":
    nxt()
    ptr = parse_un()
    expectv("OP", "=")
    val = parse_expr()
    return N("store", ln, {"ptr": ptr, "val": val})
  if k == "ID" and v == "def":
    raise "def not allowed in unsafe at line " + str(ln)
  if k == "ID" and v == "for":
    raise "for not allowed in unsafe (use while) at line " + str(ln)
  if k == "ID" and v == "try":
    raise "try not allowed in unsafe (wrap the unsafe block instead) at line " + str(ln)
  if k == "ID" and v == "extern":
    raise "extern not allowed in unsafe (declare at top level) at line " + str(ln)
  if k == "ID" and v == "raise":
    nxt()
    e = null
    if not end_of_stmt():
      e = parse_expr()
    return N("raise", ln, {"val": e})
  if k == "ID" and v == "unsafe":
    raise "unsafe inside unsafe at line " + str(ln)
  if k == "ID" and v in ["if", "while", "return", "break", "continue", "pass", "global", "print"]:
    return parse_stmt()
  e = parse_expr()
  if atv("OP", "="):
    nxt()
    rhs = parse_expr()
    if e["t"] == "var":
      return N("set", ln, {"name": e["name"], "val": rhs})
    if e["t"] == "field":
      return N("fstore", ln, {"obj": e["obj"], "name": e["name"], "idx": e["idx"], "val": rhs})
    raise "cannot assign to this in unsafe (use *p = v for memory) at line " + str(ln)
  return N("expr", ln, {"val": e})

def parse_def():
  t = expect("ID")
  name = expect("ID")[1]
  expectv("OP", "(")
  params = []
  defaults = []
  if not atv("OP", ")"):
    while true:
      a = expect("ID")[1]
      if a in params:
        raise "duplicate param '" + a + "' at line " + str(t[2])
      append(params, a)
      if atv("OP", "="):
        nxt()
        append(defaults, parse_expr())
      elif len(defaults) > 0:
        raise "param '" + a + "' without a default follows one with a default at line " + str(t[2])
      if atv("OP", ","):
        nxt()
        continue
      break
  expectv("OP", ")")
  expectv("OP", ":")
  d = N("def", t[2], {"name": name, "params": params, "body": parse_block(t[2])})
  if len(defaults) > 0:
    d["defaults"] = defaults
  return d

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
  a = parse_or()
  if atv("ID", "if"):
    t = nxt()
    c = parse_or()
    if not atv("ID", "else"):
      raise "expected else, got " + pyrepr(peek()[1]) + " at line " + str(t[2])
    nxt()
    b = parse_expr()
    ln = t[2]
    sel = N("bin", ln, {"op": "or", "l": N("bin", ln, {"op": "and", "l": c, "r": N("list", ln, {"items": [a]})}), "r": N("list", ln, {"items": [b]})})
    return N("index", ln, {"obj": sel, "idx": N("num", ln, {"val": 0, "raw": null}), "tern": true, "c": c, "a": a, "b": b})
  return a

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
  if P["unsafe"] > 0 and atv("OP", "*"):
    t = nxt()
    return N("deref", t[2], {"val": parse_un()})
  if P["unsafe"] > 0 and atv("ID", "sizeof"):
    t = nxt()
    expectv("OP", "(")
    tn = expect("ID")
    if not tn[1] in UTYPES and not has(P["structs"], tn[1]):
      raise "sizeof wants a type, got '" + tn[1] + "' at line " + str(tn[2])
    expectv("OP", ")")
    return N("sizeof", t[2], {"stype": tn[1]})
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
      if P["unsafe"] > 0:
        idx = null
        if atv("OP", "["):
          nxt()
          idx = parse_expr()
          expectv("OP", "]")
        e = N("field", t[2], {"obj": e, "name": nm[1], "idx": idx})
      elif is_modref(e):
        e = N("attr", t[2], {"obj": e, "name": nm[1]})
      else:
        e = N("index", t[2], {"obj": e, "idx": N("str", t[2], {"val": nm[1]}), "dot": nm[1]})
    else:
      return e

def parse_listcomp(t, elem, h0):
  ln = t[2]
  h1 = len(P["hoist"])
  nxt()
  v = expect("ID")
  if v[1] in KEYWORDS:
    raise "bad loop variable '" + v[1] + "' at line " + str(v[2])
  if not atv("ID", "in"):
    raise "expected 'in', got " + pyrepr(peek()[1]) + " at line " + str(peek()[2])
  nxt()
  it = parse_or()
  h2 = len(P["hoist"])
  c = null
  if atv("ID", "if"):
    nxt()
    c = parse_or()
  expectv("OP", "]")
  pre = P["hoist"][h1:h2]
  inl = P["hoist"][h0:h1] + P["hoist"][h2:len(P["hoist"])]
  P["hoist"] = P["hoist"][0:h0]
  P["nlam"] = P["nlam"] + 1
  name = "_lc" + str(P["nlam"])
  r = name + "_r"
  app = N("expr", ln, {"val": N("call", ln, {"fn": N("var", ln, {"name": "append"}), "args": [N("var", ln, {"name": r}), elem]})})
  loop_body = inl + [app]
  if c != null:
    loop_body = inl + [N("if", ln, {"cond": c, "then": [app], "elifs": [], "els": []})]
  body = []
  for s in pre:
    append(body, s)
  append(body, N("set", ln, {"name": r, "val": N("list", ln, {"items": []})}))
  append(body, N("for", ln, {"var": v[1], "iter": it, "body": loop_body}))
  append(body, N("return", ln, {"val": N("var", ln, {"name": r})}))
  d = N("def", ln, {"name": name, "params": [], "body": body, "lam": true})
  append(P["hoist"], d)
  return N("call", ln, {"fn": N("var", ln, {"name": name}), "args": [], "lc": true, "e": elem, "x": v[1], "it": it, "c": c, "hl": pre + inl})

def parse_lambda():
  t = nxt()
  if P["unsafe"] > 0:
    raise "lambda not allowed in unsafe at line " + str(t[2])
  params = []
  if not atv("OP", ":"):
    while true:
      a = expect("ID")[1]
      if a in KEYWORDS:
        raise "bad parameter name '" + a + "' at line " + str(t[2])
      if a in params:
        raise "duplicate param '" + a + "' at line " + str(t[2])
      append(params, a)
      if atv("OP", ","):
        nxt()
        continue
      break
  expectv("OP", ":")
  outer = P["hoist"]
  P["hoist"] = []
  body = parse_expr()
  inner = P["hoist"]
  P["hoist"] = outer
  P["nlam"] = P["nlam"] + 1
  name = "_lam" + str(P["nlam"])
  d = N("def", t[2], {"name": name, "params": params, "body": inner + [N("return", t[2], {"val": body})], "lam": true})
  append(P["hoist"], d)
  return N("var", t[2], {"name": name})

def is_blank(s):
  i = 0
  while i < len(s):
    if not (s[i] == " " or s[i] == "\t" or s[i] == "\n" or s[i] == "\r"):
      return false
    i = i + 1
  return true

def parse_fstring(t):
  raw = t[1]
  ln = t[2]
  parts = []
  kinds = []
  lit = ""
  i = 0
  while i < len(raw):
    c = raw[i]
    if c == "\\" and i + 1 < len(raw):
      lit = lit + raw[i:i + 2]
      i = i + 2
    elif raw[i:i + 2] == "{{":
      lit = lit + "{"
      i = i + 2
    elif raw[i:i + 2] == "}}":
      lit = lit + "}"
      i = i + 2
    elif c == "}":
      raise "single '}' in f-string (write }}) at line " + str(ln)
    elif c == "{":
      depth = 1
      j = i + 1
      while j < len(raw) and depth > 0:
        if raw[j] == "{":
          depth = depth + 1
        if raw[j] == "}":
          depth = depth - 1
        j = j + 1
      if depth > 0:
        raise "unclosed '{' in f-string at line " + str(ln)
      src = raw[i + 1:j - 1]
      if is_blank(src):
        raise "empty {} in f-string at line " + str(ln)
      if len(lit) > 0:
        append(parts, lexlib.unesc("\"" + lit + "\""))
        append(kinds, true)
        lit = ""
      sub = []
      lexlib.lex_line(sub, src, ln)
      append(sub, ["EOF", "", ln])
      saved_t = P["t"]
      saved_i = P["i"]
      P["t"] = sub
      P["i"] = 0
      e = parse_expr()
      if not at("EOF"):
        raise "bad expression in f-string at line " + str(ln)
      P["t"] = saved_t
      P["i"] = saved_i
      append(parts, e)
      append(kinds, false)
      i = j
    else:
      lit = lit + c
      i = i + 1
  if len(lit) > 0:
    append(parts, lexlib.unesc("\"" + lit + "\""))
    append(kinds, true)
  node = null
  qi = 0
  while qi < len(parts):
    q = parts[qi]
    x = null
    if kinds[qi]:
      x = N("str", ln, {"val": q})
    else:
      x = N("call", ln, {"fn": N("var", ln, {"name": "str"}), "args": [q]})
    qi = qi + 1
    if node == null:
      node = x
    else:
      node = N("bin", ln, {"op": "+", "l": node, "r": x})
  if node == null:
    node = N("str", ln, {"val": ""})
  if node["t"] != "bin":
    node = N("bin", ln, {"op": "+", "l": N("str", ln, {"val": ""}), "r": node})
  node["fs"] = parts
  return node

def parse_extern():
  t = expect("ID")
  lib = null
  if atv("ID", "from"):
    nxt()
    lib = expect("STR")[1]
  expectv("OP", ":")
  if not at("NEWLINE"):
    raise "expected ':' then a new line at line " + str(t[2])
  nxt()
  if not at("INDENT"):
    raise "expected indented block at line " + str(peek()[2])
  nxt()
  decls = []
  skip_nl()
  while not at("EOF") and not at("DEDENT"):
    if at("INDENT"):
      u = nxt()
      raise "unexpected indent at line " + str(u[2])
    rt = expect("ID")
    if not rt[1] in FFTYPE:
      raise "bad ffi type '" + rt[1] + "' (want one of U0 I64 U64 F64 Str Ptr) at line " + str(rt[2])
    nm = expect("ID")
    if nm[1] in KEYWORDS or nm[1] in FFTYPE or nm[1] in UTYPES:
      raise "bad extern name '" + nm[1] + "' at line " + str(nm[2])
    expectv("OP", "(")
    params = []
    fixed = null
    if not atv("OP", ")"):
      while true:
        if atv("OP", "."):
          expectv("OP", ".")
          expectv("OP", ".")
          expectv("OP", ".")
          if fixed != null or len(params) == 0:
            raise "ffi variadic marker needs fixed parameters and appears once at line " + str(nm[2])
          fixed = len(params)
          expectv("OP", ",")
        ft = expect("ID")
        if not ft[1] in FFTYPE or ft[1] == "U0":
          raise "bad ffi param type '" + ft[1] + "' at line " + str(ft[2])
        pn = expect("ID")
        if pn[1] in KEYWORDS:
          raise "bad param name '" + pn[1] + "' at line " + str(pn[2])
        append(params, [pn[1], ft[1]])
        if atv("OP", ","):
          nxt()
          continue
        break
    expectv("OP", ")")
    decl = {"name": nm[1], "rtype": rt[1], "params": params, "line": nm[2]}
    if fixed != null:
      decl["fixed"] = fixed
    append(decls, decl)
    skip_nl()
  if at("DEDENT"):
    nxt()
  else:
    raise "expected indented block at line " + str(peek()[2])
  if len(decls) == 0:
    raise "extern block is empty at line " + str(t[2])
  return N("extern", t[2], {"decls": decls, "lib": lib})

def parse_class():
  t = expect("ID")
  name = expect("ID")[1]
  base = null
  if atv("OP", "("):
    nxt()
    bt = expect("ID")
    base = bt[1]
    if not has(P["classes"], base):
      raise "unknown base class '" + base + "' (define it first) at line " + str(bt[2])
    expectv("OP", ")")
  expectv("OP", ":")
  if not at("NEWLINE"):
    raise "expected ':' then a new line at line " + str(t[2])
  nxt()
  if not at("INDENT"):
    raise "expected indented block at line " + str(peek()[2])
  nxt()
  methods = []
  skip_nl()
  while not at("EOF") and not at("DEDENT"):
    if atv("ID", "pass"):
      nxt()
    elif atv("ID", "def"):
      outer = P["hoist"]
      P["hoist"] = []
      d = parse_def()
      d["body"] = P["hoist"] + d["body"]
      P["hoist"] = outer
      if len(d["params"]) == 0 or d["params"][0] != "self":
        raise "method '" + d["name"] + "' must take 'self' first at line " + str(d["line"])
      if has(d, "defaults"):
        raise "default args are not supported on methods at line " + str(d["line"])
      if d["name"] in METHODS:
        raise "method name '" + d["name"] + "' is taken by a builtin (split/find/join/append) at line " + str(d["line"])
      for m in methods:
        if m["name"] == d["name"]:
          raise "duplicate method '" + d["name"] + "' at line " + str(d["line"])
      append(methods, d)
    else:
      raise "a class body holds only def at line " + str(peek()[2])
    skip_nl()
  if at("DEDENT"):
    nxt()
  ln = t[2]
  table = {}
  init_fn = null
  params = []
  if base != null:
    info = P["classes"][base]
    btab = info[0]
    init_fn = info[1]
    params = info[2]
    for k in keys(btab):
      table[k] = btab[k]
  for m in methods:
    orig = m["name"]
    m["orig"] = orig
    if orig[0:2] == "__":
      m["name"] = name + orig
    else:
      m["name"] = name + "__" + orig
    m["clsmember"] = true
    append(P["hoist"], m)
    if orig == "__init__":
      init_fn = m["name"]
      params = m["params"][1:len(m["params"])]
    else:
      table[orig] = m["name"]
  P["classes"][name] = [table, init_fn, params]
  pairs = []
  for k in keys(table):
    append(pairs, [N("str", ln, {"val": k}), N("var", ln, {"name": table[k]})])
  body = [N("set", ln, {"name": "self", "val": N("dict", ln, {"pairs": pairs})})]
  if init_fn != null:
    cargs = [N("var", ln, {"name": "self"})]
    for a in params:
      append(cargs, N("var", ln, {"name": a}))
    append(body, N("expr", ln, {"val": N("call", ln, {"fn": N("var", ln, {"name": init_fn}), "args": cargs})}))
  append(body, N("return", ln, {"val": N("var", ln, {"name": "self"})}))
  return N("def", ln, {"name": name, "params": params, "body": body, "cls": name, "methods": methods, "base": base})

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
  if (P["unsafe"] > 0 or (has(P, "kernel_wide") and P["kernel_wide"])) and has(P, "wide_literals") and P["wide_literals"] and find(s, ".") < 0:
    ishex = len(s) > 1 and (s[1] == "x" or s[1] == "X")
    if ishex or (find(s, "e") < 0 and find(s, "E") < 0):
      bs = wide_number(s, ishex)
      if bs[7] >= 32:
        return N("num", x[2], {"val": {"wide": bs}, "raw": s})
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
    nxt()
    return parse_fstring(t)
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
    return parse_lambda()
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
    items = []
    if not atv("OP", "]"):
      h0 = len(P["hoist"])
      while true:
        append(items, parse_expr())
        if len(items) == 1 and atv("ID", "for"):
          return parse_listcomp(t, items[0], h0)
        if atv("OP", ","):
          nxt()
          continue
        break
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

def parse(src):
  P["t"] = lexlib.lex(src)
  P["i"] = 0
  P["mods"] = {}
  P["hoist"] = []
  P["nlam"] = 0
  P["classes"] = {}
  P["unsafe"] = 0
  if not (has(P, "kernel_wide") and P["kernel_wide"]):
    P["structs"] = {}
  body = parse_body(true)
  expect("EOF")
  return body

def strip_raise(e):
  # hs `raise` appends " at line N" of the raise site; the Python parser's
  # message is the part before it
  last = 0 - 1
  i = 0
  while true:
    j = find(e[i:], " at line ")
    if j < 0:
      break
    last = i + j
    i = i + j + 1
  if last < 0:
    return e
  return e[:last]


def wide_number(s, ishex):
  base = 10
  start = 0
  if ishex:
    base = 16
    start = 2
  bs = [0, 0, 0, 0, 0, 0, 0, 0]
  for i in range(start, len(s)):
    digit = find("0123456789abcdef", s[i])
    if digit < 0:
      digit = find("ABCDEF", s[i]) + 10
    carry = digit
    for j in range(8):
      v = bs[j] * base + carry
      bs[j] = v & 255
      carry = v >> 8
    if carry != 0:
      raise "integer literal exceeds 64 bits"
  return bs
