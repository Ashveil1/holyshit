# cc.hs - a tiny holyshit compiler written in holyshit.
#   hs run selfhost/cc.hs prog.hs out     (then ./out)
# It parses with selfhost/parselib.hs (the hs-written parser) and emits a
# static x86-64 Linux ELF straight to disk with write_bytes. No gcc, no
# Python in the compile step. Subset: Int variables, + - * % & | ^ << >>,
# comparisons and/or/not (conditions only), if/elif/else, while, break,
# continue, def/return/recursion, print of Ints and string literals.
# Anything else is a compile error, never silently different output.
import parselib

CODE = []
LABELS = {}
FIX = []
STRS = []
ST = {"lbl": 0, "fn": null, "locals": {}, "funcs": {}, "globals": {}, "loops": [], "nglob": 0}
BASE = 4194304 + 120
GLOBALS_AT = 5242880

def fail(msg, ln):
  raise "cc: " + msg + " (line " + str(ln) + ")"

def byte(b):
  append(CODE, b)

def bs(xs):
  for x in xs:
    append(CODE, x)

def le32(v):
  return [v & 255, (v >> 8) & 255, (v >> 16) & 255, (v >> 24) & 255]

def le64(v):
  out = []
  i = 0
  while i < 8:
    append(out, (v >> (8 * i)) & 255)
    i = i + 1
  return out

def label(name):
  LABELS[name] = len(CODE)

def new_label(p):
  ST["lbl"] = ST["lbl"] + 1
  return p + str(ST["lbl"])

def jump(op, name):
  bs(op)
  append(FIX, [len(CODE), name, "rel"])
  bs(le32(0))

def patch32(pos, v):
  b = le32(v)
  i = 0
  while i < 4:
    CODE[pos + i] = b[i]
    i = i + 1

# ---- variables -------------------------------------------------------
def var_loc(name, ln):
  if name in ST["locals"]:
    return ["rbp", ST["locals"][name]]
  if name in ST["globals"]:
    return ["abs", ST["globals"][name]]
  fail("unknown variable '" + name + "'", ln)

def load_var(name, ln):
  loc = var_loc(name, ln)
  if loc[0] == "rbp":
    bs([72, 139, 133])
  else:
    bs([72, 139, 4, 37])
  bs(le32(loc[1]))

def store_var(name, ln):
  loc = var_loc(name, ln)
  if loc[0] == "rbp":
    bs([72, 137, 133])
  else:
    bs([72, 137, 4, 37])
  bs(le32(loc[1]))

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
CMP = {"<": 156, "<=": 158, ">": 159, ">=": 157, "==": 148, "!=": 149}
ARITH = {"+": [72, 1, 200], "-": [72, 41, 200], "*": [72, 15, 175, 193], "&": [72, 33, 200], "|": [72, 9, 200], "^": [72, 49, 200]}

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
  byte(80)
  gen_int(e["r"])
  bs([72, 137, 193])
  byte(88)

def gen(e):
  t = e["t"]
  ln = e["line"]
  if t == "num":
    v = e["val"]
    for ch in str(v):
      if find("-0123456789", ch) < 0:
        fail("only Int literals are supported (no Float/Bool/null)", ln)
    bs([72, 184])
    bs(le64(v))
  elif t == "var":
    load_var(e["name"], ln)
  elif t == "neg":
    gen_int(e["val"])
    bs([72, 247, 216])
  elif t == "not":
    gen(e["val"])
    bs([72, 133, 192, 15, 148, 192, 15, 182, 192])
  elif t == "bin":
    op = e["op"]
    if op == "and" or op == "or":
      if not is_bool(e["l"]) or not is_bool(e["r"]):
        fail("and/or only on comparisons in cc subset", ln)
      end = new_label("L")
      gen(e["l"])
      bs([72, 133, 192])
      if op == "and":
        jump([15, 132], end)
      else:
        jump([15, 133], end)
      gen(e["r"])
      label(end)
    elif op in CMP:
      if is_bool(e["l"]) or is_bool(e["r"]):
        fail("comparing Bool values not supported", ln)
      gen_pair(e)
      bs([72, 57, 200, 15, CMP[op], 192, 15, 182, 192])
    elif op in ARITH:
      gen_pair(e)
      bs(ARITH[op])
    elif op == "%":
      gen_pair(e)
      # floor modulo like Python: cqo; idiv rcx; fix sign of the remainder
      done = new_label("L")
      bs([72, 153, 72, 247, 249, 72, 137, 208, 72, 133, 210])
      jump([15, 132], done)
      bs([72, 49, 202])
      jump([15, 137], done)
      bs([72, 1, 200])
      label(done)
    elif op == "<<" or op == ">>":
      gen_pair(e)
      if op == "<<":
        bs([72, 211, 224])
      else:
        bs([72, 211, 248])
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
      byte(80)
    jump([232], "f_" + nm)
    if len(e["args"]) > 0:
      bs([72, 129, 196])
      bs(le32(8 * len(e["args"])))
  else:
    fail("expression '" + t + "' not supported", ln)

# ---- statements ------------------------------------------------------
def gen_cond_jz(c, target):
  if not is_bool(c):
    fail("condition must be a comparison / and / or / not in cc subset", c["line"])
  gen(c)
  bs([72, 133, 192])
  jump([15, 132], target)

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
  bs([72, 199, 198])
  append(FIX, [len(CODE), lab, "abs"])
  bs(le32(0))
  byte(186)
  bs(le32(len(s)))
  bs([191, 1, 0, 0, 0, 184, 1, 0, 0, 0, 15, 5])

def put_char(c):
  byte(184)
  bs(le32(c))
  jump([232], "rt_putc")

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
        jump([232], "rt_puti")
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
    jump([233], end)
    label(nxt)
    for ec in s["elifs"]:
      nxt = new_label("N")
      gen_cond_jz(ec[0], nxt)
      gen_body(ec[1])
      jump([233], end)
      label(nxt)
    gen_body(s["els"])
    label(end)
  elif t == "while":
    top = new_label("W")
    out = new_label("X")
    label(top)
    gen_cond_jz(s["cond"], out)
    append(ST["loops"], [top, out])
    gen_body(s["body"])
    ST["loops"] = ST["loops"][0:len(ST["loops"]) - 1]
    jump([233], top)
    label(out)
  elif t == "break" or t == "continue":
    if len(ST["loops"]) == 0:
      fail(t + " outside loop", ln)
    lp = ST["loops"][len(ST["loops"]) - 1]
    if t == "break":
      jump([233], lp[1])
    else:
      jump([233], lp[0])
  elif t == "return":
    if ST["fn"] == null:
      fail("return outside function", ln)
    if s["val"] == null:
      bs([49, 192])
    else:
      gen_int(s["val"])
    jump([233], "r_" + ST["fn"])
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
  label("f_" + nm)
  byte(85)
  bs([72, 137, 229])
  if nl > 0:
    bs([72, 129, 236])
    bs(le32(8 * nl))
    # zero the locals so a stray read is deterministic
    j = 1
    while j <= nl:
      bs([72, 199, 133])
      bs(le32(0 - 8 * j))
      bs(le32(0))
      j = j + 1
  gen_body(d["body"])
  bs([49, 192])
  label("r_" + nm)
  bs([72, 137, 236, 93, 195])
  ST["fn"] = null
  ST["locals"] = {}

def gen_runtime():
  # rt_putc: write the byte in al
  label("rt_putc")
  bs([80, 72, 137, 230, 186, 1, 0, 0, 0, 191, 1, 0, 0, 0, 184, 1, 0, 0, 0, 15, 5, 88, 195])
  # rt_puti: print the Int in rax in decimal (no newline)
  label("rt_puti")
  bs([85, 72, 137, 229, 72, 131, 236, 48])
  bs([72, 137, 193])
  bs([72, 141, 117, 255])
  bs([191, 0, 0, 0, 0])
  bs([72, 133, 201])
  bs([15, 137, 8, 0, 0, 0])
  bs([72, 247, 217])
  bs([191, 1, 0, 0, 0])
  bs([65, 185, 10, 0, 0, 0])
  # loop: xor edx,edx; mov rax,rcx; div r9; add dl,'0'; mov [rsi],dl; dec rsi; mov rcx,rax; test rcx,rcx; jnz loop
  bs([49, 210, 72, 137, 200, 73, 247, 241, 128, 194, 48, 136, 22, 72, 255, 206, 72, 137, 193, 72, 133, 201])
  bs([15, 133])
  bs(le32(0 - 28))
  # sign: test edi,edi; jz skip; mov byte [rsi],'-'; dec rsi
  bs([133, 255, 15, 132, 6, 0, 0, 0, 198, 6, 45, 72, 255, 206])
  # inc rsi; mov rdx,rbp; sub rdx,rsi; write(1, rsi, rdx)
  bs([72, 255, 198, 72, 137, 234, 72, 41, 242, 191, 1, 0, 0, 0, 184, 1, 0, 0, 0, 15, 5])
  bs([72, 137, 236, 93, 195])

def compile(prog):
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
    ST["globals"][k] = GLOBALS_AT + 8 * ST["nglob"]
    ST["nglob"] = ST["nglob"] + 1
  gen_body(top)
  bs([191, 0, 0, 0, 0, 184, 60, 0, 0, 0, 15, 5])
  for s in prog:
    if s["t"] == "def":
      gen_func(s)
  gen_runtime()
  for st in STRS:
    label(st[0])
    for ch in st[1]:
      byte(ascii_byte(ch, st[2]))
  for f in FIX:
    if not (f[1] in LABELS):
      raise "cc: internal: label " + f[1]
    if f[2] == "rel":
      patch32(f[0], LABELS[f[1]] - (f[0] + 4))
    else:
      patch32(f[0], BASE + LABELS[f[1]])
  if len(CODE) > 900000:
    raise "cc: program too large"

def elf():
  n = 120 + len(CODE)
  h = [127, 69, 76, 70, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
  h = h + [2, 0, 62, 0, 1, 0, 0, 0]
  h = h + le64(BASE) + le64(64) + le64(0)
  h = h + [0, 0, 0, 0, 64, 0, 56, 0, 1, 0, 0, 0, 0, 0, 0, 0]
  h = h + [1, 0, 0, 0, 7, 0, 0, 0] + le64(0) + le64(4194304) + le64(4194304)
  h = h + le64(n) + le64(2097152) + le64(4096)
  return h + CODE

a = argv()
if len(a) != 2:
  print "usage: hs run selfhost/cc.hs prog.hs out"
  raise "usage"
try:
  prog = parselib.parse(read_text(a[0]))
  compile(prog)
  write_bytes(a[1], elf())
except as e:
  print "error: " + parselib.strip_raise(e)
  raise "compile failed"
