#!/usr/bin/env python3
"""holyshit v0.3 — HolyC subset -> WASM32. Easier than Python for small scripts.
- types optional (x = 5 infers I64), semicolons optional (newline ends stmt)
- Print like Python: space-separated, trailing newline. Print with no args = blank line.
- bare "str" prints, # comments, for i in A..B
- every value i64 (fixed 64-bit), strings via imported memory + print_str."""
import re, sys

# ---------- LEB128 ----------
def uleb(n):
    assert n >= 0
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n: return bytes(out)

def sleb(n):
    out = bytearray()
    more = True
    while more:
        b = n & 0x7F; n >>= 7
        sign = b & 0x40
        more = not ((n == 0 and not sign) or (n == -1 and sign))
        out.append(b | (0x80 if more else 0))
    return bytes(out)

def strvec(s: str) -> bytes:
    b = s.encode()
    return uleb(len(b)) + b

def vec_of(parts) -> bytes:
    out = uleb(len(parts))
    for p in parts: out += p
    return out

# ---------- Lexer ----------
TOK = re.compile(r"""
    (?P<nl>\n)
  | (?P<ws>[ \t\r]+)
  | (?P<comment>//[^\n]*|/\*.*?\*/|\#[^\n]*)
  | (?P<dotdot>\.\.)
  | (?P<hex>0[xX][0-9a-fA-F]+)
  | (?P<int>[0-9]+)
  | (?P<str>"(?:[^"\\\n]|\\.)*")
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|<=|>=|[(){},;=+\-*/%<>!])
""", re.X | re.S)

class LexError(Exception): pass

def lex(src):
    toks = []
    i = 0
    while i < len(src):
        m = TOK.match(src, i)
        if not m: raise LexError(f"bad char at {i}: {src[i:i+20]!r}")
        i = m.end()
        g = m.lastgroup
        if g in ("ws", "comment"): continue
        if g == "nl": toks.append(("nl", "\n")); continue
        toks.append((g, m.group()))
    toks.append(("eof", ""))
    return toks

# ---------- Parser ----------
class PErr(Exception): pass
TYPES = {"I64", "U0", "U64"}
BLOCK = {"if", "while", "for"}

class P:
    def __init__(self, toks):
        self.t = toks; self.i = 0
    def peek(self): return self.t[self.i]
    def next(self):
        x = self.t[self.i]; self.i += 1; return x
    def expect(self, k, v=None):
        x = self.next()
        if x[0] != k or (v is not None and x[1] != v):
            raise PErr(f"expected {k} {v}, got {x}")
        return x
    def at(self, k, v=None):
        x = self.peek()
        return x[0] == k and (v is None or x[1] == v)

def eat_ends(p):
    while p.at("nl") or p.at("op", ";"): p.next()

def at_end(p):
    return p.at("nl") or p.at("op", ";") or p.at("op", "}") or p.at("eof")

def need_end(p):
    if p.at("nl") or p.at("op", ";"):
        eat_ends(p); return
    if p.at("op", "}") or p.at("eof"): return
    raise PErr(f"end of statement expected, got {p.peek()}")

def is_funcdef(p):
    return (p.i + 2 < len(p.t) and p.t[p.i][0] == "id" and p.t[p.i][1] in TYPES
            and p.t[p.i+1][0] == "id" and p.t[p.i+2] == ("op", "("))

def parse_program(src):
    p = P(lex(src))
    funcs, top = [], []
    eat_ends(p)
    while not p.at("eof"):
        if p.at("op", "}"): raise PErr("stray }")
        if is_funcdef(p):
            funcs.append(parse_func(p))
            eat_ends(p)
        else:
            s = parse_stmt(p)
            top.append(s)
            if s[0] in BLOCK: eat_ends(p)
            else: need_end(p)
        eat_ends(p)
    return funcs, top

def parse_func(p):
    rtype = p.next()[1]
    name = p.expect("id")[1]
    p.expect("op", "(")
    eat_ends(p)
    params = []
    if not p.at("op", ")"):
        while True:
            t = p.next()
            if not (t[0] == "id" and t[1] in TYPES): raise PErr(f"param type expected, got {t}")
            params.append(p.expect("id")[1])
            eat_ends(p)
            if p.at("op", ","): p.next(); eat_ends(p); continue
            break
    p.expect("op", ")")
    eat_ends(p)
    p.expect("op", "{")
    body = parse_block_rest(p)
    return {"name": name, "rtype": rtype, "params": params, "body": body}

def parse_block_rest(p):
    """after consuming '{', parse until '}'."""
    body = []
    eat_ends(p)
    while not p.at("op", "}"):
        if p.at("eof"): raise PErr("missing }")
        s = parse_stmt(p)
        body.append(s)
        if s[0] in BLOCK: eat_ends(p)
        else: need_end(p)
        eat_ends(p)
    p.expect("op", "}")
    return body

def parse_stmt(p):
    if p.peek()[0] == "id" and p.peek()[1] in TYPES and p.i + 1 < len(p.t) and p.t[p.i+1][0] == "id":
        p.next()
        name = p.expect("id")[1]
        init = None
        if p.at("op", "="): p.next(); eat_ends(p); init = parse_expr(p)
        return ("decl", name, init)
    if p.peek() == ("id", "if"): return parse_if(p)
    if p.peek() == ("id", "while"): return parse_while(p)
    if p.peek() == ("id", "for"): return parse_for(p)
    if p.peek() == ("id", "return"):
        p.next()
        e = None
        if not at_end(p): e = parse_expr(p)
        return ("return", e)
    if p.peek() == ("id", "Print"): return parse_print(p)
    if p.peek()[0] == "str":
        return ("print", [("str", p.next()[1])])
    if p.peek()[0] == "id" and p.i + 1 < len(p.t) and p.t[p.i+1] == ("op", "="):
        name = p.next()[1]
        p.next()
        eat_ends(p)
        return ("set", name, parse_expr(p))
    return ("expr", parse_expr(p))

def parse_print(p):
    p.next()  # Print
    if p.at("op", "("):
        p.next(); eat_ends(p)
        args = []
        if not p.at("op", ")"):
            while True:
                eat_ends(p)
                args.append(("str", p.next()[1]) if p.at("str") else parse_expr(p))
                eat_ends(p)
                if p.at("op", ","): p.next(); continue
                break
        p.expect("op", ")")
        return ("print", args)
    args = []
    if at_end(p): return ("print", args)
    while True:
        args.append(("str", p.next()[1]) if p.at("str") else parse_expr(p))
        if p.at("op", ","): p.next(); continue
        break
    return ("print", args)

def parse_if(p):
    p.next()
    p.expect("op", "("); eat_ends(p)
    c = parse_expr(p); eat_ends(p)
    p.expect("op", ")"); eat_ends(p)
    p.expect("op", "{")
    t = parse_block_rest(p)
    eat_ends(p)
    e = []
    if p.peek() == ("id", "else"):
        p.next(); eat_ends(p)
        p.expect("op", "{")
        e = parse_block_rest(p)
    return ("if", c, t, e)

def parse_while(p):
    p.next()
    p.expect("op", "("); eat_ends(p)
    c = parse_expr(p); eat_ends(p)
    p.expect("op", ")"); eat_ends(p)
    p.expect("op", "{")
    return ("while", c, parse_block_rest(p))

def parse_for(p):
    p.next()
    paren = False
    if p.at("op", "("): paren = True; p.next(); eat_ends(p)
    var = p.expect("id")[1]
    if p.peek() != ("id", "in"): raise PErr(f"expected 'in' in for, got {p.peek()}")
    p.next()
    start = parse_expr(p)
    p.expect("dotdot", "..")
    end = parse_expr(p)
    if paren: eat_ends(p); p.expect("op", ")")
    eat_ends(p)
    p.expect("op", "{")
    return ("for", var, start, end, parse_block_rest(p))

def parse_expr(p): return parse_eq(p)
def parse_eq(p):
    l = parse_rel(p)
    while p.peek()[1] in ("==", "!=") and p.peek()[0] == "op":
        op = p.next()[1]; r = parse_rel(p); l = ("bin", op, l, r)
    return l
def parse_rel(p):
    l = parse_add(p)
    while p.peek()[1] in ("<", ">", "<=", ">=") and p.peek()[0] == "op":
        op = p.next()[1]; r = parse_add(p); l = ("bin", op, l, r)
    return l
def parse_add(p):
    l = parse_mul(p)
    while p.at("op", "+") or p.at("op", "-"):
        op = p.next()[1]; r = parse_mul(p); l = ("bin", op, l, r)
    return l
def parse_mul(p):
    l = parse_un(p)
    while p.at("op", "*") or p.at("op", "/") or p.at("op", "%"):
        op = p.next()[1]; r = parse_un(p); l = ("bin", op, l, r)
    return l
def parse_un(p):
    if p.at("op", "-"): p.next(); return ("neg", parse_un(p))
    return parse_prim(p)
def parse_prim(p):
    k, v = p.peek()
    if k == "hex": p.next(); return ("int", int(v, 16))
    if k == "int": p.next(); return ("int", int(v))
    if k == "id":
        p.next()
        if p.at("op", "("):
            p.next(); eat_ends(p)
            args = []
            if not p.at("op", ")"):
                while True:
                    eat_ends(p)
                    args.append(parse_expr(p))
                    eat_ends(p)
                    if p.at("op", ","): p.next(); continue
                    break
            p.expect("op", ")")
            return ("call", v, args)
        return ("var", v)
    if k == "op" and v == "(":
        p.next(); eat_ends(p); e = parse_expr(p); eat_ends(p); p.expect("op", ")"); return e
    raise PErr(f"expr expected, got {(k, v)}")

# ---------- Codegen -> WASM ----------
I64, I32 = 0x7E, 0x7F
OP = {
    "local.get": 0x20, "local.set": 0x21, "call": 0x10, "drop": 0x1A,
    "return": 0x0F, "if": 0x04, "else": 0x05, "end": 0x0B,
    "block": 0x02, "loop": 0x03, "br": 0x0C, "br_if": 0x0D,
    "i64.const": 0x42, "i32.const": 0x41,
    "i64.add": 0x7C, "i64.sub": 0x7D, "i64.mul": 0x7E,
    "i64.div_s": 0x7F, "i64.rem_s": 0x80,
    "i64.eq": 0x51, "i64.ne": 0x52, "i64.lt_s": 0x53, "i64.gt_s": 0x55,
    "i64.le_s": 0x57, "i64.ge_s": 0x59,
    "i64.eqz": 0x50, "i64.extend_i32_u": 0xAD,
}
CMP = {"==": OP["i64.eq"], "!=": OP["i64.ne"], "<": OP["i64.lt_s"],
       ">": OP["i64.gt_s"], "<=": OP["i64.le_s"], ">=": OP["i64.ge_s"]}
ESC = {"n": b"\n", "t": b"\t", "r": b"\r", '"': b'"', "\\": b"\\", "0": b"\x00"}

def unesc(lit):
    s = lit[1:-1]
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out += ESC.get(s[i+1], ("\\" + s[i+1]).encode())
            i += 2
        else:
            out += s[i].encode("utf-8"); i += 1
    return bytes(out)

def collect_vars(stmts):
    out = []
    def walk(s):
        if s[0] in ("decl", "set"):
            if s[1] not in out: out.append(s[1])
        elif s[0] == "for":
            if s[1] not in out: out.append(s[1])
            for x in s[4]: walk(x)
        elif s[0] == "if":
            for x in s[2]: walk(x)
            for x in s[3]: walk(x)
        elif s[0] == "while":
            for x in s[2]: walk(x)
    for s in stmts: walk(s)
    return out

def collect_strs(funcs, top):
    table, blob = {'" "': (0, 1)}, bytearray(b" ")
    def walk(s):
        nonlocal blob
        if s[0] == "print":
            for a in s[1]:
                if isinstance(a, tuple) and a[0] == "str" and a[1] not in table:
                    b = unesc(a[1])
                    table[a[1]] = (len(blob), len(b))
                    blob += b
        elif s[0] == "if":
            for x in s[2]: walk(x)
            for x in s[3]: walk(x)
        elif s[0] == "while":
            for x in s[2]: walk(x)
        elif s[0] == "for":
            for x in s[4]: walk(x)
    for f in funcs:
        for s in f["body"]: walk(s)
    for s in top: walk(s)
    assert len(blob) < 60000, "strings too big for 1 page"
    return table, bytes(blob)

class Gen:
    def __init__(self, funcs, top):
        self.fidx = {f["name"]: 3 + i for i, f in enumerate(funcs)}
        self.arity = {f["name"]: len(f["params"]) for f in funcs}
        self.strs, self.blob = collect_strs(funcs, top)

    def emit_expr(self, e, lmap, out):
        k = e[0]
        if k == "int":
            v = e[1] & 0xFFFFFFFFFFFFFFFF
            if v >= 0x8000000000000000: v -= 0x10000000000000000
            out.append(OP["i64.const"]); out += sleb(v)
        elif k == "var":
            if e[1] not in lmap: raise PErr(f"unknown var {e[1]}")
            out.append(OP["local.get"]); out += uleb(lmap[e[1]])
        elif k == "neg":
            out.append(OP["i64.const"]); out += sleb(0)
            self.emit_expr(e[1], lmap, out)
            out.append(OP["i64.sub"])
        elif k == "bin":
            _, op, l, r = e
            self.emit_expr(l, lmap, out); self.emit_expr(r, lmap, out)
            if op == "+": out.append(OP["i64.add"])
            elif op == "-": out.append(OP["i64.sub"])
            elif op == "*": out.append(OP["i64.mul"])
            elif op == "/": out.append(OP["i64.div_s"])
            elif op == "%": out.append(OP["i64.rem_s"])
            elif op in CMP:
                out.append(CMP[op]); out.append(OP["i64.extend_i32_u"])
            else: raise PErr(f"bad op {op}")
        elif k == "call":
            _, name, args = e
            if name not in self.fidx: raise PErr(f"unknown func {name}")
            if len(args) != self.arity[name]:
                raise PErr(f"{name} wants {self.arity[name]} args, got {len(args)}")
            for a in args: self.emit_expr(a, lmap, out)
            out.append(OP["call"]); out += uleb(self.fidx[name])
        else: raise PErr(f"bad expr {e}")

    def emit_cond_i32(self, cond, lmap, out):
        self.emit_expr(cond, lmap, out)
        out.append(OP["i64.const"]); out += sleb(0)
        out.append(OP["i64.ne"])

    def emit_stmt(self, s, lmap, out):
        if s[0] == "decl":
            _, name, init = s
            if init is None:
                out.append(OP["i64.const"]); out += sleb(0)
            else: self.emit_expr(init, lmap, out)
            out.append(OP["local.set"]); out += uleb(lmap[name])
        elif s[0] == "set":
            _, name, rhs = s
            if name not in lmap: raise PErr(f"compiler bug: no local {name}")
            self.emit_expr(rhs, lmap, out)
            out.append(OP["local.set"]); out += uleb(lmap[name])
        elif s[0] == "return":
            if s[1] is None:
                out.append(OP["i64.const"]); out += sleb(0)
            else: self.emit_expr(s[1], lmap, out)
            out.append(OP["return"])
        elif s[0] == "expr":
            e = s[1]
            if e[0] == "var" and e[1] in self.fidx and self.arity[e[1]] == 0 and e[1] not in lmap:
                out.append(OP["call"]); out += uleb(self.fidx[e[1]])
                out.append(OP["drop"])
            else:
                self.emit_expr(e, lmap, out)
                out.append(OP["drop"])
        elif s[0] == "print":
            # Python-like: space-separated args + trailing newline (import 2 = print_nl)
            sptr, slen = self.strs['" "']
            for i, a in enumerate(s[1]):
                if i > 0:
                    out.append(OP["i32.const"]); out += sleb(sptr)
                    out.append(OP["i32.const"]); out += sleb(slen)
                    out.append(OP["call"]); out += uleb(1)
                if isinstance(a, tuple) and a[0] == "str":
                    ptr, ln = self.strs[a[1]]
                    out.append(OP["i32.const"]); out += sleb(ptr)
                    out.append(OP["i32.const"]); out += sleb(ln)
                    out.append(OP["call"]); out += uleb(1)
                else:
                    self.emit_expr(a, lmap, out)
                    out.append(OP["call"]); out += uleb(0)
            out.append(OP["call"]); out += uleb(2)
        elif s[0] == "if":
            _, c, t, e = s
            self.emit_cond_i32(c, lmap, out)
            out.append(OP["if"]); out.append(0x40)
            for x in t: self.emit_stmt(x, lmap, out)
            if e:
                out.append(OP["else"])
                for x in e: self.emit_stmt(x, lmap, out)
            out.append(OP["end"])
        elif s[0] == "while":
            _, c, b = s
            out.append(OP["block"]); out.append(0x40)
            out.append(OP["loop"]); out.append(0x40)
            self.emit_expr(c, lmap, out)
            out.append(OP["i64.const"]); out += sleb(0)
            out.append(OP["i64.eq"])
            out.append(OP["br_if"]); out += uleb(1)
            for x in b: self.emit_stmt(x, lmap, out)
            out.append(OP["br"]); out += uleb(0)
            out.append(OP["end"]); out.append(OP["end"])
        elif s[0] == "for":
            _, var, start, end, b = s
            self.emit_expr(start, lmap, out)
            out.append(OP["local.set"]); out += uleb(lmap[var])
            out.append(OP["block"]); out.append(0x40)
            out.append(OP["loop"]); out.append(0x40)
            self.emit_expr(("bin", "<", ("var", var), end), lmap, out)
            out.append(OP["i64.const"]); out += sleb(0)
            out.append(OP["i64.eq"])
            out.append(OP["br_if"]); out += uleb(1)
            for x in b: self.emit_stmt(x, lmap, out)
            out.append(OP["local.get"]); out += uleb(lmap[var])
            out.append(OP["i64.const"]); out += sleb(1)
            out.append(OP["i64.add"])
            out.append(OP["local.set"]); out += uleb(lmap[var])
            out.append(OP["br"]); out += uleb(0)
            out.append(OP["end"]); out.append(OP["end"])
        else: raise PErr(f"bad stmt {s[0]}")

    def func_body(self, params, stmts):
        lmap = {n: i for i, n in enumerate(params)}
        for v in collect_vars(stmts):
            if v not in lmap: lmap[v] = len(lmap)
        n_extra = len(lmap) - len(params)
        out = bytearray()
        for s in stmts: self.emit_stmt(s, lmap, out)
        out.append(OP["i64.const"]); out += sleb(0)
        out.append(OP["end"])
        loc = uleb(1) + uleb(n_extra) + bytes([I64]) if n_extra else uleb(0)
        return loc + bytes(out)

    def start_body(self, stmts):
        lmap = {}
        for v in collect_vars(stmts):
            if v not in lmap: lmap[v] = len(lmap)
        out = bytearray()
        for s in stmts: self.emit_stmt(s, lmap, out)
        out.append(OP["end"])
        loc = uleb(1) + uleb(len(lmap)) + bytes([I64]) if lmap else uleb(0)
        return loc + bytes(out)

def build_wasm(funcs, top):
    g = Gen(funcs, top)
    max_arity = max([0] + [len(f["params"]) for f in funcs])
    types = [
        bytes([0x60]) + uleb(1) + bytes([I64]) + uleb(0),        # 0: print_i64
        bytes([0x60]) + uleb(2) + bytes([I32, I32]) + uleb(0),   # 1: print_str
        bytes([0x60]) + uleb(0) + uleb(0),                       # 2: print_nl
        bytes([0x60]) + uleb(0) + uleb(0),                       # 3: start
    ]
    t_arity = {}
    for n in range(max_arity + 1):
        t_arity[n] = len(types)
        types.append(bytes([0x60]) + uleb(n) + bytes([I64] * n) + uleb(1) + bytes([I64]))
    type_sec = bytes([1]) + uleb(len(vec_of(types))) + vec_of(types)

    imp = vec_of([
        strvec("env") + strvec("print_i64") + bytes([0x00]) + uleb(0),
        strvec("env") + strvec("print_str") + bytes([0x00]) + uleb(1),
        strvec("env") + strvec("print_nl") + bytes([0x00]) + uleb(2),
        strvec("env") + strvec("memory") + bytes([0x02, 0x00, 0x01]),
    ])
    imp_sec = bytes([2]) + uleb(len(imp)) + imp

    ftypes = [t_arity[len(f["params"])] for f in funcs]
    has_start = len(top) > 0
    if has_start: ftypes.append(3)
    fvec = vec_of([uleb(t) for t in ftypes])
    func_sec = bytes([3]) + uleb(len(fvec)) + fvec

    exp = vec_of([strvec(f["name"]) + bytes([0x00]) + uleb(g.fidx[f["name"]]) for f in funcs])
    exp_sec = bytes([7]) + uleb(len(exp)) + exp

    codes = [g.func_body(f["params"], f["body"]) for f in funcs]
    if has_start: codes.append(g.start_body(top))
    cvec = vec_of([uleb(len(c)) + c for c in codes])
    code_sec = bytes([10]) + uleb(len(cvec)) + cvec

    mod = b"\x00asm\x01\x00\x00\x00" + type_sec + imp_sec + func_sec + exp_sec
    if has_start:
        sb = uleb(len(funcs) + 3)
        mod += bytes([8]) + uleb(len(sb)) + sb
    mod += code_sec
    if g.blob:
        seg = uleb(0) + bytes([0x41, 0x00, 0x0B]) + uleb(len(g.blob)) + g.blob
        dvec = vec_of([seg])
        mod += bytes([11]) + uleb(len(dvec)) + dvec
    return mod

def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} in.HC out.wasm  (out=- writes bytes to stdout)", file=sys.stderr); sys.exit(2)
    src = open(sys.argv[1], encoding="utf-8").read()
    try:
        funcs, top = parse_program(src)
        data = build_wasm(funcs, top)
        if sys.argv[2] == "-":
            sys.stdout.buffer.write(data)
        else:
            open(sys.argv[2], "wb").write(data)
            print(f"ok: {len(funcs)} funcs, {len(top)} top-stmts -> {sys.argv[2]}")
    except (PErr, LexError, AssertionError) as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()
