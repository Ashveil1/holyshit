#!/usr/bin/env python3
"""Dev-time translator: Python emitter modules (gcrt.py, x64gen.py, irx64.py
style) -> hs. Covers the subset those files use. The output is trusted only
through the byte-identical differential tests; after the first translation
the .holy file is the maintained source.
usage: py2hs.py in.py out.holy [--module NAME] [--asm-methods FILE]"""
import ast
import os
import sys

HS_RESERVED = {"def", "if", "elif", "else", "while", "for", "in", "return",
               "break", "continue", "global", "and", "or", "not", "true",
               "false", "null", "pass", "import", "try", "except", "as",
               "extern", "raise", "lambda", "class", "assert", "module",
               "print", "finally", "unsafe", "self_"}
# hs builtins that a Python local/param name must not shadow
HS_BUILTINS = {"alloc", "append", "append_text", "argv", "as_int", "as_ptr",
               "close", "contains", "env", "exists", "find", "float", "has",
               "http_get", "input", "int", "join", "json_load", "json_parse",
               "json_save", "json_str", "keys", "len", "load32", "load64",
               "load8", "ls", "meminfo", "mkdir", "open", "pmm_alloc",
               "range", "read", "read_mem", "read_text", "readkey", "split",
               "store32", "store64", "store8", "str", "system", "ticks",
               "values", "write", "write_bytes", "write_text"}
BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.BitAnd: "&",
       ast.BitOr: "|", ast.BitXor: "^", ast.LShift: "<<", ast.RShift: ">>"}
CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.Gt: ">",
       ast.LtE: "<=", ast.GtE: ">="}
# Python builtins / methods mapped to pyrt helpers
FUNCS = {"bytes": "py_bytes", "bytearray": "py_bytes", "set": "py_set",
         "sorted": "py_sorted", "enumerate": "py_enumerate",
         "reversed": "py_reversed", "all": "py_all", "any": "py_any",
         "min": "py_min", "max": "py_max", "abs": "py_abs", "list": "py_list",
         "id": "py_id", "getattr": "py_getattr", "hex": "py_hex",
         "ord": "py_ord", "chr": "py_chr", "tuple": "py_list",
         "dict": "py_dict", "isinstance": "py_isinstance", "repr": "py_repr",
         "sum": "py_sum", "zip": "py_zip", "map": "py_map",
         "callable": "py_callable", "hasattr": "py_hasattr"}
METHODS = {"get": "py_get", "setdefault": "py_setdefault", "items": "py_items",
           "add": "py_add", "update": "py_update", "extend": "py_extend",
           "pop": "py_pop", "startswith": "py_startswith",
           "endswith": "py_endswith", "replace": "py_replace",
           "encode": "py_encode", "decode": "py_decode", "index": "py_index",
           "discard": "py_discard", "copy": "py_copy", "insert": "py_insert",
           "strip": "py_strip", "lstrip": "py_lstrip", "rstrip": "py_rstrip",
           "lower": "py_lower", "upper": "py_upper", "count": "py_count",
           "sort": "py_sort", "remove": "py_remove", "clear": "py_clear",
           "isdigit": "py_isdigit", "isalpha": "py_isalpha",
           "format": "py_format", "to_bytes": "py_to_bytes",
           "rsplit": "py_rsplit", "rfind": "py_rfind", "union": "py_union",
           "keys": "py_keys", "values": "py_values", "match": "py_match",
           "isidentifier": "py_isidentifier", "isalnum": "py_isalnum",
           "splitlines": "py_splitlines", "ljust": "py_ljust",
           "partition": "py_partition", "hex": "py_hexm",
           "issubset": "py_issubset", "difference": "py_difference"}
MODFUNCS = {("_st", "pack"): "py_pack", ("_st", "pack_into"): "py_pack_into",
            ("struct", "pack"): "py_pack", ("struct", "unpack"): "py_unpack",
            ("_os", "path"): None}


PAD = {"py_err": 2, "py_get": 3, "py_dict": 1, "py_set": 1, "py_min": 2,
       "py_max": 2, "py_sorted": 2, "py_getattr": 3, "py_encode": 2,
       "py_bytes": 1, "py_list": 1, "py_split": 2, "py_sort": 2}


def padded(name, args):
    n = PAD.get(name)
    if n is None:
        return name + "(" + ", ".join(args) + ")"
    args = list(args)
    while len(args) < n:
        args.append("null")
    return name + "(" + ", ".join(args) + ")"


class Unsupported(Exception):
    pass


class T:
    def __init__(self, asm_methods, sigs):
        self.out = []
        self.asm_methods = asm_methods
        self.sigs = sigs            # func/method name -> [param names]
        self.alias = {}             # local alias of an asm method
        self.lam = 0
        self.warn = []
        self.cls = None
        self.fails = []
        self.pending = []
        self.curfn = None
        self.hoisted = []
        self.hoisted_consts = []
        self.consts = {}   # class -> constant names
        self.defaults = {}  # method name -> [default expr or None]
        self.allconsts = {}
        self.cmap = set()

    def w(self, ind, s):
        for ln in self.pending:
            self.out.append("  " * ind + ln)
        self.pending = []
        self.out.append("  " * ind + s)

    def nm(self, n):
        if n in HS_RESERVED or n in HS_BUILTINS:
            return n + "_"
        return n

    # ---- expressions ----
    def s(self, v):
        r = repr(v) if False else None
        out = ['"']
        for ch in v:
            o = ord(ch)
            if ch == "\\":
                out.append("\\\\")
            elif ch == '"':
                out.append('\\"')
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\t":
                out.append("\\t")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\0":
                out.append("\\0")
            elif o < 32 or o == 127:
                out.append("\" + py_chr(%d) + \"" % o)
            else:
                out.append(ch)
        out.append('"')
        return "".join(out)

    def isasm(self, f):
        return isinstance(f, ast.Attribute) and f.attr in self.asm_methods \
            and not (isinstance(f.value, ast.Name) and f.value.id in ("self", "Gen"))

    def e(self, x):
        t = type(x)
        if t is ast.Constant:
            v = x.value
            if isinstance(v, bool):
                return "true" if v else "false"
            if v is None:
                return "null"
            if isinstance(v, str):
                return self.s(v)
            if isinstance(v, bytes):
                return "[" + ", ".join(str(b) for b in v) + "]"
            if isinstance(v, float):
                return repr(v)
            if isinstance(v, int):
                if 2 ** 63 <= v < 2 ** 64:
                    v -= 2 ** 64
                return str(v) if v >= 0 else "(0 - %d)" % -v
            raise Unsupported(repr(v))
        if t is ast.Name:
            if x.id in self.alias:
                return self.alias[x.id]
            if x.id == "None":
                return "null"
            return self.nm(x.id)
        if t is ast.Attribute:
            if x.attr in ("code", "labels", "data", "data_labels", "fixups") and self.isasmobj(x.value):
                return 'asm.state()["%s"]' % x.attr
            if isinstance(x.value, ast.Name) and x.value.id in ("Gen", "GenIR", "self", "cls") \
                    and x.attr in self.allconsts and not (x.value.id == "self" and x.attr in self.sigs):
                return self.constname(x.value.id, x.attr)
            if isinstance(x.value, ast.Name) and x.value.id == "Gen" and x.attr == "Scope":
                return "Gen_Scope"
            return self.e(x.value) + "." + self.nm(x.attr)
        if t is ast.Call:
            return self.call(x)
        if t is ast.UnaryOp:
            if isinstance(x.op, ast.USub):
                if isinstance(x.operand, ast.Constant):
                    return "(0 - %s)" % self.e(x.operand)
                return "(0 - %s)" % self.e(x.operand)
            if isinstance(x.op, ast.Not):
                return "(not %s)" % self.e(x.operand)
            if isinstance(x.op, ast.Invert):
                return "(~%s)" % self.e(x.operand)
            if isinstance(x.op, ast.UAdd):
                return self.e(x.operand)
        if t is ast.BinOp:
            op = type(x.op)
            if op is ast.Mult and (self.seqish(x.left) or self.seqish(x.right)):
                return "py_rep(%s, %s)" % (self.e(x.left), self.e(x.right))
            if op is ast.BitAnd and self.is_mask64(x.right):
                return self.e(x.left)
            if op is ast.BitOr and (self.setish(x.left) or self.setish(x.right)):
                return "py_union(%s, %s)" % (self.e(x.left), self.e(x.right))
            if op in BIN:
                if op is ast.Add and (isinstance(x.left, ast.Constant) and isinstance(x.left.value, bytes)):
                    pass
                return "(%s %s %s)" % (self.e(x.left), BIN[op], self.e(x.right))
            if op is ast.FloorDiv:
                return "py_floordiv(%s, %s)" % (self.e(x.left), self.e(x.right))
            if op is ast.Mod:
                if isinstance(x.left, ast.Constant) and isinstance(x.left.value, str):
                    return "py_percent(%s, %s)" % (self.e(x.left), self.e(x.right))
                return "(%s %% %s)" % (self.e(x.left), self.e(x.right))
            if op is ast.Pow:
                return "py_pow(%s, %s)" % (self.e(x.left), self.e(x.right))
            raise Unsupported(op.__name__)
        if t is ast.BoolOp:
            j = " and " if isinstance(x.op, ast.And) else " or "
            return "(" + j.join(self.e(v) for v in x.values) + ")"
        if t is ast.Compare:
            parts = []
            left = x.left
            for op, right in zip(x.ops, x.comparators):
                parts.append(self.cmp(left, op, right))
                left = right
            return parts[0] if len(parts) == 1 else "(" + " and ".join(parts) + ")"
        if t is ast.IfExp:
            return "(%s if %s else %s)" % (self.e(x.body), self.e(x.test), self.e(x.orelse))
        if t is ast.Subscript:
            sl = x.slice
            if isinstance(sl, ast.Slice):
                lo = self.e(sl.lower) if sl.lower else "0"
                if sl.upper:
                    hi = self.e(sl.upper)
                    return "%s[%s:%s]" % (self.e(x.value), lo, hi)
                return "py_tail(%s, %s)" % (self.e(x.value), lo)
            if isinstance(sl, ast.Tuple):
                return "%s[%s]" % (self.e(x.value), self.key(sl))
            return "%s[%s]" % (self.e(x.value), self.e(sl))
        if t is ast.Tuple or t is ast.List:
            return "[" + ", ".join(self.e(v) for v in x.elts) + "]"
        if t is ast.Set:
            return "py_set([" + ", ".join(self.e(v) for v in x.elts) + "])"
        if t is ast.Dict:
            items = []
            for k, v in zip(x.keys, x.values):
                if k is None:
                    raise Unsupported("dict **")
                items.append(self.key(k) + ": " + self.e(v))
            return "{" + ", ".join(items) + "}"
        if t is ast.JoinedStr:
            return self.fstr(x)
        if t is ast.NamedExpr:
            self.pending.append("%s = %s" % (self.nm(x.target.id), self.e(x.value)))
            return self.nm(x.target.id)
        if t is ast.Lambda:
            return "(lambda %s: %s)" % (", ".join(self.nm(a.arg) for a in x.args.args), self.e(x.body))
        if t is ast.ListComp or t is ast.GeneratorExp:
            return "[" + self.comp(x.elt, x.generators) + "]"
        if t is ast.SetComp:
            return "py_set([" + self.comp(x.elt, x.generators) + "])"
        if t is ast.DictComp:
            return "py_dict([" + self.comp(ast.List(elts=[x.key, x.value], ctx=ast.Load()), x.generators) + "])"
        raise Unsupported(t.__name__)

    def constname(self, owner, attr):
        c = self.cls if owner in ("self", "cls") else owner
        for cand in (c, "Gen"):
            if (cand, attr) in self.cmap:
                return cand + "_" + attr
        return self.allconsts[attr]

    def keyused(self, name):
        if self.curfn is None:
            return False
        for n in ast.walk(self.curfn):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Name) and n.slice.id == name:
                return True
            if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == name \
                    and isinstance(n.ops[0], (ast.In, ast.NotIn)):
                return True
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("get", "setdefault", "pop", "add", "discard") \
                    and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == name:
                return True
        return False

    def seqish(self, x):
        return isinstance(x, (ast.List, ast.Tuple)) or (isinstance(x, ast.Constant) and isinstance(x.value, (bytes, str)))

    def is_mask64(self, x):
        try:
            return eval(compile(ast.Expression(x), "m", "eval")) == 2 ** 64 - 1
        except Exception:
            return False

    def setish(self, x):
        if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "set":
            return True
        if isinstance(x, ast.Name) and x.id.isupper() and len(x.id) > 2:
            return True
        if isinstance(x, ast.Attribute) and x.attr.isupper() and len(x.attr) > 2:
            return True
        if isinstance(x, ast.BinOp) and isinstance(x.op, ast.BitOr):
            return self.setish(x.left) or self.setish(x.right)
        return False

    def key(self, k):
        # tuple dict keys become "a|b" strings via py_key
        if isinstance(k, ast.Tuple):
            return "py_key([" + ", ".join(self.e(v) for v in k.elts) + "])"
        return self.e(k)

    def isasmobj(self, v):
        if isinstance(v, ast.Name):
            return v.id in ("a", "b", "asm")
        return isinstance(v, ast.Attribute) and v.attr == "a"

    def comp(self, elt, gens):
        saved = dict(self.alias)
        clauses = []
        for gi, g in enumerate(gens):
            tgt = g.target
            it = self.e(g.iter)
            if isinstance(tgt, ast.Tuple):
                if not all(isinstance(t, ast.Name) for t in tgt.elts):
                    raise Unsupported("nested comp target")
                pv = "_p%d_%d" % (len(self.out), gi)
                for i, t in enumerate(tgt.elts):
                    self.alias[t.id] = "%s[%d]" % (pv, i)
                nm = pv
            else:
                nm = self.nm(tgt.id)
                self.alias.pop(tgt.id, None)
            cl = " for %s in %s" % (nm, it)
            for c in g.ifs:
                cl += " if " + self.e(c)
            clauses.append(cl)
        body = self.e(elt)
        self.alias = saved
        return body + "".join(clauses)

    def cmp(self, l, op, r):
        if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(r, ast.Constant) \
                and isinstance(r.value, bool):
            le = self.e(l)
            t = "(py_type(%s) == \"bool\" and %s == %s)" % (
                le, le, "true" if r.value else "false")
            return t if isinstance(op, ast.Is) else "(not %s)" % t
        if isinstance(op, (ast.Is, ast.Eq)):
            return "(%s == %s)" % (self.e(l), self.e(r))
        if isinstance(op, (ast.IsNot, ast.NotEq)):
            return "(%s != %s)" % (self.e(l), self.e(r))
        if isinstance(op, ast.In):
            return "(%s in %s)" % (self.keyexpr(l), self.e(r))
        if isinstance(op, ast.NotIn):
            return "(not (%s in %s))" % (self.keyexpr(l), self.e(r))
        return "(%s %s %s)" % (self.e(l), CMP[type(op)], self.e(r))

    def keyexpr(self, l):
        return self.key(l)

    def fstr(self, x):
        parts = []
        for v in x.values:
            if isinstance(v, ast.Constant):
                parts.append(self.s(v.value))
            else:
                spec = v.format_spec
                inner = self.e(v.value)
                if v.conversion == 114:
                    inner = "py_repr(%s)" % inner
                if spec is None:
                    parts.append("str(%s)" % inner)
                else:
                    sp = "".join(p.value for p in spec.values)
                    parts.append("py_fmt(%s, %s)" % (inner, self.s(sp)))
        return "(" + " + ".join(parts) + ")" if parts else '""'

    def argv_list(self, call, sig):
        a = self.args(call, sig)
        # count top-level args
        depth = 0
        n = 1 if a.strip() else 0
        instr = False
        i = 0
        while i < len(a):
            c = a[i]
            if instr:
                if c == "\\":
                    i += 1
                elif c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == "," and depth == 0:
                n += 1
            i += 1
        return [None] * n

    def args(self, call, sig=None):
        out = [self.e(a) for a in call.args]
        call = ast.Call(func=call.func, args=call.args,
                        keywords=[k for k in call.keywords if k.arg not in ("encoding", "file")])
        if call.keywords:
            if sig is None:
                raise Unsupported("kwargs without signature: " + ast.unparse(call)[:60])
            pos = list(out)
            names = sig[len(call.args):]
            kw = {k.arg: self.e(k.value) for k in call.keywords}
            # fill remaining params in order up to the last given keyword
            last = max(names.index(k) for k in kw) if kw else -1
            for nme in names[:last + 1]:
                if nme in kw:
                    pos.append(kw[nme])
                else:
                    pos.append("null")  # skipped parameter: its default is None
            out = pos
        return ", ".join(out)

    def recv(self, v):
        r = self.e(v)
        if isinstance(v, (ast.Name, ast.Attribute)) or (isinstance(v, ast.Subscript) and False):
            return r
        self.tmpn = getattr(self, "tmpn", 0) + 1
        nm = "_r%d" % self.tmpn
        self.pending.append("%s = %s" % (nm, r))
        return nm

    def call(self, x):
        f = x.func
        if isinstance(f, ast.Name):
            n = f.id
            if n in self.alias:
                return self.alias[n] + "(" + self.args(x) + ")"
            if n == "print":
                return "py_print([" + self.args(x) + "])"
            if n == "isinstance" and len(x.args) == 2:
                tn = x.args[1]
                names = [t.id for t in (tn.elts if isinstance(tn, ast.Tuple) else [tn])]
                return "py_isinstance(%s, [%s])" % (self.e(x.args[0]), ", ".join('"%s"' % t for t in names))
            if n in FUNCS and n not in self.sigs:
                pos = [self.e(a) for a in x.args] + [self.e(k.value) for k in x.keywords if k.arg not in ("file",)]
                return padded(FUNCS[n], pos)
            if n == "HSErr":
                return padded("py_err", [self.e(a) for a in x.args])
            if n in ("len", "range"):
                return n + "(" + self.args(x) + ")"
            if n in ("str", "int", "float"):
                return n + "(" + self.args(x) + ")"
            return self.nm(n) + "(" + self.args(x, self.sigs.get(n)) + ")"
        if isinstance(f, ast.Attribute):
            at = f.attr
            if isinstance(f.value, ast.Name) and (f.value.id, at) in MODFUNCS and MODFUNCS[(f.value.id, at)]:
                return MODFUNCS[(f.value.id, at)] + "(" + self.args(x) + ")"
            if isinstance(f.value, ast.Name) and f.value.id in ("_os", "os", "_sys", "sys", "_re", "re"):
                return "py_%s_%s(%s)" % (f.value.id.strip("_"), at, self.args(x))
            if isinstance(f.value, ast.Attribute) and isinstance(f.value.value, ast.Name) \
                    and f.value.value.id in ("_os", "os") and f.value.attr == "path":
                return "py_os_path_%s(%s)" % (at, self.args(x))
            if isinstance(f.value, ast.Name) and f.value.id == "Gen" and at == "Scope":
                a = [p for p in self.args(x, self.sigs.get("Scope.__init__")).split(", ") if p]
                a += ["null", "false"][len(a):]
                return "Gen_Scope(" + ", ".join(a) + ")"
            if isinstance(f.value, ast.Name) and at == "__init__":
                rest = self.args(ast.Call(func=x.func, args=x.args[1:], keywords=x.keywords), self.sigs.get(f.value.id + ".__init__"))
                return "%s__init__(%s%s)" % (f.value.id, self.e(x.args[0]), (", " + rest) if rest else "")
            if at == "__contains__":
                return "(%s in %s)" % (self.key(x.args[0]), self.e(f.value))
            if self.isasm(f):
                if at == "lea_m" and len(x.args) == 5:
                    d, b, disp, ix, sc = [self.e(y) for y in x.args]
                    return "asm.lea_mx(%s, %s, %s, %s, %s)" % (d, b, ix, sc, disp)
                if at == "resolve" and len(x.args) == 2:
                    at = "resolve_at"
                return "asm." + at + "(" + self.args(x, self.sigs.get("asm." + at)) + ")"
            if isinstance(f.value, ast.Name) and f.value.id == "self" or at in self.sigs and at not in METHODS:
                a = self.args(x, self.sigs.get(at))
                dfl = self.defaults.get(at)
                if dfl is not None:
                    have = len(x.args) + (len(x.keywords) and 0)
                    cnt = len(a.split(", ")) if a else 0
                    cnt = len([1 for _ in x.args]) + 0
                    try:
                        n_have = len(self.argv_list(x, self.sigs.get(at)))
                    except Unsupported:
                        n_have = cnt
                    pad = dfl[n_have:]
                    if pad and all(d is not None for d in pad):
                        a = (a + ", " if a else "") + ", ".join(pad)
                return self.recv(f.value) + "." + self.nm(at) + "(" + a + ")"
            if at == "append" and len(x.args) == 1:
                return "append(%s, %s)" % (self.e(f.value), self.e(x.args[0]))
            if at == "split":
                return padded("py_split", [self.e(f.value)] + [self.e(a) for a in x.args])
            if at == "join":
                return "py_join(%s, %s)" % (self.e(f.value), self.args(x))
            if at == "find":
                return "py_find(%s, %s)" % (self.e(f.value), self.args(x))
            if at in METHODS:
                return padded(METHODS[at], [self.e(f.value)] + [self.e(a) for a in x.args])
            return self.recv(f.value) + "." + self.nm(at) + "(" + self.args(x, self.sigs.get(at)) + ")"
        return self.e(f) + "(" + self.args(x) + ")"

    # ---- statements ----
    def body(self, stmts, ind):
        n0 = len(self.out)
        for s in stmts:
            self.st(s, ind)
        if len(self.out) == n0:
            self.w(ind, "pass")

    def target(self, tg):
        if isinstance(tg, ast.Name):
            return self.nm(tg.id)
        if isinstance(tg, ast.Subscript):
            return "%s[%s]" % (self.e(tg.value), self.key(tg.slice) if isinstance(tg.slice, ast.Tuple) else self.e(tg.slice))
        if isinstance(tg, ast.Attribute):
            return self.e(tg)
        raise Unsupported("target " + type(tg).__name__)

    def st(self, s, ind):
        t = type(s)
        if t is ast.FunctionDef:
            ps = []
            defs = s.args.defaults
            nd = len(s.args.args) - len(defs)
            inclass = bool(s.args.args) and s.args.args[0].arg == "self"
            for i, a in enumerate(s.args.args):
                p = self.nm(a.arg)
                if i >= nd and not inclass:
                    p += "=" + self.e(defs[i - nd])
                ps.append(p)
            self.w(ind, "def %s(%s):" % (s.name, ", ".join(ps)))
            prev = self.curfn
            self.curfn = s
            self.body(s.body, ind + 1)
            self.curfn = prev
            return
        if t is ast.ClassDef:
            base = "(" + s.bases[0].id + ")" if s.bases else ""
            nested = [m for m in s.body if isinstance(m, ast.ClassDef)]
            consts = [m for m in s.body if isinstance(m, ast.Assign)]
            s = ast.ClassDef(name=s.name, bases=s.bases, keywords=[], decorator_list=[],
                             body=[m for m in s.body if isinstance(m, ast.FunctionDef)])
            for c in nested:
                c2 = ast.ClassDef(name=s.name + "_" + c.name, bases=c.bases, keywords=[],
                                  decorator_list=[], body=c.body)
                self.hoisted.append(c2)
            for c in consts:
                self.hoisted_consts.append(c)
            self.w(ind, "class %s%s:" % (s.name, base))
            self.cls = s.name
            n0 = len(self.out)
            for m in s.body:
                mark = len(self.out)
                try:
                    self.st(m, ind + 1)
                except (Unsupported, KeyError, AttributeError) as ex:
                    del self.out[mark:]
                    self.fails.append("%s.%s:%d %s" % (s.name, getattr(m, "name", "?"), m.lineno, ex))
                    if isinstance(m, ast.FunctionDef):
                        self.w(ind + 1, "def %s(%s):" % (m.name, ", ".join(a.arg for a in m.args.args)))
                        self.w(ind + 2, "raise \"untranslated %s\"" % m.name)
            if len(self.out) == n0:
                self.w(ind + 1, "pass")
            return
        if t is ast.Expr and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Attribute):
            f = s.value.func
            if f.attr == "pop" and not s.value.args and isinstance(f.value, (ast.Name, ast.Attribute)):
                r = self.e(f.value)
                self.w(ind, "%s = %s[0:(len(%s) - 1)]" % (r, r, r))
                return
            if f.attr == "pop" and len(s.value.args) == 2 and isinstance(f.value, (ast.Name, ast.Attribute, ast.Call)):
                self.w(ind, "%s[%s] = null" % (self.recv(f.value), self.key(s.value.args[0])))
                return
            if f.attr == "discard" and len(s.value.args) == 1:
                self.w(ind, "%s[%s] = false" % (self.recv(f.value), self.key(s.value.args[0])))
                return
        if t is ast.Expr:
            if isinstance(s.value, ast.Constant):
                return
            self.w(ind, self.e(s.value))
            return
        if t is ast.Return:
            self.w(ind, "return " + (self.e(s.value) if s.value else "null"))
            return
        if t is ast.Pass:
            self.w(ind, "pass")
            return
        if t is ast.Break:
            self.w(ind, "break")
            return
        if t is ast.Continue:
            self.w(ind, "continue")
            return
        if t is ast.Assert:
            self.w(ind, "py_assert(%s)" % self.e(s.test))
            return
        if t is ast.Raise:
            if s.exc is None:
                self.w(ind, "raise")
            else:
                self.w(ind, "raise " + self.e(s.exc))
            return
        if t is ast.Delete:
            for tg in s.targets:
                self.w(ind, "%s[%s] = null" % (self.e(tg.value), self.key(tg.slice)))
            return
        if t is ast.Import or t is ast.ImportFrom:
            return
        if t is ast.AugAssign:
            op = type(s.op)
            tg = self.target(s.target)
            if isinstance(s.target, ast.Attribute) and s.target.attr == "code" and self.isasmobj(s.target.value):
                self.w(ind, "py_extend(asm.state()[\"code\"], %s)" % self.e(s.value))
                return
            if op in BIN:
                self.w(ind, "%s = %s %s %s" % (tg, tg, BIN[op], self.e(s.value)))
            elif op is ast.FloorDiv:
                self.w(ind, "%s = py_floordiv(%s, %s)" % (tg, tg, self.e(s.value)))
            elif op is ast.Mod:
                self.w(ind, "%s = %s %% %s" % (tg, tg, self.e(s.value)))
            else:
                raise Unsupported("augassign " + op.__name__)
            return
        if t is ast.Assign and len(s.targets) > 1:
            first = s.targets[0]
            self.st(ast.Assign(targets=[s.targets[-1]], value=s.value), ind)
            for extra in s.targets[:-1]:
                self.st(ast.Assign(targets=[extra], value=s.targets[-1]), ind)
            return
        if t is ast.Assign:
            tg = s.targets[0]
            v = s.value
            if isinstance(tg, ast.Name) and self.isasm(v) and not isinstance(v, ast.Call):
                self.alias[tg.id] = "asm." + v.attr
                return
            if isinstance(tg, ast.Name) and isinstance(v, ast.Attribute) and v.attr == "a" \
                    and isinstance(v.value, ast.Name) and v.value.id in ("self", "g"):
                return  # `a = self.a`: the assembler is the asm module
            if isinstance(tg, ast.Attribute) and tg.attr == "a" and isinstance(v, ast.Call) \
                    and isinstance(v.func, ast.Name) and v.func.id == "Asm":
                self.w(ind, "asm.reset()")
                self.w(ind, "asm.data_reset()")
                return
            if isinstance(tg, ast.Tuple):
                if isinstance(v, ast.Tuple) and len(v.elts) == len(tg.elts):
                    tmp = "_t%d" % len(self.out)
                    self.w(ind, "%s = %s" % (tmp, self.e(v)))
                else:
                    tmp = "_t%d" % len(self.out)
                    self.w(ind, "%s = %s" % (tmp, self.e(v)))
                for i, el in enumerate(tg.elts):
                    self.w(ind, "%s = %s[%d]" % (self.target(el), tmp, i))
                return
            if isinstance(tg, ast.Name) and isinstance(v, ast.Tuple) and self.keyused(tg.id):
                self.w(ind, "%s = py_key(%s)" % (self.nm(tg.id), self.e(v)))
                return
            self.w(ind, "%s = %s" % (self.target(tg), self.e(v)))
            return
        if t is ast.If:
            self.w(ind, "if %s:" % self.e(s.test))
            self.body(s.body, ind + 1)
            orelse = s.orelse
            while orelse:
                if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                    self.w(ind, "elif %s:" % self.e(orelse[0].test))
                    self.body(orelse[0].body, ind + 1)
                    orelse = orelse[0].orelse
                else:
                    self.w(ind, "else:")
                    self.body(orelse, ind + 1)
                    break
            return
        if t is ast.While:
            self.w(ind, "while %s:" % self.e(s.test))
            self.body(s.body, ind + 1)
            return
        if t is ast.For:
            tgt = s.target
            pre = []
            if isinstance(tgt, ast.Tuple):
                names = []
                for i, x in enumerate(tgt.elts):
                    if isinstance(x, ast.Name):
                        names.append(self.nm(x.id))
                    else:
                        tmpn = "_f%d_%d" % (len(self.out), i)
                        names.append(tmpn)
                        pre.append((x, tmpn))
                nm = ", ".join(names)
            elif isinstance(tgt, ast.Name):
                nm = self.nm(tgt.id)
            else:
                raise Unsupported("for target")
            it = s.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                its = "range(" + self.args(it) + ")"
            else:
                its = self.e(it)
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr == "items":
                    its = self.e(it)
            self.w(ind, "for %s in %s:" % (nm, its))
            for x, tmpn in pre:
                for j, el in enumerate(x.elts):
                    if not isinstance(el, ast.Name):
                        raise Unsupported("deep for target")
                    self.w(ind + 1, "%s = %s[%d]" % (self.nm(el.id), tmpn, j))
            self.body(s.body, ind + 1)
            return
        if t is ast.Try:
            self.w(ind, "try:")
            self.body(s.body, ind + 1)
            for h in s.handlers:
                self.w(ind, "except as %s:" % (self.nm(h.name) if h.name else "_e"))
                self.body(h.body, ind + 1)
            if s.finalbody:
                self.w(ind, "finally:")
                self.body(s.finalbody, ind + 1)
            return
        if t is ast.With:
            it = s.items[0]
            if isinstance(it.context_expr, ast.Call) and isinstance(it.context_expr.func, ast.Name) \
                    and it.context_expr.func.id == "open":
                nm = self.nm(it.optional_vars.id)
                self.w(ind, "%s = py_open(%s)" % (nm, self.args(it.context_expr)))
                self.body(s.body, ind)
                self.w(ind, "py_close(%s)" % nm)
                return
        raise Unsupported(t.__name__ + " line %d" % getattr(s, "lineno", 0))


def collect_sigs(trees):
    sigs = {}
    for tree in trees:
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef):
                ps = [a.arg for a in n.args.args if a.arg != "self"]
                sigs[n.name] = ps
            if isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, ast.FunctionDef):
                        sigs[n.name + "." + m.name] = [a.arg for a in m.args.args if a.arg != "self"]
    return sigs


def asm_method_names(path):
    t = ast.parse(open(path).read())
    out = set()
    for n in t.body:
        if isinstance(n, ast.ClassDef) and n.name == "Asm":
            for m in n.body:
                if isinstance(m, ast.FunctionDef) and not m.name.startswith("_"):
                    out.add(m.name)
    return out


def translate(srcs, dst, asm_path):
    tree = ast.Module(body=[], type_ignores=[])
    for src in srcs:
        tree.body.extend(ast.parse(open(src).read()).body)
    asm_m = asm_method_names(asm_path)
    sigs = collect_sigs([tree])
    # asm method signatures: keywords to asm calls
    at = ast.parse(open(asm_path).read())
    for n in at.body:
        if isinstance(n, ast.ClassDef) and n.name == "Asm":
            for m in n.body:
                if isinstance(m, ast.FunctionDef):
                    sigs["asm." + m.name] = [a.arg for a in m.args.args if a.arg != "self"]
    t = T(asm_m, sigs)
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.args.args and n.args.args[0].arg == "self" and n.args.defaults:
            nd = len(n.args.args) - len(n.args.defaults) - 1
            dl = [None] * nd + [t.e(d) for d in n.args.defaults]
            t.defaults[n.name] = dl
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, ast.Assign):
                    names = []
                    tg = m.targets[0]
                    for x in (tg.elts if isinstance(tg, ast.Tuple) else [tg]):
                        names.append(x.id)
                    for nme in names:
                        t.allconsts[nme] = n.name + "_" + nme
                        t.cmap.add((n.name, nme))
    errs = []
    for s in tree.body:
        mark = len(t.out)
        try:
            if isinstance(s, ast.Assign):
                t.w(0, "%s = %s" % (t.target(s.targets[0]), t.e(s.value)))
            elif isinstance(s, (ast.Import, ast.ImportFrom, ast.Expr)):
                continue
            elif isinstance(s, ast.If) and "__name__" in ast.dump(s.test):
                continue
            else:
                t.st(s, 0)
            t.w(0, "")
            while t.hoisted or t.hoisted_consts:
                hc, t.hoisted_consts = t.hoisted_consts, []
                hh, t.hoisted = t.hoisted, []
                owner = s.name if isinstance(s, ast.ClassDef) else ""
                for c in hc:
                    tg = c.targets[0]
                    names = [x.id for x in tg.elts] if isinstance(tg, ast.Tuple) else [tg.id]
                    val = t.e(c.value)
                    if isinstance(tg, ast.Tuple):
                        tmp = "_c_" + owner + "_" + names[0]
                        t.w(0, "%s = %s" % (tmp, val))
                        for i, nme in enumerate(names):
                            t.w(0, "%s_%s = %s[%d]" % (owner, nme, tmp, i))
                    else:
                        t.w(0, "%s_%s = %s" % (owner, names[0], val))
                    t.w(0, "")
                for c in hh:
                    t.cls = c.name
                    t.st(c, 0)
                    t.w(0, "")
        except (Unsupported, KeyError, AttributeError) as ex:
            del t.out[mark:]
            errs.append("%s:%d %s" % (type(s).__name__, getattr(s, "lineno", 0), ex))
    open(dst, "w").write("\n".join(t.out) + "\n")
    return errs + t.fails


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    errs = translate(sys.argv[1].split(","), sys.argv[2], os.path.join(here, "..", "x64.py"))
    for e in errs:
        print("UNSUPPORTED", e)
