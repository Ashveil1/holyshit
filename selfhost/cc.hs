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
SOBJ = []
ST = {"lbl": 0, "fn": null, "locals": {}, "funcs": {}, "globals": {}, "loops": []}
BASE = 4194304 + 120
HEAP_END = 4194304 + 268435456

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
    elif t == "for":
      out[s["var"]] = true
      out["%i" + str(s["line"])] = true
      out["%n" + str(s["line"])] = true
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
  elif t == "str":
    lab = new_label("O")
    append(SOBJ, [lab, e["val"], ln])
    asm.lea_rip("rax", lab)
  elif t == "list":
    for it in e["items"]:
      gen(it)
      asm.push_r("rax")
    asm.mov_ri32("rcx", len(e["items"]))
    asm.call("rt_mklist")
    if len(e["items"]) > 0:
      asm.add_ri32("rsp", 8 * len(e["items"]))
  elif t == "index":
    if has(e, "tern") or has(e, "dot"):
      fail("expression 'index' form not supported", ln)
    gen(e["obj"])
    asm.push_r("rax")
    gen(e["idx"])
    asm.mov_rr("rcx", "rax")
    asm.pop_r("rax")
    asm.call("rt_index")
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
      lf = new_label("L")
      ld = new_label("L")
      asm.mov_rr("rdx", "rax")
      asm.and_rr("rdx", "rcx")
      asm.and_ri32("rdx", 1)
      asm.jcc("ne", lf)
      asm.call("rt_scmp")
      asm.cmp_ri32("rdx", 0)
      asm.jmp(ld)
      asm.label(lf)
      asm.cmp_rr("rax", "rcx")
      asm.label(ld)
      asm.setcc_al(CMP[op])
      to_bool()
    elif op == "+":
      gen_pair(e)
      lf = new_label("L")
      ld = new_label("L")
      asm.mov_rr("rdx", "rax")
      asm.and_rr("rdx", "rcx")
      asm.and_ri32("rdx", 1)
      asm.jcc("ne", lf)
      asm.call("rt_str_add")
      asm.jmp(ld)
      asm.label(lf)
      asm.sub_ri32("rax", 1)
      asm.add_rr("rax", "rcx")
      asm.jcc("o", "rt_err_ovf")
      asm.label(ld)
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
    if nm == "len" and not (nm in ST["funcs"]):
      if len(e["args"]) != 1:
        fail("len wants 1 arg", ln)
      gen(e["args"][0])
      asm.mov_rr("rdx", "rax")
      asm.and_ri32("rdx", 7)
      asm.jcc("ne", "rt_err_type")
      asm.mov_rm("rax", "rax", 8)
      retag()
      return 0
    if nm == "append" and not (nm in ST["funcs"]):
      if len(e["args"]) != 2:
        fail("append wants 2 args", ln)
      gen(e["args"][0])
      asm.push_r("rax")
      gen(e["args"][1])
      asm.pop_r("rsi")
      asm.call("rt_append")
      return 0
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
  elif t == "setindex":
    if s["dot"] != null:
      fail("attribute assignment not supported", ln)
    gen(s["obj"])
    asm.push_r("rax")
    gen(s["idx"])
    asm.push_r("rax")
    gen(s["val"])
    asm.pop_r("rcx")
    asm.pop_r("rsi")
    asm.call("rt_setidx")
  elif t == "for":
    gen_for(s)
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

def gen_for(s):
  ln = s["line"]
  it = s["iter"]
  vi = "%i" + str(ln)
  vn = "%n" + str(ln)
  top = new_label("F")
  cont = new_label("C")
  out = new_label("X")
  if it["t"] == "call" and it["fn"]["t"] == "var" and it["fn"]["name"] == "range" and not ("range" in ST["funcs"]):
    na = len(it["args"])
    if na < 1 or na > 2:
      fail("range wants 1 or 2 args", ln)
    if na == 2:
      gen(it["args"][0])
    else:
      asm.mov_ri32("rax", 1)
    asm.mov_rr("rdx", "rax")
    asm.and_ri32("rdx", 1)
    asm.jcc("e", "rt_err_type")
    store_var(vi, ln)
    gen(it["args"][na - 1])
    asm.mov_rr("rdx", "rax")
    asm.and_ri32("rdx", 1)
    asm.jcc("e", "rt_err_type")
    store_var(vn, ln)
    asm.label(top)
    load_var(vi, ln)
    asm.mov_rr("rcx", "rax")
    load_var(vn, ln)
    asm.cmp_rr("rcx", "rax")
    asm.jcc("ge", out)
    asm.mov_rr("rax", "rcx")
    store_var(s["var"], ln)
  else:
    gen(it)
    asm.call("rt_chklist")
    store_var(vn, ln)
    asm.mov_ri32("rax", 1)
    store_var(vi, ln)
    asm.label(top)
    load_var(vn, ln)
    asm.mov_rr("rsi", "rax")
    asm.mov_rm("rdx", "rsi", 8)
    asm.add_rr("rdx", "rdx")
    asm.add_ri32("rdx", 1)
    load_var(vi, ln)
    asm.cmp_rr("rax", "rdx")
    asm.jcc("ge", out)
    asm.sar_ri8("rax", 1)
    asm.mov_rm("rcx", "rsi", 24)
    asm.mov_rmx("rax", "rcx", "rax", 8, 0)
    store_var(s["var"], ln)
  append(ST["loops"], [cont, out])
  gen_body(s["body"])
  ST["loops"] = ST["loops"][0:len(ST["loops"]) - 1]
  asm.label(cont)
  load_var(vi, ln)
  asm.add_ri32("rax", 2)
  store_var(vi, ln)
  asm.jmp(top)
  asm.label(out)

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

MSG = [["m_true", "true"], ["m_false", "false"], ["m_null", "null"], ["m_ovf", "error: Int outside the 63-bit range of the cc backend\n"], ["m_type", "error: type error (cc backend)\n"], ["m_div", "error: division by zero\n"], ["m_shift", "error: shift count out of range\n"], ["m_oom", "error: out of memory\n"], ["m_idx", "error: index out of range\n"]]

def gen_runtime2():
  # rt_truthy: rdx = 1 if rax is truthy else 0 (rax kept). falsy: 0, false, null
  asm.label("rt_truthy")
  asm.cmp_ri32("rax", 1)
  asm.jcc("e", "tr_f")
  asm.cmp_ri32("rax", 2)
  asm.jcc("e", "tr_f")
  asm.cmp_ri32("rax", 6)
  asm.jcc("e", "tr_f")
  asm.mov_rr("rdx", "rax")
  asm.and_ri32("rdx", 7)
  asm.jcc("ne", "tr_t")
  asm.mov_rm("rdx", "rax", 8)
  asm.test_rr("rdx", "rdx")
  asm.jcc("e", "tr_f")
  asm.label("tr_t")
  asm.mov_ri32("rdx", 1)
  asm.ret()
  asm.label("tr_f")
  asm.mov_ri32("rdx", 0)
  asm.ret()
  # rt_eq: rax == rcx -> tagged Bool in rax; true == 1 and false == 0 like interp
  asm.label("rt_eq")
  asm.cmp_rr("rax", "rcx")
  asm.jcc("e", "eq_yes")
  asm.mov_rr("rdx", "rax")
  asm.or_rr("rdx", "rcx")
  asm.and_ri32("rdx", 7)
  asm.jcc("e", "rt_streq")
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
  asm.and_ri32("rdx", 7)
  asm.jcc("e", "pr_ptr")
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
  asm.label("pr_ptr")
  asm.mov_rm("rdx", "rax", 0)
  asm.cmp_ri32("rdx", 2)
  asm.jcc("e", "pr_list")
  asm.mov_rm("rdx", "rax", 8)
  asm.lea_m("rsi", "rax", 16)
  asm.mov_ri32("rdi", 1)
  asm.mov_ri32("rax", 1)
  asm.syscall()
  asm.ret()
  asm.label("pr_list")
  asm.push_r("rax")
  asm.mov_ri32("rcx", 0)
  asm.push_r("rcx")
  asm.mov_ri32("rax", 91)
  asm.call("rt_putc")
  asm.label("pl_l")
  asm.mov_rm("rdx", "rsp", 0)
  asm.mov_rm("rax", "rsp", 8)
  asm.mov_rm("r8", "rax", 8)
  asm.cmp_rr("rdx", "r8")
  asm.jcc("e", "pl_d")
  asm.test_rr("rdx", "rdx")
  asm.jcc("e", "pl_f")
  asm.mov_ri32("rax", 44)
  asm.call("rt_putc")
  asm.mov_ri32("rax", 32)
  asm.call("rt_putc")
  asm.label("pl_f")
  asm.mov_rm("rdx", "rsp", 0)
  asm.mov_rm("rax", "rsp", 8)
  asm.mov_rm("rax", "rax", 24)
  asm.mov_rmx("rax", "rax", "rdx", 8, 0)
  asm.call("rt_print")
  asm.mov_rm("rdx", "rsp", 0)
  asm.add_ri32("rdx", 1)
  asm.mov_mr("rsp", "rdx", 0)
  asm.jmp("pl_l")
  asm.label("pl_d")
  asm.add_ri32("rsp", 16)
  asm.mov_ri32("rax", 93)
  asm.call("rt_putc")
  asm.ret()
  gen_runtime3()
  gen_runtime4()
  err_routine("rt_err_oom", "m_oom", len(MSG[7][1]), 1)
  err_routine("rt_err_idx", "m_idx", len(MSG[8][1]), 1)
  err_routine("rt_err_ovf", "m_ovf", len(MSG[3][1]), 97)
  err_routine("rt_err_type", "m_type", len(MSG[4][1]), 1)
  err_routine("rt_err_div", "m_div", len(MSG[5][1]), 1)
  err_routine("rt_err_shift", "m_shift", len(MSG[6][1]), 1)

def chk_str2():
  # rax, rcx must both be heap Strs (low 3 bits 0, kind 1)
  asm.mov_rr("rdx", "rax")
  asm.or_rr("rdx", "rcx")
  asm.and_ri32("rdx", 7)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rm("rdx", "rax", 0)
  asm.cmp_ri32("rdx", 1)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rm("rdx", "rcx", 0)
  asm.cmp_ri32("rdx", 1)
  asm.jcc("ne", "rt_err_type")

def gen_runtime3():
  # rt_alloc: rdi = bytes (multiple of 8) -> rax = zeroed bump block
  asm.label("rt_alloc")
  asm.mov_rm_rip("rax", "hp")
  asm.mov_rr("rdx", "rax")
  asm.add_rr("rdx", "rdi")
  asm.mov_ri64("rsi", HEAP_END)
  asm.cmp_rr("rdx", "rsi")
  asm.jcc("g", "rt_err_oom")
  asm.mov_mr_rip("hp", "rdx")
  asm.ret()
  # rt_memcpy: copy rdx bytes rsi -> rdi; rdi ends past the copy
  asm.label("rt_memcpy")
  asm.xor_rr("r11", "r11")
  asm.label("mc_l")
  asm.cmp_rr("r11", "rdx")
  asm.jcc("e", "mc_d")
  asm.movzx_rm8x("r10", "rsi", "r11", 1, 0)
  asm.mov_mr8("rdi", 10, 0)
  asm.add_ri32("rdi", 1)
  asm.add_ri32("r11", 1)
  asm.jmp("mc_l")
  asm.label("mc_d")
  asm.ret()
  # rt_str_add: rax + rcx (both Str) -> new Str
  asm.label("rt_str_add")
  chk_str2()
  asm.mov_rm("r8", "rax", 8)
  asm.mov_rm("r9", "rcx", 8)
  asm.push_r("rax")
  asm.push_r("rcx")
  asm.mov_rr("rdi", "r8")
  asm.add_rr("rdi", "r9")
  asm.add_ri32("rdi", 23)
  asm.and_ri32("rdi", 0 - 8)
  asm.call("rt_alloc")
  asm.mov_ri32("rdx", 1)
  asm.mov_mr("rax", "rdx", 0)
  asm.mov_rr("rdx", "r8")
  asm.add_rr("rdx", "r9")
  asm.mov_mr("rax", "rdx", 8)
  asm.push_r("rax")
  asm.mov_rm("rsi", "rsp", 16)
  asm.add_ri32("rsi", 16)
  asm.lea_m("rdi", "rax", 16)
  asm.mov_rr("rdx", "r8")
  asm.call("rt_memcpy")
  asm.mov_rm("rsi", "rsp", 8)
  asm.add_ri32("rsi", 16)
  asm.mov_rr("rdx", "r9")
  asm.call("rt_memcpy")
  asm.pop_r("rax")
  asm.add_ri32("rsp", 16)
  asm.ret()
  # rt_scmp: Str compare of rax, rcx -> rdx = -1 / 0 / 1
  asm.label("rt_scmp")
  chk_str2()
  asm.mov_rm("r8", "rax", 8)
  asm.mov_rm("r9", "rcx", 8)
  asm.add_ri32("rax", 16)
  asm.add_ri32("rcx", 16)
  asm.xor_rr("r11", "r11")
  asm.label("sc_l")
  asm.cmp_rr("r11", "r8")
  asm.jcc("e", "sc_ae")
  asm.cmp_rr("r11", "r9")
  asm.jcc("e", "sc_gt")
  asm.movzx_rm8x("r10", "rax", "r11", 1, 0)
  asm.movzx_rm8x("rsi", "rcx", "r11", 1, 0)
  asm.cmp_rr("r10", "rsi")
  asm.jcc("l", "sc_lt")
  asm.jcc("g", "sc_gt")
  asm.add_ri32("r11", 1)
  asm.jmp("sc_l")
  asm.label("sc_ae")
  asm.cmp_rr("r11", "r9")
  asm.jcc("ne", "sc_lt")
  asm.mov_ri32("rdx", 0)
  asm.ret()
  asm.label("sc_lt")
  asm.mov_ri32("rdx", 0)
  asm.sub_ri32("rdx", 1)
  asm.ret()
  asm.label("sc_gt")
  asm.mov_ri32("rdx", 1)
  asm.ret()
  # rt_streq: both heap pointers, not identical -> tagged Bool in rax
  asm.label("rt_streq")
  asm.mov_rm("rdx", "rax", 0)
  asm.mov_rm("rsi", "rcx", 0)
  asm.cmp_ri32("rdx", 2)
  asm.jcc("ne", "se_s")
  asm.cmp_ri32("rsi", 2)
  asm.jcc("e", "rt_leq")
  asm.jmp("eq_no")
  asm.label("se_s")
  asm.cmp_ri32("rdx", 1)
  asm.jcc("ne", "eq_no")
  asm.mov_rm("rdx", "rcx", 0)
  asm.cmp_ri32("rdx", 1)
  asm.jcc("ne", "eq_no")
  asm.mov_rm("rdx", "rax", 8)
  asm.mov_rm("rsi", "rcx", 8)
  asm.cmp_rr("rdx", "rsi")
  asm.jcc("ne", "eq_no")
  asm.add_ri32("rax", 16)
  asm.add_ri32("rcx", 16)
  asm.xor_rr("r11", "r11")
  asm.label("se_l")
  asm.cmp_rr("r11", "rdx")
  asm.jcc("e", "eq_yes")
  asm.movzx_rm8x("r10", "rax", "r11", 1, 0)
  asm.movzx_rm8x("rsi", "rcx", "r11", 1, 0)
  asm.cmp_rr("r10", "rsi")
  asm.jcc("ne", "eq_no")
  asm.add_ri32("r11", 1)
  asm.jmp("se_l")
  # rt_index: rax[rcx] on a Str -> 1-char Str
  asm.label("rt_index")
  asm.mov_rr("rdx", "rax")
  asm.and_ri32("rdx", 7)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rr("rdx", "rcx")
  asm.and_ri32("rdx", 1)
  asm.jcc("e", "rt_err_type")
  asm.sar_ri8("rcx", 1)
  asm.mov_rm("r8", "rax", 8)
  asm.test_rr("rcx", "rcx")
  asm.jcc("ns", "ix_p")
  asm.add_rr("rcx", "r8")
  asm.label("ix_p")
  asm.cmp_ri32("rcx", 0)
  asm.jcc("l", "rt_err_idx")
  asm.cmp_rr("rcx", "r8")
  asm.jcc("ge", "rt_err_idx")
  asm.mov_rm("rdx", "rax", 0)
  asm.cmp_ri32("rdx", 2)
  asm.jcc("ne", "ix_s")
  asm.mov_rm("rax", "rax", 24)
  asm.mov_rmx("rax", "rax", "rcx", 8, 0)
  asm.ret()
  asm.label("ix_s")
  asm.cmp_ri32("rdx", 1)
  asm.jcc("ne", "rt_err_type")
  asm.add_ri32("rax", 16)
  asm.movzx_rm8x("r10", "rax", "rcx", 1, 0)
  asm.mov_ri32("rdi", 24)
  asm.push_r("r10")
  asm.call("rt_alloc")
  asm.pop_r("r10")
  asm.mov_ri32("rdx", 1)
  asm.mov_mr("rax", "rdx", 0)
  asm.mov_mr("rax", "rdx", 8)
  asm.mov_mr8("rax", 10, 16)
  asm.ret()

def gen_runtime4():
  # rt_chklist: rax must be a List; kept
  asm.label("rt_chklist")
  asm.mov_rr("rdx", "rax")
  asm.and_ri32("rdx", 7)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rm("rdx", "rax", 0)
  asm.cmp_ri32("rdx", 2)
  asm.jcc("ne", "rt_err_type")
  asm.ret()
  # rt_mklist: rcx = n items sitting on the stack above the return address
  asm.label("rt_mklist")
  asm.mov_ri32("rdi", 32)
  asm.push_r("rcx")
  asm.call("rt_alloc")
  asm.pop_r("rcx")
  asm.push_r("rax")
  asm.mov_rr("rdi", "rcx")
  asm.shl_ri8("rdi", 3)
  asm.push_r("rcx")
  asm.call("rt_alloc")
  asm.pop_r("rcx")
  asm.pop_r("rsi")
  asm.mov_ri32("rdx", 2)
  asm.mov_mr("rsi", "rdx", 0)
  asm.mov_mr("rsi", "rcx", 8)
  asm.mov_mr("rsi", "rcx", 16)
  asm.mov_mr("rsi", "rax", 24)
  asm.xor_rr("rdx", "rdx")
  asm.label("ml_l")
  asm.cmp_rr("rdx", "rcx")
  asm.jcc("e", "ml_d")
  asm.mov_rmx("r8", "rsp", "rdx", 8, 8)
  asm.mov_rr("r9", "rcx")
  asm.sub_rr("r9", "rdx")
  asm.sub_ri32("r9", 1)
  asm.lea_mx("r10", "rax", "r9", 8, 0)
  asm.mov_mr("r10", "r8", 0)
  asm.add_ri32("rdx", 1)
  asm.jmp("ml_l")
  asm.label("ml_d")
  asm.mov_rr("rax", "rsi")
  asm.ret()
  # rt_append: rsi = List, rax = value -> null
  asm.label("rt_append")
  asm.mov_rr("rdx", "rsi")
  asm.and_ri32("rdx", 7)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rm("rdx", "rsi", 0)
  asm.cmp_ri32("rdx", 2)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rm("r8", "rsi", 8)
  asm.mov_rm("r9", "rsi", 16)
  asm.cmp_rr("r8", "r9")
  asm.jcc("ne", "ap_ok")
  asm.mov_rr("rcx", "rax")
  asm.push_r("rsi")
  asm.push_r("rcx")
  asm.mov_rr("r9", "r9")
  asm.add_rr("r9", "r9")
  asm.test_rr("r9", "r9")
  asm.jcc("ne", "ap_1")
  asm.mov_ri32("r9", 4)
  asm.label("ap_1")
  asm.push_r("r9")
  asm.push_r("r8")
  asm.mov_rr("rdi", "r9")
  asm.shl_ri8("rdi", 3)
  asm.call("rt_alloc")
  asm.pop_r("r8")
  asm.pop_r("r9")
  asm.pop_r("rcx")
  asm.pop_r("rsi")
  asm.push_r("rsi")
  asm.push_r("rax")
  asm.push_r("rcx")
  asm.mov_rm("rsi", "rsi", 24)
  asm.mov_rr("rdi", "rax")
  asm.mov_rr("rdx", "r8")
  asm.shl_ri8("rdx", 3)
  asm.call("rt_memcpy")
  asm.pop_r("rcx")
  asm.pop_r("rax")
  asm.pop_r("rsi")
  asm.mov_mr("rsi", "rax", 24)
  asm.mov_mr("rsi", "r9", 16)
  asm.mov_rr("rax", "rcx")
  asm.label("ap_ok")
  asm.mov_rm("r8", "rsi", 8)
  asm.mov_rm("rdx", "rsi", 24)
  asm.lea_mx("rdx", "rdx", "r8", 8, 0)
  asm.mov_mr("rdx", "rax", 0)
  asm.add_ri32("r8", 1)
  asm.mov_mr("rsi", "r8", 8)
  asm.mov_ri32("rax", 6)
  asm.ret()
  # rt_setidx: rsi[rcx] = rax (List)
  asm.label("rt_setidx")
  asm.mov_rr("rdx", "rsi")
  asm.and_ri32("rdx", 7)
  asm.jcc("ne", "rt_err_type")
  asm.mov_rr("rdx", "rcx")
  asm.and_ri32("rdx", 1)
  asm.jcc("e", "rt_err_type")
  asm.mov_rm("rdx", "rsi", 0)
  asm.cmp_ri32("rdx", 2)
  asm.jcc("ne", "rt_err_type")
  asm.sar_ri8("rcx", 1)
  asm.mov_rm("r8", "rsi", 8)
  asm.test_rr("rcx", "rcx")
  asm.jcc("ns", "si_p")
  asm.add_rr("rcx", "r8")
  asm.label("si_p")
  asm.cmp_ri32("rcx", 0)
  asm.jcc("l", "rt_err_idx")
  asm.cmp_rr("rcx", "r8")
  asm.jcc("ge", "rt_err_idx")
  asm.mov_rm("rdx", "rsi", 24)
  asm.lea_mx("rdx", "rdx", "rcx", 8, 0)
  asm.mov_mr("rdx", "rax", 0)
  asm.ret()
  # rt_leq: two distinct Lists in rax, rcx -> tagged Bool (jumped to from rt_eq)
  asm.label("rt_leq")
  asm.mov_rm("rdx", "rax", 8)
  asm.mov_rm("rsi", "rcx", 8)
  asm.cmp_rr("rdx", "rsi")
  asm.jcc("ne", "eq_no")
  asm.push_r("rax")
  asm.push_r("rcx")
  asm.push_r("rdx")
  asm.mov_ri32("rdx", 0)
  asm.push_r("rdx")
  asm.label("lq_l")
  asm.mov_rm("rdx", "rsp", 0)
  asm.mov_rm("r8", "rsp", 8)
  asm.cmp_rr("rdx", "r8")
  asm.jcc("e", "lq_y")
  asm.mov_rm("rax", "rsp", 24)
  asm.mov_rm("rax", "rax", 24)
  asm.mov_rmx("rax", "rax", "rdx", 8, 0)
  asm.mov_rm("rcx", "rsp", 16)
  asm.mov_rm("rcx", "rcx", 24)
  asm.mov_rmx("rcx", "rcx", "rdx", 8, 0)
  asm.call("rt_eq")
  asm.cmp_ri32("rax", 10)
  asm.jcc("ne", "lq_n")
  asm.mov_rm("rdx", "rsp", 0)
  asm.add_ri32("rdx", 1)
  asm.mov_mr("rsp", "rdx", 0)
  asm.jmp("lq_l")
  asm.label("lq_y")
  asm.add_ri32("rsp", 32)
  asm.jmp("eq_yes")
  asm.label("lq_n")
  asm.add_ri32("rsp", 32)
  asm.jmp("eq_no")

def pad8():
  while asm.pos() % 8 != 0:
    asm.b1(0)

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
  asm.lea_rip("rax", "heap_base")
  asm.mov_mr_rip("hp", "rax")
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
  pad8()
  for so in SOBJ:
    asm.label(so[0])
    asm.bn(le64(1))
    asm.bn(le64(len(so[1])))
    for ch in so[1]:
      asm.b1(ascii_byte(ch, so[2]))
    pad8()
  asm.label("hp")
  asm.bn([0, 0, 0, 0, 0, 0, 0, 0])
  for k in keys(ST["globals"]):
    asm.label("g_" + k)
    asm.bn([0, 0, 0, 0, 0, 0, 0, 0])
  pad8()
  asm.label("heap_base")

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
  h = h + le64(n) + le64(268435456) + le64(4096)
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
