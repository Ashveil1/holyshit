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
# Values are tagged words: Int = 2n+1 (63-bit, overflow traps with exit 97),
# false = 2, true = 10, null = 6; heap pointers (later) have low bits 000.
CMP = {"<": "l", "<=": "le", ">": "g", ">=": "ge"}

def chk_int2():
  # rax, rcx must both be Ints (low bit set) or it is a type error
  asm.mov_rr("rdx", "rax")
  asm.and_rr("rdx", "rcx")
  asm.and_ri32("rdx", 1)
  asm.jcc("e", "rt_err_type")

def gen_pair(e):
  gen(e["l"])
  asm.push_r("rax")
  gen(e["r"])
  asm.mov_rr("rcx", "rax")
  asm.pop_r("rax")

def to_bool():
  # al = 0/1 from setcc -> tagged Bool
  asm.movzx_eax_al()
  asm.shl_ri8("rax", 3)
  asm.add_ri32("rax", 2)

def retag():
  asm.add_rr("rax", "rax")
  asm.jcc("o", "rt_err_ovf")
  asm.add_ri32("rax", 1)

def gen(e):
  t = e["t"]
  ln = e["line"]
  if t == "num":
    v = e["val"]
    sv = str(v)
    if sv == "true":
      asm.mov_ri32("rax", 10)
    elif sv == "false":
      asm.mov_ri32("rax", 2)
    elif sv == "null":
      asm.mov_ri32("rax", 6)
    else:
      for ch in sv:
        if find("-0123456789", ch) < 0:
          fail("only Int literals are supported (no Float)", ln)
      mag = sv
      if mag[0] == "-":
        mag = mag[1:]
      if len(mag) > 19 or (len(mag) == 19 and mag > "4611686018427387903"):
        fail("Int literal outside the 63-bit range of cc", ln)
      asm.mov_ri64("rax", v * 2 + 1)
  elif t == "var":
    load_var(e["name"], ln)
  elif t == "neg":
    gen(e["val"])
    asm.mov_rr("rdx", "rax")
    asm.and_ri32("rdx", 1)
    asm.jcc("e", "rt_err_type")
    asm.mov_ri32("rdx", 2)
    asm.sub_rr("rdx", "rax")
    asm.jcc("o", "rt_err_ovf")
    asm.mov_rr("rax", "rdx")
  elif t == "not":
    gen(e["val"])
    asm.call("rt_truthy")
    asm.mov_ri32("rax", 1)
    asm.sub_rr("rax", "rdx")
    asm.shl_ri8("rax", 3)
    asm.add_ri32("rax", 2)
  elif t == "bin":
    op = e["op"]
    if op == "and" or op == "or":
      end = new_label("L")
      gen(e["l"])
      asm.call("rt_truthy")
      asm.test_rr("rdx", "rdx")
      if op == "and":
        asm.jcc("e", end)
      else:
        asm.jcc("ne", end)
      gen(e["r"])
      asm.label(end)
    elif op == "==" or op == "!=":
      gen_pair(e)
      asm.call("rt_eq")
      if op == "!=":
        asm.mov_ri32("rdx", 8)
        asm.xor_rr("rax", "rdx")
    elif op in CMP:
      gen_pair(e)
      chk_int2()
      asm.cmp_rr("rax", "rcx")
      asm.setcc_al(CMP[op])
      to_bool()
    elif op == "+":
      gen_pair(e)
      chk_int2()
      asm.sub_ri32("rax", 1)
      asm.add_rr("rax", "rcx")
      asm.jcc("o", "rt_err_ovf")
    elif op == "-":
      gen_pair(e)
      chk_int2()
      asm.sub_rr("rax", "rcx")
      asm.jcc("o", "rt_err_ovf")
      asm.add_ri32("rax", 1)
    elif op == "*":
      gen_pair(e)
      chk_int2()
      asm.sar_ri8("rax", 1)
      asm.sub_ri32("rcx", 1)
      asm.imul_rr("rax", "rcx")
      asm.jcc("o", "rt_err_ovf")
      asm.add_ri32("rax", 1)
    elif op == "&":
      gen_pair(e)
      chk_int2()
      asm.and_rr("rax", "rcx")
    elif op == "|":
      gen_pair(e)
      chk_int2()
      asm.or_rr("rax", "rcx")
    elif op == "^":
      gen_pair(e)
      chk_int2()
      asm.xor_rr("rax", "rcx")
      asm.add_ri32("rax", 1)
    elif op == "%":
      gen_pair(e)
      chk_int2()
      # floor modulo like Python on the untagged values, then retag
      done = new_label("L")
      asm.sar_ri8("rax", 1)
      asm.sar_ri8("rcx", 1)
      asm.test_rr("rcx", "rcx")
      asm.jcc("e", "rt_err_div")
      asm.cqo()
      asm.idiv_r("rcx")
      asm.mov_rr("rax", "rdx")
      asm.test_rr("rdx", "rdx")
      asm.jcc("e", done)
      asm.xor_rr("rdx", "rcx")
      asm.jcc("ns", done)
      asm.add_rr("rax", "rcx")
      asm.label(done)
      retag()
    elif op == "<<" or op == ">>":
      gen_pair(e)
      chk_int2()
      asm.sar_ri8("rax", 1)
      asm.sar_ri8("rcx", 1)
      asm.cmp_ri32("rcx", 0)
      asm.jcc("l", "rt_err_shift")
      asm.cmp_ri32("rcx", 63)
      asm.jcc("g", "rt_err_shift")
      if op == ">>":
        asm.sar_cl("rax")
      else:
        asm.mov_rr("rdx", "rax")
        asm.shl_cl("rax")
        asm.mov_rr("r8", "rax")
        asm.sar_cl("r8")
        asm.cmp_rr("r8", "rdx")
        asm.jcc("ne", "rt_err_ovf")
      retag()
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
      gen(a)
      asm.push_r("rax")
    asm.call("f_" + nm)
    if len(e["args"]) > 0:
      asm.add_ri32("rsp", 8 * len(e["args"]))
  else:
    fail("expression '" + t + "' not supported", ln)

# ---- statements ------------------------------------------------------
def gen_cond_jz(c, target):
  gen(c)
  asm.call("rt_truthy")
  asm.test_rr("rdx", "rdx")
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
    gen(s["val"])
    store_var(s["name"], ln)
  elif t == "print":
    n = len(s["args"])
    i = 0
    for a in s["args"]:
      if a["t"] == "str":
        put_str(a["val"], ln)
      else:
        gen(a)
        asm.call("rt_print")
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
      asm.mov_ri32("rax", 6)
    else:
      gen(s["val"])
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
    # locals start as null so a stray read is deterministic
    asm.mov_ri32("rax", 6)
    j = 1
    while j <= nl:
      asm.mov_mr("rbp", "rax", 0 - 8 * j)
      j = j + 1
  gen_body(d["body"])
  asm.mov_ri32("rax", 6)
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

def write_lit(lab, n):
  asm.lea_rip("rsi", lab)
  asm.mov_ri32("rdx", n)
  asm.mov_ri32("rdi", 1)
  asm.mov_ri32("rax", 1)
  asm.syscall()
  asm.ret()

def err_routine(name, lab, n, code):
  asm.label(name)
  asm.lea_rip("rsi", lab)
  asm.mov_ri32("rdx", n)
  asm.mov_ri32("rdi", 2)
  asm.mov_ri32("rax", 1)
  asm.syscall()
  asm.mov_ri32("rdi", code)
  asm.mov_ri32("rax", 60)
  asm.syscall()

def data_text(lab, text):
  asm.label(lab)
  for ch in text:
    asm.b1(ascii_byte(ch, 0))

MSG = [["m_true", "true"], ["m_false", "false"], ["m_null", "null"], ["m_ovf", "error: Int outside the 63-bit range of the cc backend\n"], ["m_type", "error: type error (cc backend)\n"], ["m_div", "error: division by zero\n"], ["m_shift", "error: shift count out of range\n"]]

def gen_runtime2():
  # rt_truthy: rdx = 1 if rax is truthy else 0 (rax kept). falsy: 0, false, null
  asm.label("rt_truthy")
  asm.cmp_ri32("rax", 1)
  asm.jcc("e", "tr_f")
  asm.cmp_ri32("rax", 2)
  asm.jcc("e", "tr_f")
  asm.cmp_ri32("rax", 6)
  asm.jcc("e", "tr_f")
  asm.mov_ri32("rdx", 1)
  asm.ret()
  asm.label("tr_f")
  asm.mov_ri32("rdx", 0)
  asm.ret()
  # rt_eq: rax == rcx -> tagged Bool in rax; true == 1 and false == 0 like interp
  asm.label("rt_eq")
  asm.cmp_rr("rax", "rcx")
  asm.jcc("e", "eq_yes")
  asm.cmp_ri32("rcx", 10)
  asm.jcc("ne", "eq_1")
  asm.mov_ri32("rdx", 3)
  asm.cmp_rr("rax", "rdx")
  asm.jcc("e", "eq_yes")
  asm.jmp("eq_no")
  asm.label("eq_1")
  asm.cmp_ri32("rcx", 2)
  asm.jcc("ne", "eq_2")
  asm.mov_ri32("rdx", 1)
  asm.cmp_rr("rax", "rdx")
  asm.jcc("e", "eq_yes")
  asm.jmp("eq_no")
  asm.label("eq_2")
  asm.cmp_ri32("rax", 10)
  asm.jcc("ne", "eq_3")
  asm.mov_ri32("rdx", 3)
  asm.cmp_rr("rcx", "rdx")
  asm.jcc("e", "eq_yes")
  asm.jmp("eq_no")
  asm.label("eq_3")
  asm.cmp_ri32("rax", 2)
  asm.jcc("ne", "eq_no")
  asm.mov_ri32("rdx", 1)
  asm.cmp_rr("rcx", "rdx")
  asm.jcc("e", "eq_yes")
  asm.label("eq_no")
  asm.mov_ri32("rax", 2)
  asm.ret()
  asm.label("eq_yes")
  asm.mov_ri32("rax", 10)
  asm.ret()
  # rt_print: print the tagged value in rax (no newline)
  asm.label("rt_print")
  asm.mov_rr("rdx", "rax")
  asm.and_ri32("rdx", 1)
  asm.jcc("e", "pr_imm")
  asm.sar_ri8("rax", 1)
  asm.jmp("rt_puti")
  asm.label("pr_imm")
  asm.cmp_ri32("rax", 10)
  asm.jcc("ne", "pr_1")
  write_lit("m_true", 4)
  asm.label("pr_1")
  asm.cmp_ri32("rax", 2)
  asm.jcc("ne", "pr_2")
  write_lit("m_false", 5)
  asm.label("pr_2")
  asm.cmp_ri32("rax", 6)
  asm.jcc("ne", "rt_err_type")
  write_lit("m_null", 4)
  err_routine("rt_err_ovf", "m_ovf", len(MSG[3][1]), 97)
  err_routine("rt_err_type", "m_type", len(MSG[4][1]), 1)
  err_routine("rt_err_div", "m_div", len(MSG[5][1]), 1)
  err_routine("rt_err_shift", "m_shift", len(MSG[6][1]), 1)

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
  gen_runtime2()
  for m in MSG:
    data_text(m[0], m[1])
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
