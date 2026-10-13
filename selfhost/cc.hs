# cc.hs - a tiny holyshit compiler written in holyshit.
#   hs run selfhost/cc.hs prog.hs out     (then ./out)
# It parses with selfhost/parselib.hs and assembles with selfhost/asm.hs (both
# written in hs) and writes a static x86-64 Linux ELF with write_bytes. No
# gcc, no Python in the compile step. Subset: Int variables, + - * % & | ^ << >>,
# comparisons and/or/not (conditions only), if/elif/else, while, break,
# continue, def/return/recursion, print of Ints and string literals.
# Anything else is a compile error, never silently different output.
import parselib
import asm

STRS = []
ST = {"lbl": 0, "fn": null, "locals": {}, "funcs": {}, "globals": {}, "loops": []}
BASE = 4194304 + 120

def fail(msg, ln):
  raise "cc: " + msg + " (line " + str(ln) + ")"

def new_label(p):
  ST["lbl"] = ST["lbl"] + 1
  return p + str(ST["lbl"])

# ---- variables -------------------------------------------------------
def load_var(name, ln):
  if name in ST["locals"]:
    asm.mov_rm("rax", "rbp", ST["locals"][name])
  elif name in ST["globals"]:
    asm.mov_rm_rip("rax", "g_" + name)
  else:
    fail("unknown variable '" + name + "'", ln)

def store_var(name, ln):
  if name in ST["locals"]:
    asm.mov_mr("rbp", "rax", ST["locals"][name])
  elif name in ST["globals"]:
    asm.mov_mr_rip("g_" + name, "rax")
  else:
    fail("unknown variable '" + name + "'", ln)

def collect_sets(body, out):
  for s in body:
    t = s["t"]
    if t == "set":
      out[s["name"]] = true
    elif t == "if":
      collect_sets(s["then"], out)
      for ec in s["elifs"]:
        collect_sets(ec[1], out)
      collect_sets(s["els"], out)
    elif t == "while":
      collect_sets(s["body"], out)

# ---- expressions -----------------------------------------------------
CMP = {"<": "l", "<=": "le", ">": "g", ">=": "ge", "==": "e", "!=": "ne"}

def is_bool(e):
  t = e["t"]
  if t == "not":
    return true
  if t == "bin":
    op = e["op"]
    return op in CMP or op == "and" or op == "or"
  return false

def gen_int(e):
  if is_bool(e):
    fail("Bool value used as Int (cc subset: Bool only in conditions)", e["line"])
  gen(e)

def gen_pair(e):
  gen_int(e["l"])
  asm.push_r("rax")
  gen_int(e["r"])
  asm.mov_rr("rcx", "rax")
  asm.pop_r("rax")

def gen(e):
  t = e["t"]
  ln = e["line"]
  if t == "num":
    v = e["val"]
    for ch in str(v):
      if find("-0123456789", ch) < 0:
        fail("only Int literals are supported (no Float/Bool/null)", ln)
    asm.mov_ri64("rax", v)
  elif t == "var":
    load_var(e["name"], ln)
  elif t == "neg":
    gen_int(e["val"])
    asm.neg_r("rax")
  elif t == "not":
    gen(e["val"])
    asm.test_rr("rax", "rax")
    asm.setcc_al("e")
    asm.movzx_eax_al()
  elif t == "bin":
    op = e["op"]
    if op == "and" or op == "or":
      if not is_bool(e["l"]) or not is_bool(e["r"]):
        fail("and/or only on comparisons in cc subset", ln)
      end = new_label("L")
      gen(e["l"])
      asm.test_rr("rax", "rax")
      if op == "and":
        asm.jcc("e", end)
      else:
        asm.jcc("ne", end)
      gen(e["r"])
      asm.label(end)
    elif op in CMP:
      if is_bool(e["l"]) or is_bool(e["r"]):
        fail("comparing Bool values not supported", ln)
      gen_pair(e)
      asm.cmp_rr("rax", "rcx")
      asm.setcc_al(CMP[op])
      asm.movzx_eax_al()
    elif op == "+":
      gen_pair(e)
      asm.add_rr("rax", "rcx")
    elif op == "-":
      gen_pair(e)
      asm.sub_rr("rax", "rcx")
    elif op == "*":
      gen_pair(e)
      asm.imul_rr("rax", "rcx")
    elif op == "&":
      gen_pair(e)
      asm.and_rr("rax", "rcx")
    elif op == "|":
      gen_pair(e)
      asm.or_rr("rax", "rcx")
    elif op == "^":
      gen_pair(e)
      asm.xor_rr("rax", "rcx")
    elif op == "%":
      gen_pair(e)
      # floor modulo like Python: cqo; idiv rcx; fix the sign of the remainder
      done = new_label("L")
      asm.cqo()
      asm.idiv_r("rcx")
      asm.mov_rr("rax", "rdx")
      asm.test_rr("rdx", "rdx")
      asm.jcc("e", done)
      asm.xor_rr("rdx", "rcx")
      asm.jcc("ns", done)
      asm.add_rr("rax", "rcx")
      asm.label(done)
    elif op == "<<":
      gen_pair(e)
      asm.shl_cl("rax")
    elif op == ">>":
      gen_pair(e)
      asm.sar_cl("rax")
    else:
      fail("operator '" + op + "' not supported", ln)
  elif t == "call":
    if e["fn"]["t"] != "var":
      fail("only direct calls to defined functions", ln)
    nm = e["fn"]["name"]
    if not (nm in ST["funcs"]):
      fail("call of unknown function '" + nm + "'", ln)
    if len(e["args"]) != ST["funcs"][nm]:
      fail("function '" + nm + "' wants " + str(ST["funcs"][nm]) + " args", ln)
    for a in e["args"]:
      gen_int(a)
      asm.push_r("rax")
    asm.call("f_" + nm)
    if len(e["args"]) > 0:
      asm.add_ri32("rsp", 8 * len(e["args"]))
  else:
    fail("expression '" + t + "' not supported", ln)

# ---- statements ------------------------------------------------------
def gen_cond_jz(c, target):
  if not is_bool(c):
    fail("condition must be a comparison / and / or / not in cc subset", c["line"])
  gen(c)
  asm.test_rr("rax", "rax")
  asm.jcc("e", target)

def ascii_byte(ch, ln):
  if ch == "\n":
    return 10
  if ch == "\t":
    return 9
  k = find(" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~", ch)
  if k < 0:
    fail("non-ASCII character in string literal", ln)
  return k + 32

def put_str(s, ln):
  if len(s) == 0:
    return 0
  lab = new_label("S")
  append(STRS, [lab, s, ln])
  asm.lea_rip("rsi", lab)
  asm.mov_ri32("rdx", len(s))
  asm.mov_ri32("rdi", 1)
  asm.mov_ri32("rax", 1)
  asm.syscall()

def put_char(c):
  asm.mov_ri32("rax", c)
  asm.call("rt_putc")

def gen_stmt(s):
  t = s["t"]
  ln = s["line"]
  if t == "set":
    gen_int(s["val"])
    store_var(s["name"], ln)
  elif t == "print":
    n = len(s["args"])
    i = 0
    for a in s["args"]:
      if a["t"] == "str":
        put_str(a["val"], ln)
      else:
        gen_int(a)
        asm.call("rt_puti")
      i = i + 1
      if i < n:
        put_char(32)
    put_char(10)
  elif t == "expr":
    gen(s["val"])
  elif t == "pass":
    pass
  elif t == "if":
    end = new_label("E")
    nxt = new_label("N")
    gen_cond_jz(s["cond"], nxt)
    gen_body(s["then"])
    asm.jmp(end)
    asm.label(nxt)
    for ec in s["elifs"]:
      nxt = new_label("N")
      gen_cond_jz(ec[0], nxt)
      gen_body(ec[1])
      asm.jmp(end)
      asm.label(nxt)
    gen_body(s["els"])
    asm.label(end)
  elif t == "while":
    top = new_label("W")
    out = new_label("X")
    asm.label(top)
    gen_cond_jz(s["cond"], out)
    append(ST["loops"], [top, out])
    gen_body(s["body"])
    ST["loops"] = ST["loops"][0:len(ST["loops"]) - 1]
    asm.jmp(top)
    asm.label(out)
  elif t == "break" or t == "continue":
    if len(ST["loops"]) == 0:
      fail(t + " outside loop", ln)
    lp = ST["loops"][len(ST["loops"]) - 1]
    if t == "break":
      asm.jmp(lp[1])
    else:
      asm.jmp(lp[0])
  elif t == "return":
    if ST["fn"] == null:
      fail("return outside function", ln)
    if s["val"] == null:
      asm.xor_rr("rax", "rax")
    else:
      gen_int(s["val"])
    asm.jmp("r_" + ST["fn"])
  else:
    fail("statement '" + t + "' not supported", ln)

def gen_body(body):
  for s in body:
    gen_stmt(s)

# ---- functions and runtime ------------------------------------------
def gen_func(d):
  nm = d["name"]
  ST["fn"] = nm
  ST["locals"] = {}
  n = len(d["params"])
  i = 0
  for p in d["params"]:
    ST["locals"][p] = 16 + 8 * (n - 1 - i)
    i = i + 1
  sets = {}
  collect_sets(d["body"], sets)
  nl = 0
  for k in keys(sets):
    if not (k in ST["locals"]):
      nl = nl + 1
      ST["locals"][k] = 0 - 8 * nl
  asm.label("f_" + nm)
  asm.push_r("rbp")
  asm.mov_rr("rbp", "rsp")
  if nl > 0:
    asm.sub_ri32("rsp", 8 * nl)
    # zero the locals so a stray read is deterministic
    asm.xor_rr("rax", "rax")
    j = 1
    while j <= nl:
      asm.mov_mr("rbp", "rax", 0 - 8 * j)
      j = j + 1
  gen_body(d["body"])
  asm.xor_rr("rax", "rax")
  asm.label("r_" + nm)
  asm.mov_rr("rsp", "rbp")
  asm.pop_r("rbp")
  asm.ret()
  ST["fn"] = null
  ST["locals"] = {}

def gen_runtime():
  # rt_putc: write the byte in al
  asm.label("rt_putc")
  asm.push_r("rax")
  asm.mov_rr("rsi", "rsp")
  asm.mov_ri32("rdx", 1)
  asm.mov_ri32("rdi", 1)
  asm.mov_ri32("rax", 1)
  asm.syscall()
  asm.pop_r("rax")
  asm.ret()
  # rt_puti: print the Int in rax in decimal (no newline); digits are built
  # backwards below rbp, magnitude via unsigned div so Int min works
  asm.label("rt_puti")
  asm.push_r("rbp")
  asm.mov_rr("rbp", "rsp")
  asm.sub_ri32("rsp", 48)
  asm.mov_rr("rcx", "rax")
  asm.lea_m("rsi", "rbp", 0 - 1)
  asm.mov_ri32("rdi", 0)
  asm.test_rr("rcx", "rcx")
  asm.jcc("ns", "pi_pos")
  asm.neg_r("rcx")
  asm.mov_ri32("rdi", 1)
  asm.label("pi_pos")
  asm.mov_ri32("r9", 10)
  asm.label("pi_loop")
  asm.xor_rr("rdx", "rdx")
  asm.mov_rr("rax", "rcx")
  asm.div_r("r9")
  asm.add_ri32("rdx", 48)
  asm.mov_mr8("rsi", 2, 0)
  asm.sub_ri32("rsi", 1)
  asm.mov_rr("rcx", "rax")
  asm.test_rr("rcx", "rcx")
  asm.jcc("ne", "pi_loop")
  asm.test_rr("rdi", "rdi")
  asm.jcc("e", "pi_skip")
  asm.mov_ri32("rax", 45)
  asm.mov_mr8("rsi", 0, 0)
  asm.sub_ri32("rsi", 1)
  asm.label("pi_skip")
  asm.add_ri32("rsi", 1)
  asm.mov_rr("rdx", "rbp")
  asm.sub_rr("rdx", "rsi")
  asm.mov_ri32("rdi", 1)
  asm.mov_ri32("rax", 1)
  asm.syscall()
  asm.mov_rr("rsp", "rbp")
  asm.pop_r("rbp")
  asm.ret()

def compile(prog):
  asm.reset()
  top = []
  for s in prog:
    if s["t"] == "def":
      if s["name"] in ST["funcs"]:
        fail("function '" + s["name"] + "' defined twice", s["line"])
      ST["funcs"][s["name"]] = len(s["params"])
    else:
      append(top, s)
  gl = {}
  collect_sets(top, gl)
  for k in keys(gl):
    ST["globals"][k] = true
  gen_body(top)
  asm.mov_ri32("rdi", 0)
  asm.mov_ri32("rax", 60)
  asm.syscall()
  for s in prog:
    if s["t"] == "def":
      gen_func(s)
  gen_runtime()
  for st in STRS:
    asm.label(st[0])
    for ch in st[1]:
      asm.b1(ascii_byte(ch, st[2]))
  for k in keys(ST["globals"]):
    asm.label("g_" + k)
    asm.bn([0, 0, 0, 0, 0, 0, 0, 0])

def le64(v):
  out = []
  i = 0
  while i < 8:
    append(out, (v >> (8 * i)) & 255)
    i = i + 1
  return out

def elf(code):
  n = 120 + len(code)
  h = [127, 69, 76, 70, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  h = h + [2, 0, 62, 0, 1, 0, 0, 0]
  h = h + le64(BASE) + le64(64) + le64(0)
  h = h + [0, 0, 0, 0, 64, 0, 56, 0, 1, 0, 0, 0, 0, 0, 0, 0]
  h = h + [1, 0, 0, 0, 7, 0, 0, 0] + le64(0) + le64(4194304) + le64(4194304)
  h = h + le64(n) + le64(n) + le64(4096)
  return h + code

a = argv()
if len(a) != 2:
  print "usage: hs run selfhost/cc.hs prog.hs out"
  raise "usage"
try:
  prog = parselib.parse(read_text(a[0]))
  compile(prog)
  write_bytes(a[1], elf(asm.resolve()))
except as e:
  print "error: " + parselib.strip_raise(e)
  raise "compile failed"
