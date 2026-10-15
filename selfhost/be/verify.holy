import pyrt
def verify_module(m):
  if not (m["entry"] in m["funcs"]):
    raise pyrt.py_err("IR: missing entry", 0)
  seen = pyrt.py_set(null)
  for name in m["order"]:
    if name in seen:
      raise pyrt.py_err("IR: duplicate function '" + str(name) + "'", 0)
    pyrt.py_add(seen, name)
    if not (name in m["funcs"]):
      raise pyrt.py_err("IR: missing function '" + str(name) + "'", 0)
    _verify_func(m["funcs"][name], m["funcs"])
def _verify_func(fn, funcs):
  labels = [b["label"] for b in fn["blocks"]]
  if len(pyrt.py_set(labels)) != len(labels):
    raise pyrt.py_err("IR: duplicate block label in '" + str(fn["dispname"]) + "'", 0)
  by = pyrt.py_dict([[b["label"], b] for b in fn["blocks"]])
  if not (fn["entry"] in by):
    raise pyrt.py_err("IR: missing entry block in '" + str(fn["dispname"]) + "'", 0)
  defs = {}
  for b in fn["blocks"]:
    for ins in b["instrs"]:
      d = pyrt.py_get(ins, "dest", null)
      if d != null:
        if d in defs:
          raise pyrt.py_err("IR: temp '" + str(d) + "' redefined", ins["line"])
        defs[d] = b["label"]
  preds = pyrt.py_dict([[l, pyrt.py_set(null)] for l in labels])
  succs = pyrt.py_dict([[l, []] for l in labels])
  def _edge(frm, to, tm):
    _need(by, to, tm)
    pyrt.py_add(preds[to], frm)
    append(succs[frm], to)
  for b in fn["blocks"]:
    tm = b["term"]
    if tm == null:
      raise pyrt.py_err("IR: block '" + str(b["label"]) + "' has no terminator", b["instrs"][0 - 1]["line"] if b["instrs"] else 0)
    if tm["term"] == "jmp":
      _edge(b["label"], tm["to"], tm)
    elif tm["term"] == "br":
      _edge(b["label"], tm["then"], tm)
      _edge(b["label"], tm["els"], tm)
    elif tm["term"] != "ret" and tm["term"] != "raise":
      raise pyrt.py_err("IR: bad terminator '" + str(tm["term"]) + "'", tm["line"])
  reach = pyrt.py_set(null)
  stack = [fn["entry"]]
  while stack:
    l = stack[len(stack) - 1]
    stack = stack[0:len(stack) - 1]
    if l in reach:
      continue
    pyrt.py_add(reach, l)
    pyrt.py_extend(stack, succs[l])
  dom = pyrt.py_dict([[l, pyrt.py_set(labels)] for l in labels])
  dom[fn["entry"]] = pyrt.py_set([fn["entry"]])
  changed = true
  while changed:
    changed = false
    for l in labels:
      if l == fn["entry"]:
        continue
      ps = preds[l]
      ds = []
      for p in keys(ps):
        append(ds, dom[p])
      new = pyrt.py_set([l])
      if len(ds) > 0:
        new = pyrt.py_union(intersections(ds), new)
      if new != dom[l]:
        dom[l] = new
        changed = true
  def _use(t, at, ln):
    if not (t in defs):
      raise pyrt.py_err("IR: undefined temp '" + str(t) + "'", ln)
    if at in reach and not (defs[t] in dom[at]):
      raise pyrt.py_err("IR: temp '" + str(t) + "' does not dominate use", ln)
  for b in fn["blocks"]:
    tm = b["term"]
    if tm["term"] == "br":
      _use(tm["cond"], b["label"], tm["line"])
    elif tm["term"] == "ret":
      if tm["val"] != null:
        _use(tm["val"], b["label"], tm["line"])
    elif tm["term"] == "raise":
      if tm["src"] != null:
        _use(tm["src"], b["label"], tm["line"])
  for b in fn["blocks"]:
    for ins in b["instrs"]:
      op = ins["op"]
      ln = ins["line"]
      if op == "phi":
        if b["label"] == fn["entry"]:
          raise pyrt.py_err("IR: phi in entry block", ln)
        if not ins["arms"]:
          raise pyrt.py_err("IR: phi with no arms", ln)
        for al, at in ins["arms"]:
          if not (al in preds[b["label"]]):
            raise pyrt.py_err("IR: phi arm from non-predecessor '" + str(al) + "'", ln)
          _use(at, al, ln)
      elif op in ["const", "load", "stvar", "stglobal", "import", "sconst", "sload", "sstr", "ffi"]:
        pass
      elif op == "sdecl":
        _use(ins["src"], b["label"], ln)
      elif op in ["sstore"]:
        _use(ins["ptr"], b["label"], ln)
        _use(ins["val"], b["label"], ln)
      elif op == "sfstore":
        _use(ins["obj"], b["label"], ln)
        _use(ins["val"], b["label"], ln)
        if ins["idx"] != null:
          _use(ins["idx"], b["label"], ln)
      elif op in ["sset", "dset"]:
        _use(ins["src"], b["label"], ln)
      elif op == "sbin":
        _use(ins["l"], b["label"], ln)
        _use(ins["r"], b["label"], ln)
      elif op == "sun":
        _use(ins["v"], b["label"], ln)
      elif op == "scall":
        for x in ins["args"]:
          _use(x, b["label"], ln)
      elif op == "sderef":
        _use(ins["v"], b["label"], ln)
      elif op == "sfield":
        _use(ins["obj"], b["label"], ln)
        if ins["idx"] != null:
          _use(ins["idx"], b["label"], ln)
      elif op in ["box", "sraw", "snz"]:
        _use(ins["src"], b["label"], ln)
      elif op == "svarptr":
        pass
      elif op in ["serr", "ssizeof"]:
        pass
      elif op in ["try_push"]:
        if not (ins["handler"] in by):
          raise pyrt.py_err("IR: jump to missing block '" + str(ins["handler"]) + "'", ln)
      elif op in ["try_pop", "exc_pop"]:
        pass
      elif op == "exc_str":
        pass
      elif op == "unbind":
        pass
      elif op == "reraise":
        pass
      elif op == "attr":
        _use(ins["obj"], b["label"], ln)
      elif op == "setattr":
        _use(ins["obj"], b["label"], ln)
        _use(ins["val"], b["label"], ln)
      elif op == "mkfunc":
        if not (ins["func"] in funcs):
          raise pyrt.py_err("IR: unknown function '" + str(ins["func"]) + "'", ln)
      elif op == "build_list":
        for x in ins["items"]:
          _use(x, b["label"], ln)
      elif op == "build_dict":
        for k, v in ins["pairs"]:
          _use(k, b["label"], ln)
          _use(v, b["label"], ln)
      elif op == "index":
        _use(ins["obj"], b["label"], ln)
        _use(ins["idx"], b["label"], ln)
      elif op == "slice":
        _use(ins["obj"], b["label"], ln)
        for k in ["start", "stop"]:
          if ins[k] != null:
            _use(ins[k], b["label"], ln)
      elif op == "setindex":
        for k in ["obj", "idx", "val"]:
          _use(ins[k], b["label"], ln)
      elif op == "iterseq":
        _use(ins["src"], b["label"], ln)
      elif op == "bin":
        _use(ins["l"], b["label"], ln)
        _use(ins["r"], b["label"], ln)
      elif op == "un":
        _use(ins["v"], b["label"], ln)
      elif op == "call":
        _use(ins["fn"], b["label"], ln)
        for a in ins["args"]:
          _use(a, b["label"], ln)
      elif op == "print":
        for a in ins["args"]:
          _use(a, b["label"], ln)
      else:
        raise pyrt.py_err("IR: bad op '" + str(op) + "'", ln)
def _need(by, lab, tm):
  if not (lab in by):
    raise pyrt.py_err("IR: jump to missing block '" + str(lab) + "'", tm["line"])
def intersections(sets):
  if len(sets) == 0:
    return {}
  out = {}
  for k in keys(sets[0]):
    yes = true
    for d in sets:
      if not has(d, k):
        yes = false
    if yes:
      out[k] = true
  return out
