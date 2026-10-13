#!/usr/bin/env python3
"""holyshit v1 interpreter (เฟส 2) — tree-walk, dynamic, indent syntax.
usage: python3 interp.py prog.hs
notes: values are plain Python objects (int/float/str/bool/None/list/dict).
  Native backend (เฟส 3) will wrap ints to 64-bit; here Python ints are unbounded.
"""
import re
import sys

sys.setrecursionlimit(20000)

# ---------- errors ----------
class HSErr(Exception):
    def __init__(self, msg, line=None):
        self.msg = msg
        self.line = line

    def __str__(self):
        return f"error: {self.msg}" + (f" at line {self.line}" if self.line else "")


class ReturnExc(Exception):
    def __init__(self, value):
        self.value = value


_EXC_STACK = []  # (msg, line) of exceptions currently handled (for bare raise)


class BreakExc(Exception):
    pass


class ContinueExc(Exception):
    pass


# ---------- values ----------
class HSFunc:
    def __init__(self, name, params, body, closure, line):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
        self.line = line


class HSBuiltin:
    def __init__(self, name, fn):
        self.name = name
        self.fn = fn


import ctypes as _ctypes
import ctypes.util as _ctypes_util

_FFI_C_CACHE = {}  # c-abspath -> compiled .so path
_FFI_CT = {"I64": _ctypes.c_int64, "U64": _ctypes.c_uint64,
           "F64": _ctypes.c_double}


def ffi_load(lib, basedir, line):
    """Resolve an extern `from` clause to a CDLL."""
    if lib is None:
        return _ctypes.CDLL(None)
    if lib.endswith(".c"):
        p = lib if _os.path.isabs(lib) else _os.path.abspath(_os.path.join(basedir, lib))
        if not _os.path.isfile(p):
            raise HSErr(f"cannot find ffi source '{lib}'", line)
        so = _FFI_C_CACHE.get(p)
        if so is None:
            import subprocess
            import tempfile
            d = tempfile.mkdtemp(prefix="hsffi_")
            so = _os.path.join(d, "ffi.so")
            r = subprocess.run(["gcc", "-shared", "-fPIC", "-O2", p, "-o", so],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise HSErr(f"ffi compile failed for '{lib}': {r.stderr.strip()}", line)
            _FFI_C_CACHE[p] = so
        return _ctypes.CDLL(so)
    if "/" in lib or lib.endswith((".so", ".o", ".a")):
        p = lib if _os.path.isabs(lib) else _os.path.abspath(_os.path.join(basedir, lib))
        if not _os.path.isfile(p):
            raise HSErr(f"cannot find ffi library '{lib}'", line)
        try:
            return _ctypes.CDLL(p)
        except OSError:
            raise HSErr(f"cannot load ffi library '{lib}'", line)
    found = _ctypes_util.find_library(lib)
    try:
        return _ctypes.CDLL(found or ("lib" + lib + ".so"))
    except OSError:
        raise HSErr(f"cannot load ffi library '{lib}'", line)


class HSExtern:
    """A C function imported via extern. Calls go through ctypes."""

    def __init__(self, name, rtype, params, cdll, line):
        self.name = name
        self.rtype = rtype
        self.params = params  # [(pname, ftype)]
        try:
            fn = getattr(cdll, name)
        except (AttributeError, ValueError):
            raise HSErr(f"unknown ffi symbol '{name}'", line)
        fn.restype = None if rtype == "U0" else (
            _ctypes.c_char_p if rtype == "Str" else (
                _ctypes.c_void_p if rtype == "Ptr" else _FFI_CT[rtype]))
        fn.argtypes = [(_ctypes.c_char_p if ft == "Str" else (
            _ctypes.c_void_p if ft == "Ptr" else _FFI_CT[ft])) for _, ft in params]
        self.func = fn

    def call(self, args, ln):
        if len(args) != len(self.params):
            raise HSErr(f"ffi '{self.name}' wants {len(self.params)} args, got {len(args)}", ln)
        cargs = []
        for i, ((pn, ft), a) in enumerate(zip(self.params, args)):
            cargs.append(self._conv(a, ft, i, ln))
        import sys as _sys
        _sys.stdout.flush()  # keep Python print and C stdio in program order
        try:
            r = self.func(*cargs)
        except (OverflowError, _ctypes.ArgumentError, OSError) as e:
            raise HSErr(f"ffi '{self.name}' failed: {e}", ln)
        _ctypes.CDLL(None).fflush(None)
        return self._back(r)

    def _conv(self, a, ft, i, ln):
        bad = HSErr(f"ffi '{self.name}' arg {i + 1} wants {ft}, got {tname(a)}", ln)
        if ft == "I64":
            if not isinstance(a, int) or isinstance(a, bool):
                raise bad
            return a
        if ft == "U64":
            if not isinstance(a, int) or isinstance(a, bool) or a < 0:
                raise bad
            return a
        if ft == "F64":
            if isinstance(a, bool) or not isinstance(a, (int, float)):
                raise bad
            return float(a)
        if ft == "Str":
            if not isinstance(a, str):
                raise bad
            return a.encode()
        if ft == "Ptr":
            if not isinstance(a, int) or isinstance(a, bool):
                raise bad
            return a
        raise bad

    def _back(self, r):
        if self.rtype == "U0":
            return None
        if self.rtype == "F64":
            return float(r)
        if self.rtype == "Str":
            return None if r is None else r.decode()
        if self.rtype == "Ptr":
            return 0 if r is None else r
        return int(r)


class HSFile:
    def __init__(self, obj, path, mode):
        self.obj = obj
        self.path = path
        self.mode = mode
        self.closed = False


class HSMod:
    def __init__(self, name, env):
        self.name = name
        self.env = env


class UnsafeVal:
    """static value inside unsafe: utype in I64/U64/Ptr, val is Python int."""
    __slots__ = ("utype", "val")

    def __init__(self, utype, val):
        self.utype = utype
        self.val = val


# ---------- unsafe simulated memory (interpreter only) ----------
# Flat byte-addressable memory. Pointers are integer addresses. Addr 0 = NULL.
US_MEM = bytearray(1 << 20)
US_TOP = 8
MASK64 = (1 << 64) - 1


def wrap_i64(v):
    v &= MASK64
    return v - (1 << 64) if v >= (1 << 63) else v


def wrap_u64(v):
    return v & MASK64


def us_alloc(n, line):
    global US_TOP
    if n < 0:
        raise HSErr(f"alloc of negative size {n}", line)
    n = (n + 7) & ~7
    if US_TOP + n > len(US_MEM):
        raise HSErr("unsafe: out of memory (1MB sim)", line)
    addr = US_TOP
    for i in range(addr, addr + n):
        US_MEM[i] = 0
    US_TOP += n
    return addr


def us_check(addr, size, line):
    if addr == 0:
        raise HSErr("null pointer dereference", line)
    if addr < 0 or addr + size > len(US_MEM):
        raise HSErr("unsafe: address out of bounds", line)


def us_load(addr, size, line):
    us_check(addr, size, line)
    return int.from_bytes(US_MEM[addr:addr + size], "little")


def us_store(addr, size, v, line):
    us_check(addr, size, line)
    US_MEM[addr:addr + size] = (v & ((1 << (size * 8)) - 1)).to_bytes(size, "little")


def is_ptr(t):
    return t == "Ptr" or t.startswith("Ptr:")


def ptr_struct(t):
    return t[4:] if t.startswith("Ptr:") else None


HS_STRUCTS = {}  # name -> {"fields": {fname: (ftype, offset, count)}, "size": bytes}


def reset_parse_state():
    """Call once per top-level build: struct layouts live for one program only."""
    HS_STRUCTS.clear()


def struct_field(sname, fname, line):
    L = HS_STRUCTS.get(sname)
    if L is None:
        raise HSErr(f"unknown struct '{sname}'", line)
    f = L["fields"].get(fname)
    if f is None:
        raise HSErr(f"struct '{sname}' has no field '{fname}'", line)
    return f


def struct_size(sname, line):
    L = HS_STRUCTS.get(sname)
    if L is None:
        raise HSErr(f"unknown struct '{sname}'", line)
    return L["size"]


def box(utype, v, line):
    """static -> dynamic."""
    if utype in ("I64", "LIT"):
        return v
    if utype == "U64":
        if v > (1 << 63) - 1:
            raise HSErr(f"U64 value {v} too large for Int", line)
        return v
    if is_ptr(utype):
        if v >= (1 << 63):
            raise HSErr("address too large for Int", line)
        return v
    raise HSErr(f"bad static type {utype}", line)


def unbox(v, target, line):
    """dynamic -> static target (I64/U64/Ptr family)."""
    if isinstance(v, bool):
        v = int(v)
    if target == "I64":
        if isinstance(v, int):
            return wrap_i64(v)
        raise HSErr(f"cannot use {tname(v)} as I64", line)
    if target == "U64" or is_ptr(target):
        if isinstance(v, int):
            if v < 0:
                raise HSErr(f"negative value {v} as {target}", line)
            return v & MASK64
        raise HSErr(f"cannot use {tname(v)} as {target}", line)
    raise HSErr(f"bad static type {target}", line)


def coerce(st, sv, target, line):
    """static (st, sv) -> target static type. LIT adapts; dynamic already I64."""
    if st == "LIT":
        return unbox(sv, target, line)
    if st == target:
        return sv
    if is_ptr(st) and is_ptr(target):
        return sv & MASK64
    if target == "I64" and st == "U64":
        return wrap_i64(sv)
    if target == "U64" and st == "I64":
        if sv < 0:
            raise HSErr(f"negative value {sv} as U64", line)
        return sv & MASK64
    raise HSErr(f"cannot convert {st} to {target}", line)


def tname(v):
    if isinstance(v, bool):
        return "Bool"
    if isinstance(v, int):
        return "Int"
    if isinstance(v, float):
        return "Float"
    if isinstance(v, str):
        return "Str"
    if v is None:
        return "Null"
    if isinstance(v, list):
        return "List"
    if isinstance(v, dict):
        return "Dict"
    if isinstance(v, HSFunc):
        return "Func"
    if isinstance(v, HSFile):
        return "File"
    if isinstance(v, HSSock):
        return "Sock"
    if isinstance(v, HSBuiltin):
        return "Builtin"
    if isinstance(v, HSExtern):
        return "Extern"
    if isinstance(v, HSMod):
        return "Module"
    if isinstance(v, UnsafeVal):
        return f"Unsafe({v.utype})"
    return "?"


def disp(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "[" + ", ".join(disp(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(disp(k) + ": " + disp(x) for k, x in v.items()) + "}"
    if isinstance(v, HSFunc):
        return f"<func {v.name}>"
    if isinstance(v, HSFile):
        return f"<file {v.path}>"
    if isinstance(v, HSSock):
        return "<sock>"
    if isinstance(v, HSBuiltin):
        return f"<builtin {v.name}>"
    if isinstance(v, HSExtern):
        return f"<extern {v.name}>"
    if isinstance(v, HSMod):
        return f"<module {v.name}>"
    return str(v)


# ---------- lexer ----------
KEYWORDS = {"def", "if", "elif", "else", "while", "for", "in", "return",
            "break", "continue", "global", "and", "or", "not",
            "true", "false", "null", "pass", "import", "try", "except", "as",
            "extern", "raise", "lambda"}
RESERVED = {"module"}
UTYPES = {"I64", "U64", "Ptr"}
FFTYPE = {"U0", "I64", "U64", "F64", "Str", "Ptr"}
UNSAFE_BUILTINS = {"alloc", "load8", "load32", "load64", "store8", "store32",
                   "store64", "as_ptr", "as_int", "asm"}
UNSAFE_SIZES = {"load8": 1, "load32": 4, "load64": 8,
                "store8": 1, "store32": 4, "store64": 8}


class Tok:
    # raw keeps the source spelling of a literal (0xAB stays 0xAB in fmt)
    __slots__ = ("k", "v", "line", "raw")

    def __init__(self, k, v, line, raw=None):
        self.k = k
        self.v = v
        self.line = line
        self.raw = raw

    def __repr__(self):
        return f"Tok({self.k},{self.v!r},{self.line})"


SC = re.compile(r"""
    (?P<fstr>f"(?:[^"\\\n]|\\.)*")
  | (?P<str>"(?:[^"\\\n]|\\.)*")
  | (?P<float>[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?
              |\.[0-9]+([eE][+-]?[0-9]+)?
              |[0-9]+[eE][+-]?[0-9]+)
  | (?P<hex>0[xX][0-9a-fA-F]+)
  | (?P<int>[0-9]+)
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><<|>>|==|!=|<=|>=|[+\-*/%<>=&|^~(){}\[\],:.])
  | (?P<ws>[ \t]+)
""", re.X)

ESC = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}


def unesc(lit, line):
    s = lit[1:-1]
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append(ESC.get(nxt, nxt))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def lex_line(content, line):
    toks = []
    j = 0
    while j < len(content):
        if content[j:j + 2] == "//":
            break
        if content[j] == "#":
            break
        m = SC.match(content, j)
        if not m:
            raise HSErr(f"bad character {content[j]!r}", line)
        j = m.end()
        g = m.lastgroup
        v = m.group()
        if g == "ws":
            continue
        if g == "str":
            toks.append(Tok("STR", unesc(v, line), line))
        elif g == "fstr":
            toks.append(Tok("FSTR", v[2:-1], line))
        elif g == "float":
            # raw keeps the spelling (1.5e3 stays 1.5e3 in `hs fmt`)
            toks.append(Tok("NUM", float(v), line, raw=v))
        elif g == "hex":
            toks.append(Tok("NUM", int(v, 16), line, raw=v))
        elif g == "int":
            toks.append(Tok("NUM", int(v), line))
        elif g == "id":
            if v in RESERVED:
                raise HSErr(f"'{v}' is reserved for future use", line)
            toks.append(Tok("ID", v, line))
        else:
            toks.append(Tok("OP", v, line))
    return toks


def lex(src):
    toks = []
    stack = [0]
    lines = src.split("\n")
    ln = 1
    for ln, raw in enumerate(lines, 1):
        line = raw.rstrip("\r")
        if not line.strip() or line.strip().startswith("#") or line.strip().startswith("//"):
            continue
        i = 0
        while i < len(line) and line[i] == " ":
            i += 1
        if i < len(line) and line[i] == "\t":
            raise HSErr("tabs not allowed, use spaces", ln)
        indent = i
        content = line[i:]
        if indent > stack[-1]:
            stack.append(indent)
            toks.append(Tok("INDENT", "", ln))
        elif indent < stack[-1]:
            while stack and indent < stack[-1]:
                stack.pop()
                toks.append(Tok("DEDENT", "", ln))
            if indent != stack[-1]:
                raise HSErr("inconsistent indent", ln)
        toks.extend(lex_line(content, ln))
        toks.append(Tok("NEWLINE", "", ln))
    while len(stack) > 1:
        stack.pop()
        toks.append(Tok("DEDENT", "", ln))
    toks.append(Tok("EOF", "", ln))
    return toks


# ---------- parser ----------
class P:
    def __init__(self, toks):
        self.t = toks
        self.i = 0
        self.unsafe = 0
        self.hoist = []   # defs for lambdas seen in the statement being parsed
        self.nlam = 0
        self.mods = set()  # first segment of every `import` seen so far

    def peek(self):
        return self.t[self.i]

    def next(self):
        x = self.t[self.i]
        self.i += 1
        return x

    def at(self, k, v=None):
        x = self.peek()
        return x.k == k and (v is None or x.v == v)

    def expect(self, k, v=None):
        x = self.next()
        if x.k != k or (v is not None and x.v != v):
            raise HSErr(f"expected {v or k}, got {x.v!r}", x.line)
        return x

    def skip_nl(self):
        while self.at("NEWLINE"):
            self.next()


def N(t, line, **kw):
    kw.update({"t": t, "line": line})
    return kw


def parse_program(src):
    p = P(lex(src))
    body = parse_body(p, top=True)
    p.expect("EOF")
    return body


def parse_body(p, top=False):
    body = []
    p.skip_nl()
    while not p.at("EOF") and not p.at("DEDENT"):
        if p.at("INDENT"):
            t = p.next()
            raise HSErr("unexpected indent", t.line)
        # nested blocks inside unsafe: keep static statement parsing
        outer, p.hoist = p.hoist, []
        st = parse_ustmt(p) if p.unsafe > 0 else parse_stmt(p)
        body.extend(p.hoist)   # lambda defs go right before their statement
        p.hoist = outer
        body.append(st)
        p.skip_nl()
    if not top:
        if p.at("DEDENT"):
            p.next()
        else:
            raise HSErr("expected indented block", p.peek().line)
    return body


def parse_block(p, line):
    # after '...:' — must be NEWLINE INDENT body (DEDENT consumed by parse_body)
    if not p.at("NEWLINE"):
        raise HSErr("expected ':' then a new line", line)
    p.next()
    if not p.at("INDENT"):
        raise HSErr("expected indented block", p.peek().line)
    p.next()
    return parse_body(p)


def parse_stmt(p):
    t = p.peek()
    if t.k == "ID" and t.v == "def":
        return parse_def(p)
    if t.k == "ID" and t.v == "if":
        return parse_if(p)
    if t.k == "ID" and t.v == "while":
        p.next()
        c = parse_expr(p)
        p.expect("OP", ":")
        return N("while", t.line, cond=c, body=parse_block(p, t.line))
    if t.k == "ID" and t.v == "for":
        p.next()
        v = p.expect("ID")
        if v.v in ("true", "false", "null") or v.v in KEYWORDS:
            raise HSErr(f"bad loop variable '{v.v}'", v.line)
        it = p.expect("ID")
        if it.v != "in":
            raise HSErr(f"expected 'in', got {it.v!r}", it.line)
        e = parse_expr(p)
        p.expect("OP", ":")
        return N("for", t.line, var=v.v, iter=e, body=parse_block(p, t.line))
    if t.k == "ID" and t.v == "return":
        p.next()
        e = None
        if not p.at("NEWLINE") and not p.at("EOF") and not p.at("DEDENT"):
            e = parse_expr(p)
        return N("return", t.line, val=e)
    if t.k == "ID" and t.v == "raise":
        p.next()
        e = None
        if not p.at("NEWLINE") and not p.at("EOF") and not p.at("DEDENT"):
            e = parse_expr(p)
        return N("raise", t.line, val=e)
    if t.k == "ID" and t.v == "break":
        p.next()
        return N("break", t.line)
    if t.k == "ID" and t.v == "continue":
        p.next()
        return N("continue", t.line)
    if t.k == "ID" and t.v == "pass":
        p.next()
        return N("pass", t.line)
    if t.k == "ID" and t.v == "global":
        p.next()
        names = [p.expect("ID").v]
        while p.at("OP", ","):
            p.next()
            names.append(p.expect("ID").v)
        return N("global", t.line, names=names)
    if t.k == "ID" and t.v == "print":
        return parse_print(p)
    if t.k == "ID" and t.v == "unsafe":
        return parse_unsafe(p)
    if t.k == "ID" and t.v == "import":
        p.next()
        name = p.expect("ID")
        if name.v in KEYWORDS or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name.v):
            raise HSErr(f"bad module name '{name.v}'", name.line)
        full = name.v
        while p.peek().k == "OP" and p.peek().v == ".":
            p.next()
            part = p.expect("ID")
            if part.v in KEYWORDS or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part.v):
                raise HSErr(f"bad module name '{full}.{part.v}'", part.line)
            full = full + "." + part.v
        p.mods.add(full.split(".")[0])
        return N("import", t.line, name=full)
    if t.k == "ID" and t.v == "try":
        p.next()
        p.expect("OP", ":")
        body = parse_block(p, t.line)
        ename = None
        ebody = None
        fbody = None
        if p.peek().k == "ID" and p.peek().v == "except":
            p.next()
            if p.peek().k == "ID" and p.peek().v == "as":
                p.next()
                ename = p.expect("ID").v
            p.expect("OP", ":")
            ebody = parse_block(p, t.line)
        if p.peek().k == "ID" and p.peek().v == "finally":
            p.next()
            p.expect("OP", ":")
            fbody = parse_block(p, t.line)
        if ebody is None and fbody is None:
            raise HSErr("try without except or finally", p.peek().line)
        return N("try", t.line, body=body, ename=ename, ebody=ebody, fbody=fbody)
    if t.k == "ID" and t.v == "extern":
        return parse_extern(p)
    if t.k == "ID" and t.v in ("elif", "else", "except"):
        raise HSErr(f"stray '{t.v}'", t.line)
    # assignment or expression statement
    e = parse_expr(p)
    if e["t"] == "str" and not p.at("OP", "="):
        return N("print", t.line, args=[e])
    if p.at("OP", "="):
        p.next()
        rhs = parse_expr(p)
        if e["t"] == "var":
            return N("set", t.line, name=e["name"], val=rhs)
        if e["t"] == "index":
            return N("setindex", t.line, obj=e["obj"], idx=e["idx"], val=rhs)
        if e["t"] == "attr":
            return N("setattr", t.line, obj=e["obj"], name=e["name"], val=rhs)
        raise HSErr("cannot assign to this", t.line)
    return N("expr", t.line, val=e)


def parse_extern(p):
    # extern [from "lib|file.c|path.so"]: <NEWLINE> INDENT <FTYPE name(params)>...
    t = p.expect("ID")  # extern
    lib = None
    if p.peek().k == "ID" and p.peek().v == "from":
        p.next()
        lib = p.expect("STR").v
    p.expect("OP", ":")
    if not p.at("NEWLINE"):
        raise HSErr("expected ':' then a new line", t.line)
    p.next()
    if not p.at("INDENT"):
        raise HSErr("expected indented block", p.peek().line)
    p.next()
    decls = []
    p.skip_nl()
    while not p.at("EOF") and not p.at("DEDENT"):
        if p.at("INDENT"):
            u = p.next()
            raise HSErr("unexpected indent", u.line)
        rt = p.expect("ID")
        if rt.v not in FFTYPE:
            raise HSErr(f"bad ffi type '{rt.v}' (want one of U0 I64 U64 F64 Str Ptr)", rt.line)
        nm = p.expect("ID")
        if nm.v in KEYWORDS or nm.v in FFTYPE or nm.v in UTYPES:
            raise HSErr(f"bad extern name '{nm.v}'", nm.line)
        p.expect("OP", "(")
        params = []
        if not p.at("OP", ")"):
            while True:
                ft = p.expect("ID")
                if ft.v not in FFTYPE or ft.v == "U0":
                    raise HSErr(f"bad ffi param type '{ft.v}'", ft.line)
                pn = p.expect("ID")
                if pn.v in KEYWORDS:
                    raise HSErr(f"bad param name '{pn.v}'", pn.line)
                params.append((pn.v, ft.v))
                if p.at("OP", ","):
                    p.next()
                    continue
                break
        p.expect("OP", ")")
        decls.append({"name": nm.v, "rtype": rt.v, "params": params, "line": nm.line})
        p.skip_nl()
    if p.at("DEDENT"):
        p.next()
    else:
        raise HSErr("expected indented block", p.peek().line)
    if not decls:
        raise HSErr("extern block is empty", t.line)
    return N("extern", t.line, decls=decls, lib=lib)


def parse_def(p):
    t = p.expect("ID")  # def
    name = p.expect("ID").v
    p.expect("OP", "(")
    params = []
    if not p.at("OP", ")"):
        while True:
            a = p.expect("ID").v
            if a in params:
                raise HSErr(f"duplicate param '{a}'", t.line)
            params.append(a)
            if p.at("OP", ","):
                p.next()
                continue
            break
    p.expect("OP", ")")
    p.expect("OP", ":")
    return N("def", t.line, name=name, params=params, body=parse_block(p, t.line))


def parse_unsafe(p):
    t = p.expect("ID")  # unsafe
    if p.unsafe > 0:
        raise HSErr("unsafe inside unsafe", t.line)
    p.expect("OP", ":")
    if not p.at("NEWLINE"):
        raise HSErr("expected ':' then a new line", t.line)
    p.next()
    if not p.at("INDENT"):
        raise HSErr("expected indented block", p.peek().line)
    p.next()
    p.unsafe += 1
    body = []
    p.skip_nl()
    while not p.at("EOF") and not p.at("DEDENT"):
        if p.at("INDENT"):
            u = p.next()
            raise HSErr("unexpected indent", u.line)
        body.append(parse_ustmt(p))
        p.skip_nl()
    if p.at("DEDENT"):
        p.next()
    else:
        raise HSErr("expected indented block", p.peek().line)
    p.unsafe -= 1
    return N("unsafe", t.line, body=body)


def parse_struct(p):
    # struct Name: <NEWLINE> INDENT <FTYPE|Struct field[N]>... (unsafe only)
    t = p.expect("ID")  # struct
    nm = p.expect("ID")
    if nm.v in KEYWORDS or nm.v in UTYPES or nm.v in FFTYPE or nm.v in BUILTINS:
        raise HSErr(f"bad struct name '{nm.v}'", nm.line)
    p.expect("OP", ":")
    if not p.at("NEWLINE"):
        raise HSErr("expected ':' then a new line", t.line)
    p.next()
    if not p.at("INDENT"):
        raise HSErr("expected indented block", p.peek().line)
    p.next()
    fields = {}
    off = 0
    p.skip_nl()
    while not p.at("EOF") and not p.at("DEDENT"):
        if p.at("INDENT"):
            u = p.next()
            raise HSErr("unexpected indent", u.line)
        ft = p.expect("ID")
        if ft.v in ("I64", "U64", "Ptr"):
            ftype = ft.v
        elif ft.v in HS_STRUCTS or ft.v == nm.v:
            ftype = ft.v
        else:
            raise HSErr(f"bad field type '{ft.v}'", ft.line)
        if p.at("OP", "*"):
            # Struct pointer field: Next* next
            if ftype in ("I64", "U64", "Ptr"):
                raise HSErr(f"scalar type '{ft.v}' cannot use '*'", ft.line)
            p.next()
            ftype = "Ptr:" + ftype
        fn = p.expect("ID")
        if fn.v in KEYWORDS:
            raise HSErr(f"bad field name '{fn.v}'", fn.line)
        if fn.v in fields:
            raise HSErr(f"duplicate field '{fn.v}'", fn.line)
        count = 1
        if p.at("OP", "["):
            p.next()
            cn = p.expect("NUM")
            if not isinstance(cn.v, int) or isinstance(cn.v, bool) or cn.v <= 0:
                raise HSErr("array size must be a positive integer", cn.line)
            count = cn.v
            p.expect("OP", "]")
        fields[fn.v] = (ftype, off, count)
        off += 8 * count
        p.skip_nl()
    if p.at("DEDENT"):
        p.next()
    else:
        raise HSErr("expected indented block", p.peek().line)
    if not fields:
        raise HSErr("struct needs at least one field", t.line)
    if nm.v in HS_STRUCTS and HS_STRUCTS[nm.v] != {"fields": fields, "size": off}:
        raise HSErr(f"struct '{nm.v}' redefined with a different layout", nm.line)
    HS_STRUCTS[nm.v] = {"fields": fields, "size": off}
    return N("struct", t.line, name=nm.v)


def parse_ustmt(p):
    t = p.peek()
    # struct declaration: struct Name: ...
    if t.k == "ID" and t.v == "struct":
        return parse_struct(p)
    # typed declaration: I64 x = ... / U64 y / Ptr p / Name* q
    if t.k == "ID" and (t.v in UTYPES or t.v in HS_STRUCTS) \
            and p.i + 1 < len(p.t) and (
                p.t[p.i + 1].k == "ID" or t.v in HS_STRUCTS):
        typ = p.next().v
        if typ in HS_STRUCTS:
            p.expect("OP", "*")
            utype = "Ptr:" + typ
        else:
            utype = typ
        name = p.expect("ID").v
        init = None
        if p.at("OP", "="):
            p.next()
            init = parse_expr(p)
        return N("udecl", t.line, utype=utype, name=name, init=init)
    # store: *p = v
    if t.k == "OP" and t.v == "*":
        p.next()
        ptr = parse_un(p)
        p.expect("OP", "=")
        val = parse_expr(p)
        return N("store", t.line, ptr=ptr, val=val)
    if t.k == "ID" and t.v == "def":
        raise HSErr("def not allowed in unsafe", t.line)
    if t.k == "ID" and t.v == "for":
        raise HSErr("for not allowed in unsafe (use while)", t.line)
    if t.k == "ID" and t.v == "try":
        raise HSErr("try not allowed in unsafe (wrap the unsafe block instead)", t.line)
    if t.k == "ID" and t.v == "extern":
        raise HSErr("extern not allowed in unsafe (declare at top level)", t.line)
    if t.k == "ID" and t.v == "raise":
        p.next()
        e = None
        if not p.at("NEWLINE") and not p.at("EOF") and not p.at("DEDENT"):
            e = parse_expr(p)
        return N("raise", t.line, val=e)
    if t.k == "ID" and t.v == "unsafe":
        raise HSErr("unsafe inside unsafe", t.line)
    # shared statements (if/while/return/break/continue/pass/global/print)
    if t.k == "ID" and t.v in ("if", "while", "return", "break",
                               "continue", "pass", "global", "print"):
        return parse_stmt(p)
    # assignment (static or dynamic target) or expression statement
    e = parse_expr(p)
    if p.at("OP", "="):
        p.next()
        rhs = parse_expr(p)
        if e["t"] == "var":
            return N("set", t.line, name=e["name"], val=rhs)
        if e["t"] == "field":
            return N("fstore", t.line, obj=e["obj"], name=e["name"],
                     idx=e.get("idx"), val=rhs)
        raise HSErr("cannot assign to this in unsafe (use *p = v for memory)", t.line)
    return N("expr", t.line, val=e)


def parse_if(p):
    t = p.expect("ID")  # if
    c = parse_expr(p)
    p.expect("OP", ":")
    then = parse_block(p, t.line)
    elifs = []
    els = []
    while p.at("ID", "elif"):
        p.next()
        ec = parse_expr(p)
        p.expect("OP", ":")
        elifs.append((ec, parse_block(p, t.line)))
    if p.at("ID", "else"):
        p.next()
        p.expect("OP", ":")
        els = parse_block(p, t.line)
    return N("if", t.line, cond=c, then=then, elifs=elifs, els=els)


def parse_print(p):
    t = p.expect("ID")  # print
    args = []
    if p.at("NEWLINE") or p.at("EOF") or p.at("DEDENT"):
        return N("print", t.line, args=args)
    if p.at("OP", "("):
        p.next()
        if not p.at("OP", ")"):
            while True:
                args.append(parse_expr(p))
                if p.at("OP", ","):
                    p.next()
                    continue
                break
        p.expect("OP", ")")
        return N("print", t.line, args=args)
    while True:
        args.append(parse_expr(p))
        if p.at("OP", ","):
            p.next()
            continue
        break
    return N("print", t.line, args=args)


def parse_expr(p):
    return parse_or(p)


def parse_or(p):
    l = parse_and(p)
    while p.at("ID", "or"):
        t = p.next()
        l = N("bin", t.line, op="or", l=l, r=parse_and(p))
    return l


def parse_and(p):
    l = parse_not(p)
    while p.at("ID", "and"):
        t = p.next()
        l = N("bin", t.line, op="and", l=l, r=parse_not(p))
    return l


def parse_not(p):
    if p.at("ID", "not"):
        t = p.next()
        return N("not", t.line, val=parse_not(p))
    return parse_cmp(p)


def parse_cmp(p):
    l = parse_add(p)
    ops = []
    while p.at("OP") and p.peek().v in ("==", "!=", "<", ">", "<=", ">="):
        t = p.next()
        ops.append((t.v, parse_add(p), t.line))
    if not ops:
        return l
    if len(ops) == 1:
        op, r, ln = ops[0]
        return N("bin", ln, op=op, l=l, r=r)
    # a < b < c  ->  (a<b) and (b<c)
    out = None
    prev = l
    for op, r, ln in ops:
        one = N("bin", ln, op=op, l=prev, r=r)
        out = one if out is None else N("bin", ln, op="and", l=out, r=one)
        prev = r
    return out


def parse_bits(p):
    # bitwise binds tighter than +- and looser than */: a & b + c == (a & b) + c
    l = parse_mul(p)
    while p.at("OP") and p.peek().v in ("<<", ">>", "&", "|", "^"):
        t = p.next()
        l = N("bin", t.line, op=t.v, l=l, r=parse_mul(p))
    return l


def parse_add(p):
    l = parse_bits(p)
    while p.at("OP") and p.peek().v in ("+", "-"):
        t = p.next()
        l = N("bin", t.line, op=t.v, l=l, r=parse_bits(p))
    return l


def parse_mul(p):
    l = parse_un(p)
    while p.at("OP") and p.peek().v in ("*", "/", "%"):
        t = p.next()
        l = N("bin", t.line, op=t.v, l=l, r=parse_un(p))
    return l


def parse_un(p):
    if p.at("OP", "~"):
        t = p.next()
        return N("unot", t.line, val=parse_un(p))
    if p.at("OP", "-"):
        t = p.next()
        return N("neg", t.line, val=parse_un(p))
    if p.unsafe > 0 and p.at("OP", "*"):
        t = p.next()
        return N("deref", t.line, val=parse_un(p))
    if p.unsafe > 0 and p.at("ID", "sizeof"):
        t = p.next()
        p.expect("OP", "(")
        tn = p.expect("ID")
        if tn.v not in ("I64", "U64", "Ptr") and tn.v not in HS_STRUCTS:
            raise HSErr(f"sizeof wants a type, got '{tn.v}'", tn.line)
        p.expect("OP", ")")
        return N("sizeof", t.line, stype=tn.v)
    return parse_post(p)


def parse_post(p):
    e = parse_atom(p)
    while True:
        if p.at("OP", "("):
            t = p.next()
            args = []
            if not p.at("OP", ")"):
                while True:
                    args.append(parse_expr(p))
                    if p.at("OP", ","):
                        p.next()
                        continue
                    break
            p.expect("OP", ")")
            if e["t"] == "attr" and e["name"] in METHODS and \
                    not _is_modref(e["obj"], p.mods):
                # x.name(args) on a value == name(x, args) (method sugar,
                # resolved here so every backend sees the plain builtin call)
                e = N("call", t.line, fn=N("var", t.line, name=METHODS[e["name"]]),
                      args=[e["obj"]] + args, method=e["name"])
            else:
                e = N("call", t.line, fn=e, args=args)
        elif p.at("OP", "["):
            t = p.next()
            if p.at("OP", ":"):
                start = None
            else:
                start = parse_expr(p)
            if p.at("OP", ":"):
                p.next()
                if p.at("OP", "]"):
                    stop = None
                else:
                    stop = parse_expr(p)
                p.expect("OP", "]")
                e = N("slice", t.line, obj=e, start=start, stop=stop)
            else:
                idx = start
                p.expect("OP", "]")
                e = N("index", t.line, obj=e, idx=idx)
        elif p.at("OP", "."):
            t = p.next()
            nm = p.expect("ID")
            if p.unsafe > 0:
                idx = None
                if p.at("OP", "["):
                    p.next()
                    idx = parse_expr(p)
                    p.expect("OP", "]")
                e = N("field", t.line, obj=e, name=nm.v, idx=idx)
            else:
                e = N("attr", t.line, obj=e, name=nm.v)
        else:
            return e


# method sugar: receiver.name(args) -> builtin(receiver, args). Receivers that
# are (a dotted path rooted at) an imported module keep their module meaning.
METHODS = {"split": "split", "find": "find", "join": "join", "append": "append"}


def _is_modref(e, mods):
    while e["t"] == "attr":
        e = e["obj"]
    return e["t"] == "var" and e["name"] in mods


def parse_lambda(p):
    """lambda a, b: expr  ->  a fresh `def _lamN(a, b): return expr` emitted
    just before the enclosing statement, and the expression becomes `_lamN`.
    Closures already capture the enclosing scope, so this matches Python's
    lambda for every case the language can express."""
    t = p.next()  # lambda
    if p.unsafe > 0:
        raise HSErr("lambda not allowed in unsafe", t.line)
    params = []
    if not p.at("OP", ":"):
        while True:
            a = p.expect("ID").v
            if a in KEYWORDS:
                raise HSErr(f"bad parameter name '{a}'", t.line)
            if a in params:
                raise HSErr(f"duplicate param '{a}'", t.line)
            params.append(a)
            if p.at("OP", ","):
                p.next()
                continue
            break
    p.expect("OP", ":")
    outer, p.hoist = p.hoist, []
    body = parse_expr(p)
    inner = p.hoist      # lambdas nested in the body live inside this one
    p.hoist = outer
    p.nlam += 1
    name = f"_lam{p.nlam}"
    d = N("def", t.line, name=name, params=params,
          body=inner + [N("return", t.line, val=body)], lam=True)
    p.hoist.append(d)
    return N("var", t.line, name=name)


def parse_fstring(p, t):
    """f"a{x}b" -> "a" + str(x) + "b" (parse-time desugar; every backend
    sees plain + and str()). `fs` keeps the parts so fmt can print it back.
    {{ and }} are literal braces. Expressions cannot contain a double quote."""
    raw, ln = t.v, t.line
    parts = []
    lit = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            lit.append(raw[i:i + 2])
            i += 2
        elif raw[i:i + 2] == "{{":
            lit.append("{")
            i += 2
        elif raw[i:i + 2] == "}}":
            lit.append("}")
            i += 2
        elif c == "}":
            raise HSErr("single '}' in f-string (write }})", ln)
        elif c == "{":
            depth, j = 1, i + 1
            while j < len(raw) and depth:
                depth += (raw[j] == "{") - (raw[j] == "}")
                j += 1
            if depth:
                raise HSErr("unclosed '{' in f-string", ln)
            src = raw[i + 1:j - 1]
            if not src.strip():
                raise HSErr("empty {} in f-string", ln)
            if lit:
                parts.append(unesc('"' + "".join(lit) + '"', ln))
                lit = []
            sp = P(lex_line(src, ln) + [Tok("EOF", "", ln)])
            sp.unsafe, sp.mods = p.unsafe, p.mods
            e = parse_expr(sp)
            if not sp.at("EOF"):
                raise HSErr("bad expression in f-string", ln)
            parts.append(e)
            i = j
        else:
            lit.append(c)
            i += 1
    if lit:
        parts.append(unesc('"' + "".join(lit) + '"', ln))
    node = None
    for q in parts:
        if isinstance(q, str):
            x = N("str", ln, val=q)
        else:
            x = N("call", ln, fn=N("var", ln, name="str"), args=[q])
        node = x if node is None else N("bin", ln, op="+", l=node, r=x)
    if node is None:
        node = N("str", ln, val="")
    if node["t"] != "bin":
        node = N("bin", ln, op="+", l=N("str", ln, val=""), r=node)
    node["fs"] = parts
    return node


def parse_atom(p):
    t = p.peek()
    if t.k == "NUM":
        p.next()
        return N("num", t.line, val=t.v, raw=t.raw)
    if t.k == "STR":
        p.next()
        return N("str", t.line, val=t.v)
    if t.k == "FSTR":
        p.next()
        return parse_fstring(p, t)
    if t.k == "ID" and t.v in ("true", "false", "null"):
        p.next()
        return N("num", t.line, val={"true": True, "false": False, "null": None}[t.v])
    if t.k == "ID" and t.v == "print":
        raise HSErr("print is a statement, use: print ...", t.line)
    if t.k == "ID" and t.v == "lambda":
        return parse_lambda(p)
    if t.k == "ID":
        p.next()
        return N("var", t.line, name=t.v)
    if t.k == "OP" and t.v == "(":
        p.next()
        e = parse_expr(p)
        p.expect("OP", ")")
        return e
    if t.k == "OP" and t.v == "[":
        p.next()
        items = []
        if not p.at("OP", "]"):
            while True:
                items.append(parse_expr(p))
                if p.at("OP", ","):
                    p.next()
                    continue
                break
        p.expect("OP", "]")
        return N("list", t.line, items=items)
    if t.k == "OP" and t.v == "{":
        p.next()
        pairs = []
        if not p.at("OP", "}"):
            while True:
                k = parse_expr(p)
                p.expect("OP", ":")
                v = parse_expr(p)
                pairs.append((k, v))
                if p.at("OP", ","):
                    p.next()
                    continue
                break
        p.expect("OP", "}")
        return N("dict", t.line, pairs=pairs)
    raise HSErr(f"expression expected, got {t.v!r}", t.line)


# ---------- evaluator ----------
class Env:
    def __init__(self, parent=None, is_root=False, basedir="", gbase=None):
        self.vars = {}
        self.parent = parent
        self.is_root = is_root
        self.globals = set()
        self.basedir = basedir if basedir else (parent.basedir if parent else "")
        self.gbase = gbase if gbase is not None else (
            parent.gbase if parent is not None else self)

    def root(self):
        return self.gbase

    def get(self, name, line):
        e = self
        while e is not None:
            if name in e.vars:
                return e.vars[name]
            e = e.parent
        raise HSErr(f"unknown variable '{name}'", line)

    def set(self, name, val):
        if name in self.globals:
            self.root().vars[name] = val
        else:
            self.vars[name] = val


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def ev(e, env):
    t = e["t"]
    ln = e["line"]
    if t == "num" or t == "str":
        return e["val"]
    if t == "var":
        v = env.get(e["name"], ln)
        if isinstance(v, UnsafeVal):
            return box(v.utype, v.val, ln)
        return v
    if t == "list":
        return [ev(x, env) for x in e["items"]]
    if t == "dict":
        d = {}
        for k, v in e["pairs"]:
            kk = ev(k, env)
            if not _keyok(kk):
                raise HSErr("dict key must be Str or Int", ln)
            d[kk] = ev(v, env)
        return d
    if t == "neg":
        v = ev(e["val"], env)
        if is_num(v):
            return -v
        raise HSErr(f"cannot negate {tname(v)}", ln)
    if t == "unot":
        v = ev(e["val"], env)
        if not is_int(v):
            raise HSErr(f"cannot bitwise-not {tname(v)}", ln)
        return wrap_i64(~v)
    if t == "not":
        return not ev(e["val"], env)
    if t == "bin":
        return ev_bin(e, env)
    if t == "call":
        return ev_call(e, env)
    if t == "index":
        return ev_index(e, env)
    if t == "attr":
        obj = ev(e["obj"], env)
        if not isinstance(obj, HSMod):
            raise HSErr("only modules have attributes", ln)
        if e["name"] not in obj.env.vars:
            raise HSErr(f"module '{obj.name}' has no attribute '{e['name']}'", ln)
        v = obj.env.vars[e["name"]]
        if isinstance(v, UnsafeVal):
            return box(v.utype, v.val, ln)
        return v
    if t == "slice":
        return ev_slice(e, env)
    raise HSErr(f"bad node {t}", ln)


def _keyok(k):
    # dict keys: Str or Int (Bool is excluded: True == 1 would alias)
    return isinstance(k, str) or (isinstance(k, int) and not isinstance(k, bool))


def ev_slice(e, env):
    ln = e["line"]
    obj = ev(e["obj"], env)
    if isinstance(obj, UnsafeVal):
        raise HSErr("slicing not allowed in unsafe", ln)
    lo = None
    hi = None
    if e["start"] is not None:
        lo = ev(e["start"], env)
        if not isinstance(lo, int) or isinstance(lo, bool):
            raise HSErr("slice index must be Int", ln)
    if e["stop"] is not None:
        hi = ev(e["stop"], env)
        if not isinstance(hi, int) or isinstance(hi, bool):
            raise HSErr("slice index must be Int", ln)
    if isinstance(obj, (list, str)):
        n = len(obj)
        a = lo if lo is not None else 0
        b = hi if hi is not None else n
        if a < 0:
            a += n
        if b < 0:
            b += n
        a = max(0, min(a, n))
        b = max(0, min(b, n))
        return obj[a:b] if a < b else obj[:0]
    raise HSErr(f"cannot slice {tname(obj)}", ln)


def ev_bin(e, env):
    op = e["op"]
    ln = e["line"]
    if op == "and":
        l = ev(e["l"], env)
        return l if not l else ev(e["r"], env)
    if op == "or":
        l = ev(e["l"], env)
        return l if l else ev(e["r"], env)
    l = ev(e["l"], env)
    r = ev(e["r"], env)
    if op in ("<<", ">>", "&", "|", "^"):
        if not is_int(l) or not is_int(r):
            raise HSErr(f"operator '{op}' needs Ints, got "
                        f"{tname(l)} and {tname(r)}", ln)
        if op == "&":
            return l & r
        if op == "|":
            return l | r
        if op == "^":
            return l ^ r
        if r < 0 or r > 63:
            raise HSErr(f"shift count {r} out of range (0..63)", ln)
        if op == "<<":
            return wrap_i64(l << r)
        return l >> r      # arithmetic shift, like C on signed Int
    if op == "+":
        if is_num(l) and is_num(r):
            if isinstance(l, float) or isinstance(r, float):
                return float(l) + float(r)
            return l + r
        if isinstance(l, str) and isinstance(r, str):
            return l + r
        if isinstance(l, list) and isinstance(r, list):
            return l + r
        raise HSErr(f"cannot add {tname(l)} and {tname(r)}", ln)
    if op in ("-", "*", "/", "%"):
        if not (is_num(l) and is_num(r)):
            raise HSErr(f"operator '{op}' needs numbers, got {tname(l)} and {tname(r)}", ln)
        try:
            if op == "-":
                return (float(l) - float(r)) if isinstance(l, float) or isinstance(r, float) else l - r
            if op == "*":
                return (float(l) * float(r)) if isinstance(l, float) or isinstance(r, float) else l * r
            if op == "/":
                if r == 0:
                    raise HSErr("division by zero", ln)
                return float(l) / float(r)
            if op == "%":
                if r == 0:
                    raise HSErr("division by zero", ln)
                if isinstance(l, float) or isinstance(r, float):
                    return float(l) % float(r)
                return l % r
        except HSErr:
            raise
        except Exception as ex:
            raise HSErr(str(ex), ln)
    if op in ("==", "!="):
        try:
            eq = (l == r)
        except Exception:
            eq = False
        if isinstance(eq, bool):
            return eq if op == "==" else (not eq)
        return bool(eq) if op == "==" else (not bool(eq))
    if op in ("<", ">", "<=", ">="):
        if is_num(l) and is_num(r):
            a, b = float(l), float(r)
        elif isinstance(l, str) and isinstance(r, str):
            a, b = l, r
        else:
            raise HSErr(f"cannot compare {tname(l)} and {tname(r)}", ln)
        if op == "<":
            return a < b
        if op == ">":
            return a > b
        if op == "<=":
            return a <= b
        return a >= b
    raise HSErr(f"bad operator {op}", ln)


def ev_index(e, env):
    ln = e["line"]
    obj = ev(e["obj"], env)
    idx = ev(e["idx"], env)
    if isinstance(obj, (list, str)):
        if not is_num(idx) or isinstance(idx, float):
            raise HSErr("index must be Int", ln)
        i = int(idx)
        if i < 0:
            i += len(obj)
        if i < 0 or i >= len(obj):
            raise HSErr("index out of range", ln)
        return obj[i]
    if isinstance(obj, dict):
        if not _keyok(idx):
            raise HSErr("dict key must be Str or Int", ln)
        if idx not in obj:
            raise HSErr(f"key {idx!r} not found", ln)
        return obj[idx]
    raise HSErr(f"cannot index {tname(obj)}", ln)


def ev_call(e, env):
    ln = e["line"]
    if e["fn"]["t"] == "var" and e["fn"]["name"] == "asm":
        raise HSErr("asm only allowed in unsafe", ln)
    fn = ev(e["fn"], env)
    args = [ev(a, env) for a in e["args"]]
    if isinstance(fn, HSBuiltin):
        return fn.fn(args, ln)
    if isinstance(fn, HSExtern):
        return fn.call(args, ln)
    if isinstance(fn, HSFunc):
        if len(args) != len(fn.params):
            raise HSErr(f"{fn.name} wants {len(fn.params)} args, got {len(args)}", ln)
        fenv = Env(parent=fn.closure)
        for n, v in zip(fn.params, args):
            fenv.vars[n] = v
        try:
            ex_body(fn.body, fenv)
        except ReturnExc as r:
            return r.value
        return None
    raise HSErr(f"not callable: {tname(fn)}", ln)


def sev(e, env):
    """static eval inside unsafe. Returns (type, pyval), type in I64/U64/Ptr/LIT."""
    t = e["t"]
    ln = e["line"]
    if t == "num":
        v = e["val"]
        if v is None:
            return ("Ptr", 0)
        if isinstance(v, bool):
            return ("I64", int(v))
        if isinstance(v, int):
            return ("LIT", v)
        raise HSErr("float not allowed in unsafe", ln)
    if t == "str":
        raise HSErr("strings not allowed in unsafe (use alloc + store8)", ln)
    if t == "var":
        v = lookup(e["name"], env, ln)
        if isinstance(v, UnsafeVal):
            return (v.utype, v.val)
        return ("I64", unbox(v, "I64", ln))
    if t == "deref":
        st, sv = sev(e["val"], env)
        if not is_ptr(st):
            raise HSErr(f"cannot dereference {st} (need Ptr)", ln)
        return ("I64", wrap_i64(us_load(sv, 8, ln)))
    if t == "sizeof":
        st = e["stype"]
        if st in ("I64", "U64", "Ptr"):
            return ("I64", 8)
        return ("I64", struct_size(st, ln))
    if t == "field":
        return sev_field(e, env)
    if t == "neg":
        st, sv = sev(e["val"], env)
        if is_ptr(st):
            raise HSErr("cannot negate Ptr", ln)
        if st == "LIT":
            return ("LIT", -sv)
        if st == "I64":
            return ("I64", wrap_i64(-sv))
        return ("U64", wrap_u64(-sv))
    if t == "unot":
        st, sv = sev(e["val"], env)
        if is_ptr(st):
            raise HSErr("cannot bitwise-not Ptr", ln)
        return (st, wrap_i64(~sv) if st != "U64" else wrap_u64(~sv))
    if t == "not":
        st, sv = sev(e["val"], env)
        return ("I64", 0 if sv != 0 else 1)
    if t == "bin":
        return sev_bin(e, env)
    if t == "call":
        return sev_call(e, env)
    if t in ("index", "list", "dict"):
        raise HSErr("collections not allowed in unsafe (use alloc/load/store)", ln)
    if t == "attr":
        raise HSErr("attribute access not allowed in unsafe", ln)
    if t == "slice":
        raise HSErr("slicing not allowed in unsafe", ln)
    raise HSErr(f"bad unsafe expr {t}", ln)


def sev_field(e, env):
    """p.field / p.arr[i] -> (static type, value)."""
    ln = e["line"]
    st, sv = sev(e["obj"], env)
    xs = ptr_struct(st)
    if xs is None:
        raise HSErr(f"cannot access field of {st} (need a struct pointer)", ln)
    if sv == 0:
        raise HSErr("null pointer dereference", ln)
    ft, off, count = struct_field(xs, e["name"], ln)
    if count > 1:
        if e["idx"] is None:
            raise HSErr(f"array field '{e['name']}' needs an index", ln)
        it, iv = sev(e["idx"], env)
        i = coerce(it, iv, "I64", ln)
        if i < 0 or i >= count:
            raise HSErr(f"index {i} out of range for '{e['name']}'[{count}]", ln)
    else:
        if e["idx"] is not None:
            raise HSErr(f"field '{e['name']}' is not an array", ln)
        i = 0
    addr = sv + off + i * 8
    v = us_load(addr, 8, ln)
    if ft in ("I64", "U64"):
        return (ft, wrap_i64(v) if ft == "I64" else wrap_u64(v))
    return (ft, v & MASK64)  # Ptr field: the stored address


def sev_bin(e, env):
    op = e["op"]
    ln = e["line"]
    if op in ("and", "or"):
        # in unsafe these yield I64 0/1 (strict, documented)
        lt, lv = sev(e["l"], env)
        if op == "and":
            if lv == 0:
                return ("I64", 0)
            rt, rv = sev(e["r"], env)
            return ("I64", 1 if rv != 0 else 0)
        if lv != 0:
            return ("I64", 1)
        rt, rv = sev(e["r"], env)
        return ("I64", 1 if rv != 0 else 0)
    lt, lv = sev(e["l"], env)
    rt, rv = sev(e["r"], env)
    if op in ("==", "!="):
        if is_ptr(lt) or is_ptr(rt):
            if not (is_ptr(lt) and is_ptr(rt)):
                raise HSErr(f"cannot compare {lt} and {rt}", ln)
            eq = 1 if lv == rv else 0
        else:
            kinds = {lt, rt} - {"LIT"}
            if kinds == {"I64", "U64"}:
                raise HSErr("cannot compare I64 and U64 (convert explicitly)", ln)
            tgt = (kinds.pop() if kinds else "I64")
            eq = 1 if coerce(lt, lv, tgt, ln) == coerce(rt, rv, tgt, ln) else 0
        return ("I64", eq if op == "==" else 1 - eq)
    if op in ("<", ">", "<=", ">="):
        if is_ptr(lt) or is_ptr(rt):
            raise HSErr("cannot order pointers (use == / !=)", ln)
        if lt != rt and ("I64" in (lt, rt) and "U64" in (lt, rt)):
            raise HSErr("cannot compare I64 and U64 (convert explicitly)", ln)
        tgt = lt if lt != "LIT" else (rt if rt != "LIT" else "I64")
        a = coerce(lt, lv, tgt, ln)
        b = coerce(rt, rv, tgt, ln)
        if op == "<":
            r = a < b
        elif op == ">":
            r = a > b
        elif op == "<=":
            r = a <= b
        else:
            r = a >= b
        return ("I64", 1 if r else 0)
    # arithmetic
    if is_ptr(lt) or is_ptr(rt):
        lxs, rxs = ptr_struct(lt), ptr_struct(rt)
        if op == "+" and lxs and rt in ("I64", "U64", "LIT"):
            return (lt, (lv + coerce(rt, rv, "I64", ln) * struct_size(lxs, ln)) & MASK64)
        if op == "+" and rxs and lt in ("I64", "U64", "LIT"):
            return (rt, (rv + coerce(lt, lv, "I64", ln) * struct_size(rxs, ln)) & MASK64)
        if op == "-" and lxs and rt in ("I64", "U64", "LIT"):
            return (lt, (lv - coerce(rt, rv, "I64", ln) * struct_size(lxs, ln)) & MASK64)
        if op == "-" and lxs and rxs and lxs == rxs:
            d = lv - rv
            q = abs(d) // struct_size(lxs, ln)
            return ("I64", wrap_i64(-q if d < 0 else q))
        if lt == "Ptr" or rt == "Ptr":
            if op == "+" and lt == "Ptr" and rt in ("I64", "U64", "LIT"):
                return ("Ptr", (lv + coerce(rt, rv, "I64", ln)) & MASK64)
            if op == "+" and rt == "Ptr" and lt in ("I64", "U64", "LIT"):
                return ("Ptr", (rv + coerce(lt, lv, "I64", ln)) & MASK64)
            if op == "-" and lt == "Ptr" and rt in ("I64", "U64", "LIT"):
                return ("Ptr", (lv - coerce(rt, rv, "I64", ln)) & MASK64)
            if op == "-" and lt == "Ptr" and rt == "Ptr":
                return ("I64", wrap_i64(lv - rv))
        raise HSErr(f"cannot apply '{op}' to pointers", ln)
    if lt != rt and ("I64" in (lt, rt) and "U64" in (lt, rt)):
        raise HSErr(f"cannot mix I64 and U64 with '{op}' (convert explicitly)", ln)
    tgt = lt if lt != "LIT" else (rt if rt != "LIT" else "I64")
    a = coerce(lt, lv, tgt, ln)
    b = coerce(rt, rv, tgt, ln)
    if op == "+":
        r = a + b
    elif op == "-":
        r = a - b
    elif op == "*":
        r = a * b
    elif op == "/":
        if b == 0:
            raise HSErr("division by zero", ln)
        # unsafe division truncates toward zero (C-like), unlike safe /
        r = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            r = -r
    elif op == "%":
        if b == 0:
            raise HSErr("division by zero", ln)
        r = abs(a) % abs(b)
        if a < 0:
            r = -r
    elif op == "&":
        r = a & b
    elif op == "|":
        r = a | b
    elif op == "^":
        r = a ^ b
    elif op == "<<":
        if b < 0 or b > 63:
            raise HSErr(f"shift count {b} out of range (0..63)", ln)
        r = a << b
    elif op == ">>":
        if b < 0 or b > 63:
            raise HSErr(f"shift count {b} out of range (0..63)", ln)
        r = a >> b
    else:
        raise HSErr(f"bad operator {op}", ln)
    return (tgt, wrap_i64(r) if tgt == "I64" else wrap_u64(r))


def sev_call(e, env):
    ln = e["line"]
    if e["fn"]["t"] != "var":
        raise HSErr("cannot call result of expression from unsafe", ln)
    name = e["fn"]["name"]
    if name not in UNSAFE_BUILTINS:
        raise HSErr(
            f"cannot call '{name}' from unsafe (only: {', '.join(sorted(UNSAFE_BUILTINS))})", ln)
    args = e["args"]
    if name == "alloc":
        if len(args) != 1:
            raise HSErr("alloc wants alloc(n)", ln)
        at, av = sev(args[0], env)
        n = coerce(at, av, "I64", ln)
        return ("Ptr", us_alloc(n, ln))
    if name in ("load8", "load32", "load64"):
        if len(args) != 1:
            raise HSErr(f"{name} wants {name}(p)", ln)
        pt, pv = sev(args[0], env)
        if not is_ptr(pt):
            raise HSErr(f"{name} needs Ptr, got {pt}", ln)
        return ("I64", wrap_i64(us_load(pv, UNSAFE_SIZES[name], ln)))
    if name in ("store8", "store32", "store64"):
        if len(args) != 2:
            raise HSErr(f"{name} wants {name}(p, v)", ln)
        pt, pv = sev(args[0], env)
        if not is_ptr(pt):
            raise HSErr(f"{name} needs Ptr, got {pt}", ln)
        vt, vv = sev(args[1], env)
        vv = coerce(vt, vv, "I64", ln)
        size = UNSAFE_SIZES[name]
        us_store(pv, size, vv, ln)
        return ("I64", wrap_i64(vv & ((1 << (size * 8)) - 1)))
    if name == "as_ptr":
        if len(args) != 1:
            raise HSErr("as_ptr wants as_ptr(int)", ln)
        at, av = sev(args[0], env)
        if at not in ("LIT", "I64", "U64") and not is_ptr(at):
            raise HSErr(f"as_ptr needs an integer, got {at}", ln)
        return ("Ptr", unbox(av, "Ptr", ln))
    if name == "as_int":
        if len(args) != 1:
            raise HSErr("as_int wants as_int(p)", ln)
        pt, pv = sev(args[0], env)
        if not is_ptr(pt):
            raise HSErr(f"as_int needs Ptr, got {pt}", ln)
        return ("U64", pv)
    if name == "asm":
        if len(args) != 1 or args[0]["t"] != "str":
            raise HSErr("asm wants asm(\"...\") with a string literal", ln)
        raise HSErr("asm requires native build (hs.py build)", ln)
    raise HSErr(f"bad unsafe call {name}", ln)


def lookup(name, env, line):
    e = env
    while e is not None:
        if name in e.vars:
            return e.vars[name]
        e = e.parent
    raise HSErr(f"unknown variable '{name}'", line)


# ---------- modules ----------
import os as _os
import re as _re

MOD_CACHE = {}  # abspath -> {"state": busy/done, "mod": HSMod}
BUILTINS_ENV = None  # set in main(); module envs chain to it


def _hspath():
    return [d for d in _os.environ.get("HSPATH", "").split(":") if d]


def find_module_file(name, basedir, line):
    rel = name.replace(".", "/") + ".hs"
    dirs = [basedir] + _hspath() + [_os.getcwd()]
    for d in dirs:
        if not d:
            continue
        p = _os.path.join(d, rel)
        if _os.path.isfile(p):
            return _os.path.abspath(p)
    raise HSErr(f"cannot find module '{name}'", line)


def do_import(name, env, line):
    if not _re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$", name):
        raise HSErr(f"bad module name '{name}'", line)
    if "." in name:
        parent, _, leaf = name.rpartition(".")
        try:
            pmod = do_import(parent, env, line)
        except HSErr as e:
            if f"cannot find module '{parent}'" not in str(e):
                raise
            pmod = _shell_mod(parent)
        path = find_module_file(name, env.basedir, line)
        leafmod = _load_mod_file(name, path, line)
        pmod.env.vars[leaf] = leafmod
        return leafmod
    if name in _SHELL_MODS:
        return _SHELL_MODS[name]
    path = find_module_file(name, env.basedir, line)
    return _load_mod_file(name, path, line)


_SHELL_MODS = {}  # dotted name -> empty package HSMod


def _shell_mod(name):
    m = _SHELL_MODS.get(name)
    if m is None:
        menv = Env(parent=BUILTINS_ENV)
        menv.gbase = menv
        m = HSMod(name, menv)
        _SHELL_MODS[name] = m
    return m


def _load_mod_file(name, path, line):
    ent = MOD_CACHE.get(path)
    if ent is not None:
        if ent["state"] == "done":
            return ent["mod"]
        raise HSErr(f"circular import '{name}'", line)
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        prog = parse_program(src)
    except HSErr as e:
        raise HSErr(f"in module '{name}': {e.msg}", e.line)
    mod = HSMod(name, None)
    MOD_CACHE[path] = {"state": "busy", "mod": mod}
    menv = Env(parent=BUILTINS_ENV, basedir=_os.path.dirname(path))
    menv.gbase = menv
    mod.env = menv
    try:
        ex_body(prog, menv)
    except HSErr as e:
        del MOD_CACHE[path]
        raise HSErr(f"in module '{name}': {e.msg}", e.line)
    MOD_CACHE[path] = {"state": "done", "mod": mod}
    return mod


def ex_body(body, env, ux=False):
    for s in body:
        ex(s, env, ux)


def find_var(name, env):
    e = env
    while e is not None:
        if name in e.vars:
            return e, e.vars[name]
        e = e.parent
    return None, None


def ex(s, env, ux=False):
    t = s["t"]
    ln = s["line"]
    if t == "pass":
        return
    if t == "unsafe":
        ex_body(s["body"], env, True)
        return
    if t == "struct":
        return  # types registered at parse time; no runtime code
    if t == "udecl":
        if s["name"] in env.vars:
            raise HSErr(f"'{s['name']}' already defined in this scope", ln)
        typ = s["utype"]
        if s["init"] is None:
            v = 0
        else:
            st, sv = sev(s["init"], env)
            v = coerce(st, sv, typ, ln)
        env.vars[s["name"]] = UnsafeVal(typ, v)
        return
    if t == "store":
        pt, pv = sev(s["ptr"], env)
        if not is_ptr(pt):
            raise HSErr(f"cannot store through {pt} (need Ptr)", ln)
        vt, vv = sev(s["val"], env)
        if vt not in ("LIT", "I64", "U64"):
            raise HSErr(f"cannot store {vt} to memory (need integer)", ln)
        us_store(pv, 8, coerce(vt, vv, "I64", ln) & MASK64, ln)
        return
    if t == "fstore":
        st, sv = sev(s["obj"], env)
        xs = ptr_struct(st)
        if xs is None:
            raise HSErr(f"cannot store field of {st} (need a struct pointer)", ln)
        if sv == 0:
            raise HSErr("null pointer dereference", ln)
        ft, off, count = struct_field(xs, s["name"], ln)
        if count > 1:
            if s["idx"] is None:
                raise HSErr(f"array field '{s['name']}' needs an index", ln)
            it, iv = sev(s["idx"], env)
            i = coerce(it, iv, "I64", ln)
            if i < 0 or i >= count:
                raise HSErr(f"index {i} out of range for '{s['name']}'[{count}]", ln)
        else:
            if s["idx"] is not None:
                raise HSErr(f"field '{s['name']}' is not an array", ln)
            i = 0
        vt, vv = sev(s["val"], env)
        us_store(sv + off + i * 8, 8, coerce(vt, vv, ft, ln) & MASK64, ln)
        return
    if t == "expr":
        if ux:
            sev(s["val"], env)
        else:
            ev(s["val"], env)
        return
    if t == "print":
        if ux:
            parts = []
            for a in s["args"]:
                if a["t"] == "str":
                    parts.append(a["val"])
                else:
                    parts.append(disp(box(*sev(a, env), ln)))
            sys.stdout.write(" ".join(parts) + "\n")
        else:
            sys.stdout.write(" ".join(disp(ev(a, env)) for a in s["args"]) + "\n")
        return
    if t == "set":
        holder, found = find_var(s["name"], env)
        if isinstance(found, UnsafeVal):
            if ux:
                st, sv = sev(s["val"], env)
                holder.vars[s["name"]] = UnsafeVal(found.utype, coerce(st, sv, found.utype, ln))
            else:
                v = ev(s["val"], env)
                holder.vars[s["name"]] = UnsafeVal(found.utype, unbox(v, found.utype, ln))
            return
        if ux:
            env.set(s["name"], box(*sev(s["val"], env), ln))
        else:
            env.set(s["name"], ev(s["val"], env))
        return
    if t == "setindex":
        obj = ev(s["obj"], env)
        idx = ev(s["idx"], env)
        val = ev(s["val"], env)
        if isinstance(obj, list):
            if not is_num(idx) or isinstance(idx, float):
                raise HSErr("index must be Int", ln)
            i = int(idx)
            if i < 0:
                i += len(obj)
            if i < 0 or i >= len(obj):
                raise HSErr("index out of range", ln)
            obj[i] = val
            return
        if isinstance(obj, dict):
            if not _keyok(idx):
                raise HSErr("dict key must be Str or Int", ln)
            obj[idx] = val
            return
        raise HSErr(f"cannot assign into {tname(obj)}", ln)
    if t == "setattr":
        obj = ev(s["obj"], env)
        if not isinstance(obj, HSMod):
            raise HSErr("only modules have attributes", ln)
        obj.env.vars[s["name"]] = ev(s["val"], env) if not ux else box(*sev(s["val"], env), ln)
        return
    if t == "import":
        parts = s["name"].split(".")
        mod = do_import(s["name"], env, ln)
        top = mod if len(parts) == 1 else do_import(parts[0], env, ln)
        env.set(parts[0], top)
        return
    if t == "extern":
        cdll = ffi_load(s["lib"], env.basedir, ln)
        for d in s["decls"]:
            if d["name"] in BUILTINS:
                raise HSErr(f"cannot shadow builtin '{d['name']}'", d["line"])
            if d["name"] in env.vars:
                raise HSErr(f"'{d['name']}' already defined in this scope", d["line"])
            env.vars[d["name"]] = HSExtern(d["name"], d["rtype"], d["params"], cdll, d["line"])
        return
    if t == "try":
        held = None
        try:
            try:
                ex_body(s["body"], env, ux)
            except HSErr as e:
                if s["ebody"] is None:
                    held = e
                else:
                    _EXC_STACK.append((e.msg, e.line))
                    try:
                        if s["ename"] is not None:
                            emsg = e.msg + (f" at line {e.line}" if e.line else "")
                            e2 = Env(parent=env)
                            e2.vars[s["ename"]] = emsg
                            ex_body(s["ebody"], e2, ux)
                        else:
                            ex_body(s["ebody"], env, ux)
                    finally:
                        _EXC_STACK.pop()
        finally:
            # runs on every exit: normal, handled, abrupt, propagating
            if s["fbody"] is not None:
                if held is not None:
                    _EXC_STACK.append((held.msg, held.line))
                try:
                    ex_body(s["fbody"], env, ux)
                finally:
                    if held is not None:
                        _EXC_STACK.pop()
        if held is not None:
            raise held
        return
    if t == "raise":
        if s["val"] is None:
            if not _EXC_STACK:
                raise HSErr("raise without active exception", ln)
            msg, eline = _EXC_STACK[-1]
            raise HSErr(msg, eline)
        v = s["val"]
        if ux and v["t"] == "str":
            raise HSErr(v["val"], ln)
        v = ev(v, env)
        if not isinstance(v, str):
            raise HSErr("raise wants Str", ln)
        raise HSErr(v, ln)
    if t == "global":
        for n in s["names"]:
            _, found = find_var(n, env)
            if isinstance(found, UnsafeVal):
                raise HSErr(f"cannot declare global for unsafe variable '{n}'", ln)
        env.globals.update(s["names"])
        return
    if t == "return":
        if ux:
            if s["val"] is None:
                raise ReturnExc(None)
            raise ReturnExc(box(*sev(s["val"], env), ln))
        raise ReturnExc(ev(s["val"], env) if s["val"] is not None else None)
    if t == "break":
        raise BreakExc()
    if t == "continue":
        raise ContinueExc()
    if t == "def":
        env.vars[s["name"]] = HSFunc(s["name"], s["params"], s["body"], env, ln)
        return
    if t == "if":
        cond = sev(s["cond"], env)[1] != 0 if ux else ev(s["cond"], env)
        if cond:
            ex_body(s["then"], env, ux)
            return
        for ec, eb in s["elifs"]:
            c = sev(ec, env)[1] != 0 if ux else ev(ec, env)
            if c:
                ex_body(eb, env, ux)
                return
        if s["els"]:
            ex_body(s["els"], env, ux)
        return
    if t == "while":
        while (sev(s["cond"], env)[1] != 0) if ux else ev(s["cond"], env):
            try:
                ex_body(s["body"], env, ux)
            except ContinueExc:
                continue
            except BreakExc:
                break
        return
    if t == "for":
        it = ev(s["iter"], env)
        if isinstance(it, dict):
            seq = list(it.keys())
        elif isinstance(it, (list, str)):
            seq = it
        else:
            raise HSErr(f"not iterable: {tname(it)}", ln)
        for v in seq:
            env.set(s["var"], v)
            try:
                ex_body(s["body"], env, ux)
            except ContinueExc:
                continue
            except BreakExc:
                break
        return
    raise HSErr(f"bad stmt {t}", ln)


# ---------- builtins ----------
def b_print(args, ln):
    sys.stdout.write(" ".join(disp(a) for a in args) + "\n")
    return None


def b_len(args, ln):
    if len(args) != 1:
        raise HSErr(f"len wants 1 arg, got {len(args)}", ln)
    a = args[0]
    if isinstance(a, (str, list, dict)):
        return len(a)
    raise HSErr(f"len of {tname(a)}", ln)


def b_range(args, ln):
    if len(args) == 1 and is_num(args[0]):
        return list(range(int(args[0])))
    if len(args) == 2 and is_num(args[0]) and is_num(args[1]):
        return list(range(int(args[0]), int(args[1])))
    raise HSErr("range wants range(n) or range(a, b) with Ints", ln)


def b_str(args, ln):
    if len(args) != 1:
        raise HSErr(f"str wants 1 arg, got {len(args)}", ln)
    return disp(args[0])


def b_int(args, ln):
    if len(args) != 1:
        raise HSErr(f"int wants 1 arg, got {len(args)}", ln)
    a = args[0]
    if isinstance(a, bool):
        return int(a)
    if isinstance(a, int):
        return a
    if isinstance(a, float):
        return int(a)
    if isinstance(a, str):
        try:
            return int(a.strip(), 0) if a.strip().startswith("0x") or a.strip().startswith("0X") else int(a.strip())
        except ValueError:
            raise HSErr(f"cannot convert {a!r} to Int", ln)
    raise HSErr(f"cannot convert {tname(a)} to Int", ln)


def b_float(args, ln):
    if len(args) != 1:
        raise HSErr(f"float wants 1 arg, got {len(args)}", ln)
    a = args[0]
    if isinstance(a, bool):
        return float(a)
    if isinstance(a, (int, float)):
        return float(a)
    if isinstance(a, str):
        try:
            return float(a.strip())
        except ValueError:
            raise HSErr(f"cannot convert {a!r} to Float", ln)
    raise HSErr(f"cannot convert {tname(a)} to Float", ln)


def b_input(args, ln):
    if args:
        raise HSErr("input takes no args", ln)
    line = sys.stdin.readline()
    if line == "":
        raise HSErr("input: EOF", ln)
    return line.rstrip("\n")


def b_open(args, ln):
    if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], str):
        raise HSErr("open wants open(path, mode)", ln)
    if args[1] not in ("r", "w"):
        raise HSErr('open mode must be "r" or "w"', ln)
    try:
        obj = open(args[0], args[1], encoding="utf-8")
    except OSError as e:
        raise HSErr(f"open failed: {e.strerror or e}", ln)
    return HSFile(obj, args[0], args[1])


def b_read(args, ln):
    if len(args) != 1 or not isinstance(args[0], HSFile):
        raise HSErr("read wants read(f)", ln)
    f = args[0]
    if f.closed:
        raise HSErr("file is closed", ln)
    try:
        return f.obj.read()
    except OSError as e:
        raise HSErr(f"read failed: {e.strerror or e}", ln)


def b_write(args, ln):
    if len(args) != 2 or not isinstance(args[0], HSFile) or not isinstance(args[1], str):
        raise HSErr("write wants write(f, str)", ln)
    f = args[0]
    if f.closed:
        raise HSErr("file is closed", ln)
    try:
        return f.obj.write(args[1])
    except OSError as e:
        raise HSErr(f"write failed: {e.strerror or e}", ln)


def b_close(args, ln):
    if len(args) != 1 or not isinstance(args[0], HSFile):
        raise HSErr("close wants close(f)", ln)
    f = args[0]
    if not f.closed:
        f.obj.close()
        f.closed = True
    return None


def u_int_arg(args, want, ln):
    if len(args) != len(want):
        raise HSErr(f"{want} arg count mismatch", ln)
    out = []
    for a in args:
        if isinstance(a, bool):
            a = int(a)
        if not isinstance(a, int):
            raise HSErr(f"unsafe op needs Int, got {tname(a)}", ln)
        out.append(a)
    return out


def b_alloc(args, ln):
    (n,) = u_int_arg(args, ["n"], ln)
    return us_alloc(n, ln)


def b_load8(args, ln):
    (p,) = u_int_arg(args, ["p"], ln)
    return us_load(p, 1, ln)


def b_load32(args, ln):
    (p,) = u_int_arg(args, ["p"], ln)
    return us_load(p, 4, ln)


def b_load64(args, ln):
    (p,) = u_int_arg(args, ["p"], ln)
    return wrap_i64(us_load(p, 8, ln))


def b_store8(args, ln):
    p, v = u_int_arg(args, ["p", "v"], ln)
    us_store(p, 1, v, ln)
    return v & 0xFF


def b_store32(args, ln):
    p, v = u_int_arg(args, ["p", "v"], ln)
    us_store(p, 4, v, ln)
    return v & 0xFFFFFFFF


def b_store64(args, ln):
    p, v = u_int_arg(args, ["p", "v"], ln)
    us_store(p, 8, v, ln)
    return wrap_i64(v)


def b_as_ptr(args, ln):
    (v,) = u_int_arg(args, ["v"], ln)
    return unbox(v, "Ptr", ln)


def b_as_int(args, ln):
    (v,) = u_int_arg(args, ["v"], ln)
    return v


def b_append(args, ln):
    if len(args) != 2 or not isinstance(args[0], list):
        raise HSErr("append wants append(list, x)", ln)
    args[0].append(args[1])
    return None


def b_split(args, ln):
    if len(args) not in (1, 2) or not isinstance(args[0], str) \
            or (len(args) == 2 and not isinstance(args[1], str)):
        raise HSErr("split wants split(s) or split(s, sep)", ln)
    s = args[0]
    if len(args) == 1:
        return s.split()
    return s.split(args[1])


def b_find(args, ln):
    if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], str):
        raise HSErr("find wants find(s, sub)", ln)
    return args[0].find(args[1])


def b_join(args, ln):
    if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], list):
        raise HSErr("join wants join(sep, list)", ln)
    for x in args[1]:
        if not isinstance(x, str):
            raise HSErr("join needs a list of Str", ln)
    return args[0].join(args[1])


def _fs_args(args, ln, want, n):
    if len(args) != n or not all(isinstance(a, str) for a in args):
        raise HSErr(f"{want}", ln)


def b_read_text(args, ln):
    _fs_args(args, ln, "read_text wants read_text(path)", 1)
    try:
        with open(args[0], encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise HSErr(f"read_text failed: {e.strerror or e}", ln)


def b_read_mem(args, ln):
    # raw bytes -> Str (byte-preserving latin-1). The kernel uses this to
    # read bootloader structures and ramdisk images no allocator owns.
    if len(args) != 2 or not is_int(args[0]) or not is_int(args[1]):
        raise HSErr("read_mem wants read_mem(ptr, nbytes)", ln)
    p, n = args
    if n < 0:
        raise HSErr("read_mem length must be >= 0", ln)
    if n == 0:
        return ""
    us_check(p, n, ln)
    return bytes(US_MEM[p:p + n]).decode("latin-1")


def b_write_text(args, ln):
    if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], str):
        raise HSErr("write_text wants write_text(path, str)", ln)
    try:
        with open(args[0], "w", encoding="utf-8") as f:
            f.write(args[1])
    except OSError as e:
        raise HSErr(f"write_text failed: {e.strerror or e}", ln)
    return None


def b_append_text(args, ln):
    if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], str):
        raise HSErr("append_text wants append_text(path, str)", ln)
    try:
        with open(args[0], "a", encoding="utf-8") as f:
            f.write(args[1])
    except OSError as e:
        raise HSErr(f"append_text failed: {e.strerror or e}", ln)
    return None


def b_exists(args, ln):
    _fs_args(args, ln, "exists wants exists(path)", 1)
    return _os.path.exists(args[0])


def b_ls(args, ln):
    _fs_args(args, ln, "ls wants ls(dir)", 1)
    try:
        return sorted(_os.listdir(args[0]))
    except OSError as e:
        raise HSErr(f"ls failed: {e.strerror or e}", ln)


def b_mkdir(args, ln):
    _fs_args(args, ln, "mkdir wants mkdir(path)", 1)
    try:
        _os.makedirs(args[0], exist_ok=True)
    except OSError as e:
        raise HSErr(f"mkdir failed: {e.strerror or e}", ln)
    return None


def b_json_load(args, ln):
    _fs_args(args, ln, "json_load wants json_load(path)", 1)
    return b_json_parse([b_read_text(args, ln)], ln)


def b_json_save(args, ln):
    if len(args) != 2 or not isinstance(args[0], str):
        raise HSErr("json_save wants json_save(path, x)", ln)
    b_write_text([args[0], b_json_str([args[1]], ln)], ln)
    return None


_JSON_DEPTH = 200


def _json_to_hs(v, ln, depth):
    if depth > _JSON_DEPTH:
        raise HSErr("json too deeply nested", ln)
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, list):
        return [_json_to_hs(x, ln, depth + 1) for x in v]
    if isinstance(v, dict):
        return {k: _json_to_hs(x, ln, depth + 1) for k, x in v.items()}
    raise HSErr("json got an unsupported value", ln)


def b_json_parse(args, ln):
    if len(args) != 1 or not isinstance(args[0], str):
        raise HSErr("json_parse wants json_parse(str)", ln)
    import json as _json
    try:
        v = _json.loads(args[0])
    except _json.JSONDecodeError as e:
        raise HSErr(f"json_parse failed: {e.msg}", ln)
    return _json_to_hs(v, ln, 0)


def _json_from_hs(v, ln, depth):
    if depth > _JSON_DEPTH:
        raise HSErr("json too deeply nested", ln)
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, list):
        return [_json_from_hs(x, ln, depth + 1) for x in v]
    if isinstance(v, dict):
        for k in v:
            if not isinstance(k, str):
                raise HSErr("json_str needs Str keys", ln)
        return {k: _json_from_hs(x, ln, depth + 1) for k, x in v.items()}
    raise HSErr(f"not JSON-serializable: {tname(v)}", ln)


def b_json_str(args, ln):
    if len(args) != 1:
        raise HSErr("json_str wants json_str(x)", ln)
    import json as _json
    v = _json_from_hs(args[0], ln, 0)
    try:
        return _json.dumps(v, allow_nan=False)
    except (ValueError, TypeError) as e:
        raise HSErr(f"json_str failed: {e}", ln)


# kernel-surface builtins with hosted approximations (documented)
import time as _time

_fake_pmm_total = 65536
_fake_pmm_free = 65536
_fake_pmm_next = 0x10000000


def b_ticks(args, ln):
    if args:
        raise HSErr("ticks takes no args", ln)
    return int(_time.monotonic() * 1000)


def b_readkey(args, ln):
    if args:
        raise HSErr("readkey takes no args", ln)
    c = sys.stdin.read(1)
    if c == "":
        return None
    return c


def b_pmm_alloc(args, ln):
    global _fake_pmm_free, _fake_pmm_next
    if len(args) != 1 or not isinstance(args[0], int) or isinstance(args[0], bool) \
            or args[0] < 0:
        raise HSErr("pmm_alloc wants pmm_alloc(npages)", ln)
    n = args[0]
    if n > _fake_pmm_free:
        raise HSErr("pmm_alloc: out of memory", ln)
    addr = _fake_pmm_next
    _fake_pmm_next += n * 4096
    _fake_pmm_free -= n
    return addr


def b_meminfo(args, ln):
    if args:
        raise HSErr("meminfo takes no args", ln)
    return {"total": _fake_pmm_total, "free": _fake_pmm_free, "page": 4096}


def b_argv(args, ln):
    if args:
        raise HSErr("argv takes no args", ln)
    return list(sys.argv[2:])


def b_env(args, ln):
    if len(args) != 1 or not isinstance(args[0], str):
        raise HSErr("env wants env(name)", ln)
    return _os.environ.get(args[0])


def b_system(args, ln):
    if len(args) != 1 or not isinstance(args[0], str):
        raise HSErr("system wants system(cmd)", ln)
    import subprocess
    sys.stdout.flush()
    return subprocess.run(args[0], shell=True).returncode


class HSSock:
    def __init__(self, sock):
        self.sock = sock
        self.closed = False


def _sock_arg(a, ln, what):
    if not isinstance(a, HSSock) or a.closed:
        raise HSErr(f"{what} wants an open socket", ln)
    return a.sock


def b_tcp_connect(args, ln):
    if len(args) != 2 or not isinstance(args[0], str) or not isinstance(args[1], int) \
            or isinstance(args[1], bool):
        raise HSErr("tcp_connect wants tcp_connect(host, port)", ln)
    import socket
    try:
        s = socket.create_connection((args[0], args[1]), timeout=20)
    except OSError as e:
        raise HSErr(f"tcp_connect failed: {e.strerror or e}", ln)
    return HSSock(s)


def b_tcp_send(args, ln):
    if len(args) != 2 or not isinstance(args[1], str):
        raise HSErr("tcp_send wants tcp_send(sock, str)", ln)
    s = _sock_arg(args[0], ln, "tcp_send")
    try:
        return s.sendall(args[1].encode()) or len(args[1].encode())
    except OSError as e:
        raise HSErr(f"tcp_send failed: {e.strerror or e}", ln)


def b_tcp_recv(args, ln):
    if len(args) != 2 or not isinstance(args[1], int) or isinstance(args[1], bool):
        raise HSErr("tcp_recv wants tcp_recv(sock, n)", ln)
    s = _sock_arg(args[0], ln, "tcp_recv")
    try:
        data = s.recv(max(1, args[1]))
    except OSError as e:
        raise HSErr(f"tcp_recv failed: {e.strerror or e}", ln)
    return data.decode("utf-8", errors="replace")


def b_tcp_close(args, ln):
    if len(args) != 1 or not isinstance(args[0], HSSock):
        raise HSErr("tcp_close wants tcp_close(sock)", ln)
    a = args[0]
    if not a.closed:
        try:
            a.sock.close()
        except OSError:
            pass
        a.closed = True
    return None


def b_tcp_listen(args, ln):
    if len(args) != 1 or not isinstance(args[0], int) or isinstance(args[0], bool):
        raise HSErr("tcp_listen wants tcp_listen(port)", ln)
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", args[0]))
        s.listen(8)
    except OSError as e:
        raise HSErr(f"tcp_listen failed: {e.strerror or e}", ln)
    return HSSock(s)


def b_tcp_accept(args, ln):
    if len(args) != 1:
        raise HSErr("tcp_accept wants tcp_accept(sock)", ln)
    s = _sock_arg(args[0], ln, "tcp_accept")
    try:
        c, _ = s.accept()
    except OSError as e:
        raise HSErr(f"tcp_accept failed: {e.strerror or e}", ln)
    return HSSock(c)


def _http_split(url, ln):
    if not url.startswith("http://"):
        raise HSErr("http_get wants an http:// url (no https in v1)", ln)
    rest = url[7:]
    path_i = rest.find("/")
    hostport = rest if path_i < 0 else rest[:path_i]
    path = "/" if path_i < 0 else rest[path_i:]
    if ":" in hostport:
        host, ps = hostport.rsplit(":", 1)
        try:
            port = int(ps)
        except ValueError:
            raise HSErr(f"http_get bad port in url", ln)
    else:
        host, port = hostport, 80
    if not host:
        raise HSErr("http_get bad url", ln)
    return host, port, path


def b_http_get(args, ln):
    if len(args) != 1 or not isinstance(args[0], str):
        raise HSErr("http_get wants http_get(url)", ln)
    host, port, path = _http_split(args[0], ln)
    import socket
    try:
        s = socket.create_connection((host, port), timeout=20)
    except OSError as e:
        raise HSErr(f"http_get connect failed: {e.strerror or e}", ln)
    req = f"GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    try:
        s.sendall(req.encode())
        chunks = []
        while True:
            b = s.recv(65536)
            if not b:
                break
            chunks.append(b)
    except OSError as e:
        raise HSErr(f"http_get failed: {e.strerror or e}", ln)
    finally:
        try:
            s.close()
        except OSError:
            pass
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    try:
        status = int(head.split(b" ", 2)[1])
    except (IndexError, ValueError):
        raise HSErr("http_get got a bad response", ln)
    if not (200 <= status < 300):
        raise HSErr(f"http status {status}", ln)
    return body.decode("utf-8", errors="replace")


BUILTINS = {
    "print": b_print, "len": b_len, "range": b_range, "str": b_str,
    "int": b_int, "float": b_float, "input": b_input, "open": b_open,
    "read": b_read, "write": b_write, "close": b_close,
    "alloc": b_alloc, "load8": b_load8, "load32": b_load32,
    "load64": b_load64,
    "store8": b_store8, "store32": b_store32, "store64": b_store64,
    "as_ptr": b_as_ptr, "as_int": b_as_int,
    "ticks": b_ticks, "readkey": b_readkey,
    "pmm_alloc": b_pmm_alloc, "meminfo": b_meminfo,
    "append": b_append, "split": b_split, "find": b_find, "join": b_join,
    "argv": b_argv, "env": b_env, "system": b_system,
    "tcp_connect": b_tcp_connect, "tcp_send": b_tcp_send,
    "tcp_recv": b_tcp_recv, "tcp_close": b_tcp_close,
    "tcp_listen": b_tcp_listen, "tcp_accept": b_tcp_accept,
    "http_get": b_http_get,
    "json_parse": b_json_parse, "json_str": b_json_str,
    "read_text": b_read_text, "read_mem": b_read_mem,
    "write_text": b_write_text,
    "append_text": b_append_text, "exists": b_exists, "ls": b_ls,
    "mkdir": b_mkdir, "json_load": b_json_load, "json_save": b_json_save,
}


def main():
    global BUILTINS_ENV
    raw = sys.argv[1:]
    as_json = False
    if "--json" in raw:
        as_json = True
        raw = [a for a in raw if a != "--json"]
    if not raw:
        print(f"usage: {sys.argv[0]} [--json] prog.hs [args...]", file=sys.stderr)
        sys.exit(2)
    sys.argv = [sys.argv[0]] + raw
    import json as _json

    def fail(msg, line, extra=None):
        if as_json:
            print(_json.dumps({"file": raw[0], "line": line, "message": msg}),
                  file=sys.stderr)
        else:
            print(f"error: {msg}" + (f" at line {line}" if line else ""), file=sys.stderr)
        sys.exit(1)

    try:
        with open(raw[0], encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        fail(f"cannot read {raw[0]}: {e.strerror or e}", None)
    try:
        prog = parse_program(src)
        BUILTINS_ENV = Env()
        for n, fn in BUILTINS.items():
            BUILTINS_ENV.vars[n] = HSBuiltin(n, fn)
        import os as _os
        main_env = Env(parent=BUILTINS_ENV,
                       basedir=_os.path.dirname(_os.path.abspath(raw[0])))
        main_env.gbase = main_env
        ex_body(prog, main_env)
    except HSErr as e:
        fail(e.msg, e.line)
    except RecursionError:
        fail("recursion too deep", None)


if __name__ == "__main__":
    main()
