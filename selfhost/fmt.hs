# Self-hosted formatter: prints the canonical form of a .hs file, exactly like
# `python3 hs.py fmt FILE` (fmt.py). Uses selfhost/parselib.hs for the AST.
import parselib

BIN_PREC = {"or": 1, "and": 2, "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3, "+": 4, "-": 4, "*": 5, "/": 5, "%": 5, "<<": 6, ">>": 6, "&": 6, "|": 6, "^": 6}
LAM = {}

def esc(s):
  out = ""
  i = 0
  while i < len(s):
    ch = s[i]
    if ch == "\\":
      out = out + "\\\\"
    elif ch == "\"":
      out = out + "\\\""
    elif ch == "\n":
      out = out + "\\n"
    elif ch == "\t":
      out = out + "\\t"
    elif ch == "\0":
      out = out + "\\0"
    elif ch == "\r":
      out = out + "\\r"
    else:
      j = json_str(ch)
      if len(j) > 3 and j[1:2] == "\\" and j[2:3] == "u" and j[3:5] == "00" and j[5:6] < "2":
        out = out + j[1:7]
      elif j == "\"\\b\"":
        out = out + "\\u0008"
      elif j == "\"\\f\"":
        out = out + "\\u000c"
      else:
        out = out + ch
    i = i + 1
  return out

def fmt_num(e):
  if has(e, "raw") and e["raw"] != null:
    return e["raw"]
  if has(e, "raw"):
    return str(e["val"])
  return json_str(e["val"])

def join_exprs(xs):
  out = []
  for x in xs:
    append(out, fmt_expr(x))
  return join(", ", out)

def prec(e):
  t = e["t"]
  if t == "var" and has(LAM, e["name"]):
    return 0
  if t == "bin":
    if has(e, "fs"):
      return 9
    return BIN_PREC[e["op"]]
  if t == "not":
    if has(e, "notin"):
      return 3
    return 7
  if t == "call" and has(e, "inop"):
    return 3
  if t == "index" and has(e, "tern"):
    return 0
  if t == "neg" or t == "unot":
    return 8
  return 9

def atom(e, level):
  s = fmt_expr(e)
  if prec(e) < level:
    return "(" + s + ")"
  return s

def side(e, parent, sd, op):
  c = prec(e)
  if c < parent:
    return "(" + fmt_expr(e) + ")"
  if c == parent and sd == "r" and op != "+" and op != "*":
    return "(" + fmt_expr(e) + ")"
  return fmt_expr(e)

def reg_lams(body):
  for s in body:
    if s["t"] == "def" and has(s, "lam"):
      LAM[s["name"]] = s

def fmt_expr(e):
  t = e["t"]
  if t == "num":
    return fmt_num(e)
  if t == "str":
    return "\"" + esc(e["val"]) + "\""
  if t == "var":
    if has(LAM, e["name"]):
      d = LAM[e["name"]]
      reg_lams(d["body"])
      ps = join(", ", d["params"])
      ret = d["body"][len(d["body"]) - 1]["val"]
      head = "lambda"
      if len(ps) > 0:
        head = "lambda " + ps
      return head + ": " + fmt_expr(ret)
    return e["name"]
  if t == "list":
    return "[" + join_exprs(e["items"]) + "]"
  if t == "dict":
    parts = []
    for kv in e["pairs"]:
      append(parts, fmt_expr(kv[0]) + ": " + fmt_expr(kv[1]))
    return "{" + join(", ", parts) + "}"
  if t == "neg":
    return "-" + atom(e["val"], 8)
  if t == "not" and has(e, "notin"):
    c = e["val"]
    return side(c["args"][1], 3, "l", "in") + " not in " + side(c["args"][0], 3, "r", "in")
  if t == "not":
    return "not " + atom(e["val"], 7)
  if t == "unot":
    return "~" + atom(e["val"], 8)
  if t == "bin" and has(e, "fs"):
    out = ""
    for q in e["fs"]:
      if json_str(q)[0:1] == "\"":
        out = out + join("}}", split(join("{{", split(esc(q), "{")), "}"))
      else:
        out = out + "{" + fmt_expr(q) + "}"
    return "f\"" + out + "\""
  if t == "bin":
    p = BIN_PREC[e["op"]]
    return side(e["l"], p, "l", e["op"]) + " " + e["op"] + " " + side(e["r"], p, "r", e["op"])
  if t == "call" and has(e, "lc"):
    reg_lams(e["hl"])
    cs = ""
    if e["c"] != null:
      cs = " if " + fmt_expr(e["c"])
    return "[" + fmt_expr(e["e"]) + " for " + e["x"] + " in " + fmt_expr(e["it"]) + cs + "]"
  if t == "call" and has(e, "inop"):
    return side(e["args"][1], 3, "l", "in") + " in " + side(e["args"][0], 3, "r", "in")
  if t == "call" and has(e, "mcall"):
    return fmt_expr(e["fn"]) + "(" + join_exprs(e["args"][1:len(e["args"])]) + ")"
  if t == "call" and has(e, "method"):
    return atom(e["args"][0], 9) + "." + e["method"] + "(" + join_exprs(e["args"][1:len(e["args"])]) + ")"
  if t == "call":
    return atom(e["fn"], 9) + "(" + join_exprs(e["args"]) + ")"
  if t == "index" and has(e, "tern"):
    return atom(e["a"], 1) + " if " + atom(e["c"], 1) + " else " + fmt_expr(e["b"])
  if t == "index" and has(e, "dot"):
    return atom(e["obj"], 9) + "." + e["dot"]
  if t == "index":
    return atom(e["obj"], 9) + "[" + fmt_expr(e["idx"]) + "]"
  if t == "slice":
    a = ""
    b = ""
    if e["start"] != null:
      a = fmt_expr(e["start"])
    if e["stop"] != null:
      b = fmt_expr(e["stop"])
    return atom(e["obj"], 9) + "[" + a + ":" + b + "]"
  if t == "attr":
    return atom(e["obj"], 9) + "." + e["name"]
  if t == "field":
    s = atom(e["obj"], 9) + "." + e["name"]
    if e["idx"] != null:
      s = s + "[" + fmt_expr(e["idx"]) + "]"
    return s
  if t == "deref":
    return "*" + atom(e["val"], 7)
  if t == "sizeof":
    return "sizeof(" + e["stype"] + ")"
  raise "fmt: bad expr " + t

def pad(ind):
  out = ""
  i = 0
  while i < ind:
    out = out + "  "
    i = i + 1
  return out

def fmt_block(body, ind, out):
  reg_lams(body)
  for s in body:
    if s["t"] == "def" and (has(s, "lam") or has(s, "clsmember")):
      continue
    fmt_stmt(s, ind, out)

def suite(head, body, ind, out):
  append(out, pad(ind) + head)
  fmt_block(body, ind + 1, out)

def starts_paren(f):
  return len(f) > 0 and f[0] == "("

def fmt_stmt(s, ind, out):
  t = s["t"]
  p = pad(ind)
  if t == "pass" or t == "break" or t == "continue":
    append(out, p + t)
  elif t == "expr":
    append(out, p + fmt_expr(s["val"]))
  elif t == "print":
    if len(s["args"]) == 0:
      append(out, p + "print")
    else:
      parts = []
      for a in s["args"]:
        f = fmt_expr(a)
        if starts_paren(f):
          f = "(" + f + ")"
        append(parts, f)
      append(out, p + "print " + join(", ", parts))
  elif t == "return" or t == "raise":
    if s["val"] == null:
      append(out, p + t)
    else:
      append(out, p + t + " " + fmt_expr(s["val"]))
  elif t == "global":
    append(out, p + "global " + join(", ", s["names"]))
  elif t == "import":
    append(out, p + "import " + s["name"])
  elif t == "set":
    append(out, p + s["name"] + " = " + fmt_expr(s["val"]))
  elif t == "setindex" and s["dot"] != null:
    append(out, p + fmt_expr(s["obj"]) + "." + s["dot"] + " = " + fmt_expr(s["val"]))
  elif t == "setindex":
    append(out, p + fmt_expr(s["obj"]) + "[" + fmt_expr(s["idx"]) + "] = " + fmt_expr(s["val"]))
  elif t == "setattr":
    append(out, p + fmt_expr(s["obj"]) + "." + s["name"] + " = " + fmt_expr(s["val"]))
  elif t == "def" and has(s, "cls"):
    head = p + "class " + s["cls"]
    if s["base"] != null:
      head = head + "(" + s["base"] + ")"
    append(out, head + ":")
    for m in s["methods"]:
      m["name"] = m["orig"]
      m["clsmember"] = false
      fmt_stmt(m, ind + 1, out)
    if len(s["methods"]) == 0:
      append(out, p + "  pass")
  elif t == "def":
    ps = s["params"] + []
    if has(s, "defaults"):
      nd = len(s["defaults"])
      di = 0
      while di < nd:
        pj = len(ps) - nd + di
        ps[pj] = ps[pj] + "=" + fmt_expr(s["defaults"][di])
        di = di + 1
    append(out, p + "def " + s["name"] + "(" + join(", ", ps) + "):")
    fmt_block(s["body"], ind + 1, out)
  elif t == "if" and has(s, "asrt"):
    if s["m"] == null:
      append(out, p + "assert " + fmt_expr(s["c"]))
    else:
      append(out, p + "assert " + fmt_expr(s["c"]) + ", " + fmt_expr(s["m"]))
  elif t == "if":
    suite("if " + fmt_expr(s["cond"]) + ":", s["then"], ind, out)
    for ec in s["elifs"]:
      suite("elif " + fmt_expr(ec[0]) + ":", ec[1], ind, out)
    if len(s["els"]) > 0:
      suite("else:", s["els"], ind, out)
  elif t == "while":
    suite("while " + fmt_expr(s["cond"]) + ":", s["body"], ind, out)
  elif t == "for" and has(s, "tup"):
    suite("for " + join(", ", s["tup"]) + " in " + fmt_expr(s["iter"]) + ":", s["body"][len(s["tup"]):len(s["body"])], ind, out)
  elif t == "for":
    suite("for " + s["var"] + " in " + fmt_expr(s["iter"]) + ":", s["body"], ind, out)
  elif t == "try":
    suite("try:", s["body"], ind, out)
    if s["ebody"] != null:
      head = "except:"
      if s["ename"] != null:
        head = "except as " + s["ename"] + ":"
      suite(head, s["ebody"], ind, out)
    if s["fbody"] != null:
      suite("finally:", s["fbody"], ind, out)
  elif t == "extern":
    head = "extern:"
    if s["lib"] != null:
      head = "extern from \"" + esc(s["lib"]) + "\":"
    append(out, p + head)
    for d in s["decls"]:
      ps = []
      for i in range(len(d["params"])):
        if has(d, "fixed") and i == d["fixed"]:
          append(ps, "...")
        pr = d["params"][i]
        append(ps, pr[1] + " " + pr[0])
      append(out, pad(ind + 1) + d["rtype"] + " " + d["name"] + "(" + join(", ", ps) + ")")
  elif t == "unsafe":
    append(out, p + "unsafe:")
    fmt_block(s["body"], ind + 1, out)
  elif t == "struct":
    L = parselib.P["structs"][s["name"]]
    append(out, p + "struct " + s["name"] + ":")
    for fname in keys(L["fields"]):
      f = L["fields"][fname]
      decl = f[0] + " " + fname
      if f[0][0:4] == "Ptr:":
        decl = f[0][4:len(f[0])] + "* " + fname
      if f[2] > 1:
        decl = decl + "[" + str(f[2]) + "]"
      append(out, pad(ind + 1) + decl)
  elif t == "udecl":
    ut = s["utype"]
    head = ut
    if ut[0:4] == "Ptr:":
      head = ut[4:len(ut)] + "*"
    if s["init"] != null:
      append(out, p + head + " " + s["name"] + " = " + fmt_expr(s["init"]))
    else:
      append(out, p + head + " " + s["name"])
  elif t == "store":
    append(out, p + "*" + fmt_expr(s["ptr"]) + " = " + fmt_expr(s["val"]))
  elif t == "fstore":
    base = fmt_expr(s["obj"]) + "." + s["name"]
    if s["idx"] != null:
      base = base + "[" + fmt_expr(s["idx"]) + "]"
    append(out, p + base + " = " + fmt_expr(s["val"]))
  else:
    raise "fmt: bad stmt " + t

try:
  prog = parselib.parse(read_text(argv()[0]))
  out = []
  fmt_block(prog, 0, out)
  print join("\n", out)
except as e:
  print "error: " + parselib.strip_raise(e)
  raise "fmt failed"
