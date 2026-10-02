#!/usr/bin/env python3
"""x64gen: holyshit subset -> x86-64 machine code (no gcc/as/ld/libc).

Subset (compile error otherwise): Int values, Str literals (print only),
def/call/recursion (closures supported via caps), if/while/for/break/continue,
try/except/finally is BANNED, modules/import, unsafe I64/U64/Ptr + structs,
print/int()/argv(), no Float/List/Dict/extern/slice/attr.
`/` is truncating int division (differs from main backends: documented).

Values are tagged with the low 2 bits (see TAG_* below):
  00 heap object ptr (8-aligned) | 01 Int (62-bit payload, value = word >> 2)
  10 Bool: 0x02 false, 0x0A true | 11 Null 0x03 / Unbound 0x0B
  Heap obj: [kind:u64][payload...]; kind 0 = Str{len,bytes}, 1 = Func{code,caps}.
  GC: bump-only arena (grows, never frees) -- documented.
"""
import sys

import interp
from interp import HSErr
from x64 import Asm

SUBSET_ERR = "x64 backend subset"


class Gen:
    def __init__(self, prog, main_path="<main>", freestanding=False):
        self.prog = prog
        self.main_path = main_path
        self.freestanding = freestanding
        self.a = Asm()
        self.modules = []
        self.mod_by_path = {}
        self.funcs = []  # (node, fscope, label)
        self.strs = {}  # literal -> ro label
        self.ro = bytearray()
        self.tmpn = 0
        self.loop_stack = []  # (break_label, cont_label)
        self.try_n = 0
        self.reads = []  # (scope, name) var reads for capture analysis
        self.all_fs = []  # function scopes in scan order
        self.flabels = {}  # id(fs) -> code label

    # ----- modules -----
    def load_module(self, name, from_dir, line):
        import os as _os
        if not __import__("re").match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$", name):
            raise HSErr(f"bad module name '{name}'", line)
        hspath = [d for d in _os.environ.get("HSPATH", "").split(":") if d]
        rel = name.replace(".", "/") + ".hs"
        for d in [from_dir] + hspath + [_os.getcwd()]:
            if not d:
                continue
            p = _os.path.abspath(_os.path.join(d, rel))
            if _os.path.isfile(p):
                break
        else:
            raise HSErr(f"cannot find module '{name}'", line)
        if p in self.mod_by_path:
            return self.mod_by_path[p]
        with open(p, encoding="utf-8") as f:
            src = f.read()
        try:
            prog = interp.parse_program(src)
        except HSErr as e:
            raise HSErr(f"in module '{name}': {e.msg}", e.line)
        mod = {"name": name, "prog": prog, "dir": _os.path.dirname(p),
               "pfx": f"m{len(self.modules)}_"}
        self.modules.append(mod)
        self.mod_by_path[p] = mod
        return mod

    # ----- scopes -----
    # ----- value representation (low 2 bits are the tag) -----
    TAG_HEAP, TAG_INT, TAG_BOOL, TAG_NULL = 0, 1, 2, 3
    HS_FALSE, HS_TRUE, HS_NULL, HS_UNBOUND = 0x02, 0x0A, 0x03, 0x0B
    K_STR, K_FUNC = 0, 1

    class Scope:
        def __init__(self, parent=None, is_func=False):
            self.parent = parent
            self.is_func = is_func
            self.params = []
            self.loc = {}  # dynamic name -> rbp offset (negative)
            self.uloc = {}  # unsafe static name -> rbp offset (negative)
            self.utypes = {}  # unsafe static name -> I64/U64/Ptr/Ptr:X
            self.globs = set()  # names declared global here
            self.nloc = 0

    def slot(self, sc):
        sc.nloc += 1
        return -8 * sc.nloc

    def collect(self, body, sc):
        for s in body:
            t = s["t"]
            if t == "def":
                self.decl(sc, s["name"])
                fs = Gen.Scope(parent=sc, is_func=True)
                fs.params = list(s["params"])
                for i, pn in enumerate(fs.params):
                    # [rbp+16] holds the func struct (all calls are indirect);
                    # args start at [rbp+24]
                    fs.loc[pn] = 24 + 8 * i
                self.all_fs.append(fs)
                self.collect(s["body"], fs)
                s["_fs"] = fs
            elif t == "set":
                self.ann_expr(s["val"], sc)
                self.decl(sc, s["name"])
            elif t == "for":
                raise HSErr("for not in x64 subset (use while)", s["line"])
            elif t == "try":
                raise HSErr("try not in x64 subset", s["line"])
            elif t == "if":
                self.ann_expr(s["cond"], sc)
                self.collect(s["then"], sc)
                for ec, eb in s["elifs"]:
                    self.ann_expr(ec, sc)
                    self.collect(eb, sc)
                self.collect(s["els"], sc)
            elif t == "while":
                self.ann_expr(s["cond"], sc)
                self.collect(s["body"], sc)
            elif t == "unsafe":
                self.collect_unsafe(s["body"], sc)
            elif t == "import":
                raise HSErr("import not in x64 subset yet (single file for now)", s["line"])
            elif t == "return":
                if s["val"] is not None:
                    self.ann_expr(s["val"], sc)
            elif t == "print":
                for ar in s["args"]:
                    self.ann_expr(ar, sc)
            elif t == "expr":
                self.ann_expr(s["val"], sc)
            elif t in ("pass", "break", "continue", "global", "extern", "struct"):
                if t == "global":
                    sc.globs.update(s["names"])
                pass
            else:
                raise HSErr(f"{t} not in x64 subset", s["line"])

    def collect_unsafe(self, body, sc):
        for s in body:
            t = s["t"]
            if t == "udecl":
                n = s["name"]
                if n in sc.loc or n in sc.uloc:
                    raise HSErr(f"'{n}' already defined in this scope", s["line"])
                sc.uloc[n] = self.slot(sc)
                sc.utypes[n] = s["utype"]
                if s["init"] is not None:
                    self.ann_expr(s["init"], sc, True)
            elif t == "struct":
                pass
            elif t in ("store", "fstore"):
                self.ann_expr(s["ptr"] if t == "store" else s["obj"], sc, True)
                if s.get("idx") is not None:
                    self.ann_expr(s["idx"], sc, True)
                self.ann_expr(s["val"], sc, True)
            elif t in ("if", "while"):
                self.ann_expr(s["cond"], sc, True)
                self.collect_unsafe(s.get("then", s.get("body", [])), sc)
                for ec, eb in s.get("elifs", []):
                    self.ann_expr(ec, sc, True)
                    self.collect_unsafe(eb, sc)
                self.collect_unsafe(s.get("els", []), sc)
            elif t in ("return", "break", "continue", "pass", "print", "expr", "set", "global"):
                # shared statements: reuse safe handling (slots unified)
                if t == "set":
                    self.ann_expr(s["val"], sc, True)
                    self.decl(sc, s["name"])
                elif t == "global":
                    sc.globs.update(s["names"])
                elif t == "print":
                    for ar in s["args"]:
                        self.ann_expr(ar, sc, True)
                elif t == "return" and s["val"] is not None:
                    self.ann_expr(s["val"], sc, True)
                elif t == "expr":
                    self.ann_expr(s["val"], sc, True)
            else:
                raise HSErr(f"{t} not allowed in unsafe (x64)", s["line"])

    def ann_expr(self, e, sc, ux=False):
        """Walk exprs; annotate field nodes with struct types (_st)."""
        from interp import HS_STRUCTS
        t = e["t"]
        if t in ("num", "str"):
            return
        if t == "var":
            self.reads.append((sc, e["name"]))
            return
        if t in ("neg", "not", "deref"):
            self.ann_expr(e["val"], sc, ux)
            return
        if t == "bin":
            self.ann_expr(e["l"], sc, ux)
            self.ann_expr(e["r"], sc, ux)
            return
        if t == "call":
            self.ann_expr(e["fn"], sc, ux)
            for ar in e["args"]:
                self.ann_expr(ar, sc, ux)
            return
        if t in ("index", "slice", "attr", "list", "dict"):
            raise HSErr(f"{t} not in x64 subset", e["line"])
        if t == "sizeof":
            st = e["stype"]
            if st not in ("I64", "U64", "Ptr") and st not in HS_STRUCTS:
                raise HSErr(f"unknown struct '{st}'", e["line"])
            return
        if t == "field":
            self.ann_expr(e["obj"], sc, ux)
            if e["idx"] is not None:
                self.ann_expr(e["idx"], sc, ux)
            e["_st"] = self.field_base(e["obj"], sc, e["line"])
            return
        raise HSErr(f"{t} not in x64 subset", e["line"])

    def field_base(self, obj, sc, ln):
        """Static struct name behind a field base (var or nested field)."""
        from interp import HS_STRUCTS, ptr_struct
        if obj["t"] == "var":
            s = sc
            while s is not None:
                if obj["name"] in s.utypes:
                    ut = s.utypes[obj["name"]]
                    xs = ptr_struct(ut)
                    if xs is None:
                        raise HSErr(f"cannot access field of {ut}", ln)
                    return xs
                if obj["name"] in s.loc:
                    raise HSErr(f"cannot access field of dynamic '{obj['name']}'", ln)
                s = s.parent
            raise HSErr(f"unknown variable '{obj['name']}'", ln)
        if obj["t"] == "field":
            xs = obj.get("_st")
            if xs is None or xs not in HS_STRUCTS:
                raise HSErr("struct type unknown (x64)", ln)
            f = HS_STRUCTS[xs]["fields"].get(obj["name"])
            if f is None:
                raise HSErr(f"struct '{xs}' has no field '{obj['name']}'", ln)
            xs2 = ptr_struct(f[0])
            if xs2 is None:
                raise HSErr(f"field '{obj['name']}' is not a struct pointer", ln)
            return xs2
        raise HSErr("field base must be a variable", ln)

    def decl(self, sc, name):
        if name in sc.loc or name in sc.uloc:
            return
        sc.loc[name] = self.slot(sc)

    XBUILTINS = {"print", "int", "alloc", "load8", "load32", "store8",
                 "store32", "as_ptr", "as_int"}

    def finalize(self, mod):
        ms = mod["scope"]
        for fs in self.all_fs:
            caps = set()
            for (s, nm) in self.reads:
                if s is not fs:
                    continue
                if nm in fs.params or nm in fs.loc or nm in fs.uloc or nm in fs.globs:
                    continue
                if nm in Gen.XBUILTINS:
                    continue
                p = fs.parent
                outer = False
                while p is not None:
                    if p is ms:
                        break
                    if nm in p.globs:
                        break
                    if nm in p.params or nm in p.uloc or nm in p.loc:
                        outer = True
                        break
                    p = p.parent
                if outer:
                    caps.add(nm)
            fs.caplist = sorted(caps)

    # ----- emit helpers -----
    def push_rax(self):
        self.a.push_r("rax")

    def rstr(self, s):
        if s not in self.strs:
            self.strs[s] = f"str{len(self.strs)}"
        return self.strs[s]

    def emit_str_table(self):
        for s, lab in self.strs.items():
            self.a.label(lab)
            self.a.code += s.encode()

    def new_tmp(self, pfx="t"):
        self.tmpn += 1
        return f"{pfx}{self.tmpn}"

    # ----- expressions: value ends in rax -----
    def ev(self, e, sc, mod):
        t = e["t"]
        ln = e["line"]
        a = self.a
        if t == "num":
            v = e["val"]
            if v is True:
                a.mov_ri64("rax", Gen.HS_TRUE)
            elif v is False:
                a.mov_ri64("rax", Gen.HS_FALSE)
            elif v is None:
                a.mov_ri64("rax", Gen.HS_NULL)
            elif isinstance(v, float):
                raise HSErr("Float not in x64 subset", ln)
            else:
                a.mov_ri64("rax", self.tag_int(v))
            return
        if t == "str":
            b = e["val"].encode()
            lab = self.rstr(e["val"])
            a.lea_rip("rdi", lab)
            a.mov_ri32("rsi", len(b))
            a.call("x_str_at")
            return
        if t == "var":
            self.var_get(e["name"], sc, mod, ln)
            return
        if t in ("list", "dict"):
            raise HSErr(f"{t} not in x64 subset", ln)
        if t == "neg":
            self.ev(e["val"], sc, mod)
            self.tag_check_int()
            a.sar_ri8("rax", 2)     # untag before negating
            a.neg_r("rax")
            self.tag_box()
            return
        if t == "not":
            self.ev(e["val"], sc, mod)
            self.truthy()
            a.setcc_al("e")
            self.box_bool_al()
            return
        if t == "bin":
            self.ev_bin(e, sc, mod)
            return
        if t == "call":
            self.ev_call(e, sc, mod)
            return
        if t in ("index", "slice", "attr"):
            raise HSErr(f"{t} not in x64 subset", ln)
        if t in ("deref", "sizeof", "field"):
            self.sev(e, sc, mod)
            return
        raise HSErr(f"{t} not in x64 subset", ln)

    def resolve_var(self, name, sc, mod, ln):
        """(kind, ref). Module-scope names use data labels. Names bound in an
        enclosing FUNCTION scope become captures (copy at def)."""
        # innermost function scope of the use site (None at module level)
        reader = sc
        while reader is not None and not reader.is_func:
            if reader is mod["scope"]:
                reader = None
                break
            reader = reader.parent
        s = sc
        while s is not None:
            if s is mod["scope"]:
                if name in s.uloc:
                    return ("guloc", name)
                if name in s.loc:
                    return ("gloc", name)
                break
            if name in s.globs:
                s = s.parent
                continue
            if name in s.params:
                if reader is not None and s is not reader:
                    return ("cap", self.cap_index(reader, name, ln))
                return ("param", s.loc[name])
            if name in s.uloc:
                if reader is not None and s is not reader:
                    return ("cap", self.cap_index(reader, name, ln))
                return ("uloc", s.uloc[name])
            if name in s.loc:
                if reader is not None and s is not reader:
                    return ("cap", self.cap_index(reader, name, ln))
                return ("loc", s.loc[name])
            s = s.parent
        return (None, None)

    def cap_index(self, reader, name, ln):
        cl = getattr(reader, "caplist", [])
        if name not in cl:
            raise HSErr(f"cannot capture '{name}' (x64)", ln)
        return cl.index(name)

    def glabel(self, mod, name):
        return f"g_{mod['pfx']}{name}"

    def reserve(self, name, nbytes):
        # zeroed data region for builder-filled tables (returns data offset)
        a = self.a
        if name in a.data_labels:
            raise HSErr(f"dup data reserve {name}")
        off = len(a.data)
        a.data_labels[name] = off
        a.data += b"\0" * nbytes
        return off

    def var_get(self, name, sc, mod, ln):
        a = self.a
        kind, ref = self.resolve_var(name, sc, mod, ln)
        if kind in ("param", "uloc", "loc"):
            a.mov_rm("rax", "rbp", ref)
            return
        if kind == "cap":
            a.mov_rm("rax", "r15", 8 * ref)
            return
        if kind in ("guloc", "gloc"):
            a.lea_rip("rax", self.glabel(mod, name))
            a.mov_rm("rax", "rax")
            return
        # builtin?
        if name in ("print", "len", "range", "str", "int", "float", "input",
                    "open", "read", "write", "close", "argv", "env", "system",
                    "append", "split", "find", "join", "ticks", "readkey",
                    "pmm_alloc", "meminfo", "tcp_connect", "tcp_send",
                    "tcp_recv", "tcp_close", "tcp_listen", "tcp_accept",
                    "http_get", "json_parse", "json_str", "read_text",
                    "write_text", "append_text", "exists", "ls", "mkdir",
                    "json_load", "json_save", "alloc", "load8", "load32",
                    "store8", "store32", "as_ptr", "as_int", "asm"):
            raise HSErr(f"builtin '{name}' is not a value (call it)", ln)
        raise HSErr(f"unknown variable '{name}'", ln)

    def find_global(self, name, sc, mod):
        # walk to module scope: names assigned at module level live in data
        m = mod
        return f"g_{m['pfx']}{name}" if name in m.get("globals", ()) else None

    def ev_bin(self, e, sc, mod):
        op, ln = e["op"], e["line"]
        a = self.a
        if op in ("and", "or"):
            # hs returns the operand itself, not a Bool
            self.ev(e["l"], sc, mod)
            self.truthy()
            lab_keep, lab_end = self.new_tmp("bo"), self.new_tmp("bo")
            if op == "and":
                a.jcc("e", lab_keep)    # falsy left -> result is the left value
            else:
                a.jcc("ne", lab_keep)   # truthy left -> result is the left value
            self.ev(e["r"], sc, mod)
            a.jmp(lab_end)
            a.label(lab_keep)
            a.label(lab_end)
            return
        if op in ("==", "!="):
            self.ev(e["l"], sc, mod)
            a.push_r("rax")
            self.ev(e["r"], sc, mod)
            a.mov_rr("rcx", "rax")
            a.pop_r("rax")
            a.mov_rr("rdi", "rax")
            a.mov_rr("rsi", "rcx")
            a.call("x_eq")           # al = 0/1
            self.box_bool_al()
            if op == "!=":
                a.code += bytes([0x48, 0x83, 0xF0, 0x08])  # xor rax, 8
            return
        if op in ("<", ">", "<=", ">="):
            self.ev(e["l"], sc, mod)
            a.push_r("rax")
            self.ev(e["r"], sc, mod)
            a.mov_rr("rcx", "rax")
            a.pop_r("rax")
            a.mov_rr("rdi", "rax")
            a.mov_rr("rsi", "rcx")
            a.call("x_cmp")
            a.cmp_ri32("rax", 0)
            a.setcc_al({"<": "l", ">": "g", "<=": "le", ">=": "ge"}[op])
            self.box_bool_al()
            return
        if op == "+":
            self.ev(e["l"], sc, mod)
            a.push_r("rax")
            self.ev(e["r"], sc, mod)
            a.mov_rr("rcx", "rax")
            a.pop_r("rax")
            self.emit_add()
            return
        # - * / % : Int only
        self.ev(e["l"], sc, mod)
        self.tag_check_int()
        a.sar_ri8("rax", 2)
        a.push_r("rax")
        self.ev(e["r"], sc, mod)
        self.tag_check_int()
        a.sar_ri8("rax", 2)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")
        if op == "-":
            a.sub_rr("rax", "rcx")
        elif op == "*":
            a.imul_rr("rax", "rcx")
        elif op in ("/", "%"):
            a.push_r("rdx")
            if not self.freestanding:
                # hosted: clean divide error; freestanding: hardware #DE
                a.test_rr("rcx", "rcx")
                lab_dz = self.new_tmp("dz")
                a.jcc("ne", lab_dz)
                a.add_ri32("rsp", 8)  # drop saved rdx; never returns
                a.jmp("divzero")
                a.label(lab_dz)
            a.cqo()
            a.idiv_r("rcx")
            if op == "%":
                a.mov_rr("rax", "rdx")
            a.pop_r("rdx")
        else:
            raise HSErr(f"bad operator {op}", ln)
        self.tag_box()

    def emit_add(self):
        """rax/rcx tagged -> rax = Int+Int or Str+Str, else type error."""
        a = self.a
        lab_str, lab_err, lab_end = (self.new_tmp("ad"), self.new_tmp("ad"),
                                     self.new_tmp("ad"))
        # Int + Int (fast path)
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", lab_str)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", lab_str)
        a.sar_ri8("rax", 2)
        a.sar_ri8("rcx", 2)
        a.add_rr("rax", "rcx")
        self.tag_box()
        a.jmp(lab_end)
        a.label(lab_str)
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.jcc("ne", lab_err)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.jcc("ne", lab_err)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("ne", lab_err)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("ne", lab_err)
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rcx")
        a.call("x_str_cat")
        a.jmp(lab_end)
        a.label(lab_err)
        self.type_err()
        a.label(lab_end)

    def ev_call(self, e, sc, mod):
        ln = e["line"]
        a = self.a
        fn = e["fn"]
        # builtin print / int() / unsafe builtins
        if fn["t"] == "var" and fn["name"] == "print":
            self.ev_print(e["args"], sc, mod, ln)
            return
        if fn["t"] == "var" and fn["name"] == "int":
            if len(e["args"]) != 1:
                raise HSErr("int wants 1 arg", ln)
            self.ev(e["args"][0], sc, mod)
            self.tag_check_int()
            return
        if fn["t"] == "var" and fn["name"] in ("str", "len"):
            if len(e["args"]) != 1:
                raise HSErr(f"{fn['name']} wants 1 arg", ln)
            self.ev(e["args"][0], sc, mod)
            a.mov_rr("rdi", "rax")
            a.call("x_str" if fn["name"] == "str" else "x_len")
            return
        if fn["t"] == "var" and fn["name"] in (
                "alloc", "load8", "load32", "store8", "store32",
                "as_ptr", "as_int"):
            self.sev_call(fn["name"], e["args"], sc, mod, ln)
            return
        if fn["t"] == "var" and fn["name"] in (
                "range", "float", "input", "open", "read",
                "write", "close", "argv", "env", "system", "append", "split",
                "find", "join", "ticks", "readkey", "pmm_alloc", "pmm_total",
                "pmm_free", "meminfo",
                "tcp_connect", "tcp_send", "tcp_recv", "tcp_close",
                "tcp_listen", "tcp_accept", "http_get", "json_parse",
                "json_str", "read_text", "write_text", "append_text",
                "exists", "ls", "mkdir", "json_load", "json_save", "asm"):
            if self.freestanding and fn["name"] in (
                    "ticks", "readkey", "pmm_alloc", "pmm_total", "pmm_free"):
                self.ev_kdev(fn["name"], e["args"], sc, mod, ln)
                return
            raise HSErr(f"builtin '{fn['name']}' not in x64 subset", ln)
        # user function: indirect through value (uniform caps in r15)
        self.ev(fn, sc, mod)  # rax = func struct ptr
        a.push_r("rax")
        for ar in reversed(e["args"]):
            self.ev(ar, sc, mod)
            a.push_r("rax")
        a.mov_rm("rax", "rsp", 8 * len(e["args"]))  # reload func object
        a.push_r("r15")
        a.mov_rr("r15", "rax")
        a.add_ri32("r15", 16)  # r15 = &caps (lea, no deref)
        a.mov_rm("rax", "rax", 8)  # code addr
        a.call_rax()
        a.pop_r("r15")
        a.add_ri32("rsp", 8 * (len(e["args"]) + 1))

    def ev_kdev(self, name, args, sc, mod, ln):
        # freestanding kernel device builtins -> rax (Str* for readkey, 0=Null)
        a = self.a
        if name == "ticks":
            if args:
                raise HSErr("ticks takes no args", ln)
            a.lea_rip("rax", "ticks_")
            a.mov_rm("rax", "rax", 0)
            self.tag_box()
            return
        if name == "readkey":
            if args:
                raise HSErr("readkey takes no args", ln)
            lab_no, lab_done = self.new_tmp("rk"), self.new_tmp("rk")
            a.lea_rip("rax", "keyflag_")
            a.mov_rm("rax", "rax", 0)
            a.test_rr("rax", "rax")
            a.jcc("e", lab_no)
            # Str object: [kind=0][len=1][byte]
            a.mov_ri32("rdi", 32)
            a.call("x_malloc")
            a.mov_rr("r10", "rax")
            a.mov_ri32("rcx", 0)
            a.mov_mr("r10", "rcx", 0)          # kind = K_STR
            a.mov_ri32("rcx", 1)
            a.mov_mr("r10", "rcx", 8)          # len = 1
            a.lea_rip("rcx", "keycode_")
            a.movzx_eax_m8("rcx", 0)           # al = ascii
            a.mov_mr8("r10", 0, 16)            # byte[0] = al
            a.mov_ri32("rcx", 0)
            a.lea_rip("rdx", "keyflag_")
            a.mov_mr("rdx", "rcx", 0)          # clear flag
            a.mov_rr("rax", "r10")
            a.jmp(lab_done)
            a.label(lab_no)
            a.mov_ri64("rax", Gen.HS_NULL)
            a.label(lab_done)
            return
        if name == "pmm_alloc":
            if len(args) != 1:
                raise HSErr("pmm_alloc wants pmm_alloc(npages)", ln)
            self.ev(args[0], sc, mod)  # rax = npages (tagged)
            self.tag_check_int()
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            a.lea_rip("rcx", "pmm_free_")
            a.mov_rm("rcx", "rcx", 0)
            a.pop_r("rax")
            a.cmp_rr("rcx", "rax")
            lab_pa = self.new_tmp("pa")
            a.jcc("ae", lab_pa)
            a.lea_rip("rsi", "oom_")
            a.call("k_puts_cstr")
            a.call("k_halt")
            a.label(lab_pa)
            # addr = PMM_BASE + next*4096
            a.lea_rip("rcx", "pmm_next_")
            a.mov_rm("rcx", "rcx", 0)
            a.push_r("rax")  # npages
            a.push_r("rcx")  # next
            a.mov_ri32("rax", 0x4000000)
            a.mov_rr("rdx", "rcx")
            a.shl_ri8("rdx", 12)
            a.add_rr("rax", "rdx")  # addr
            a.pop_r("rcx")  # next
            a.pop_r("rdx")  # npages
            a.push_r("rax")  # save addr
            a.add_rr("rcx", "rdx")  # next += n
            a.lea_rip("rax", "pmm_next_")
            a.mov_mr("rax", "rcx", 0)
            a.lea_rip("rax", "pmm_free_")
            a.mov_rm("rcx", "rax", 0)
            a.sub_rr("rcx", "rdx")  # free -= n
            a.mov_mr("rax", "rcx", 0)
            a.pop_r("rax")  # addr (raw)
            self.tag_box()
            return
        if name in ("pmm_total", "pmm_free"):
            if args:
                raise HSErr(f"{name} takes no args", ln)
            if name == "pmm_total":
                a.mov_ri32("rax", 32768)
            else:
                a.lea_rip("rax", "pmm_free_")
                a.mov_rm("rax", "rax", 0)
            self.tag_box()
            return
        raise HSErr(f"bad kdev {name}", ln)

    def ev_print(self, args, sc, mod, ln):
        a = self.a
        for i, ar in enumerate(args):
            if i > 0:
                a.lea_rip("rdi", "sp_")
                a.mov_ri32("rsi", 1)
                self.rt_out()
            if ar["t"] == "str":
                b = ar["val"].encode()
                lab = self.rstr(ar["val"])
                a.lea_rip("rdi", lab)
                a.mov_ri32("rsi", len(b))
                self.rt_out()
            else:
                self.ev(ar, sc, mod)
                a.mov_rr("rdi", "rax")
                a.call("print_val")
        a.lea_rip("rdi", "nl_")
        a.mov_ri32("rsi", 1)
        self.rt_out()

    # ----- unsafe subset -----
    def sev(self, e, sc, mod):
        t = e["t"]
        ln = e["line"]
        a = self.a
        if t == "num":
            v = e["val"]
            if v is None:
                a.mov_ri32("rax", 0)
            elif isinstance(v, bool):
                a.mov_ri32("rax", int(v))
            elif isinstance(v, int):
                a.mov_ri64("rax", v & ((1 << 64) - 1) if v >= 0 else v)
            else:
                raise HSErr("float not in x64 subset", ln)
            return
        if t == "str":
            raise HSErr("strings not allowed in unsafe", ln)
        if t == "var":
            self.var_get(e["name"], sc, mod, ln)
            return
        if t == "deref":
            self.sev(e["val"], sc, mod)
            a.mov_rm("rax", "rax", 0)
            return
        if t == "neg":
            self.sev(e["val"], sc, mod)
            a.neg_r("rax")
            return
        if t == "not":
            self.sev(e["val"], sc, mod)
            a.test_rr("rax", "rax")
            a.setcc_al("e")
            a.movzx_eax_al()
            return
        if t == "sizeof":
            st = e["stype"]
            if st in ("I64", "U64", "Ptr"):
                a.mov_ri32("rax", 8)
            else:
                from interp import HS_STRUCTS
                if st not in HS_STRUCTS:
                    raise HSErr(f"unknown struct '{st}'", ln)
                a.mov_ri32("rax", HS_STRUCTS[st]["size"])
            return
        if t == "field":
            self.sev_field(e, sc, mod)
            return
        if t == "bin":
            self.sev_bin(e, sc, mod)
            return
        if t == "call":
            fn = e["fn"]
            if fn["t"] == "var" and fn["name"] in (
                    "alloc", "load8", "load32", "store8", "store32",
                    "as_ptr", "as_int"):
                self.sev_call(fn["name"], e["args"], sc, mod, ln)
                return
            raise HSErr("only alloc/load/store/as_* calls allowed in unsafe (x64)", ln)
        raise HSErr(f"{t} not in x64 subset", ln)

    def sev_field(self, e, sc, mod):
        from interp import HS_STRUCTS
        ln = e["line"]
        a = self.a
        self.sev(e["obj"], sc, mod)
        a.push_r("rax")
        xs = e.get("_st")
        if xs is None or xs not in HS_STRUCTS:
            raise HSErr("struct type unknown (x64)", ln)
        L = HS_STRUCTS[xs]
        f = L["fields"].get(e["name"])
        if f is None:
            raise HSErr(f"struct '{xs}' has no field '{e['name']}'", ln)
        ft, off, count = f
        a.pop_r("rax")
        if not self.freestanding:
            # hosted: clean null error; freestanding: hardware #PF
            lab_nn = self.new_tmp("nn")
            a.test_rr("rax", "rax")
            a.jcc("ne", lab_nn)
            self.rt_die("null pointer dereference")
            a.label(lab_nn)
        if count > 1:
            if e["idx"] is None:
                raise HSErr(f"array field '{e['name']}' needs an index", ln)
            a.push_r("rax")  # save base across idx eval
            self.sev(e["idx"], sc, mod)
            a.mov_rr("rcx", "rax")
            a.pop_r("rax")  # base
            if not self.freestanding:
                a.cmp_ri32("rcx", count)  # unsigned: negatives fail too
                lab_ok = self.new_tmp("bd")
                a.jcc("b", lab_ok)
                self.rt_die(f"index out of range for '{e['name']}'")
                a.label(lab_ok)
            a.mov_rmx("rax", "rax", "rcx", 8, off)
            return
        if e["idx"] is not None:
            raise HSErr(f"field '{e['name']}' is not an array", ln)
        a.mov_rm("rax", "rax", off)

    def sev_idx(self, e, sc, mod):
        self.sev(e, sc, mod)
        self.a.push_r("rax")

    def sev_bin(self, e, sc, mod):
        op, ln = e["op"], e["line"]
        a = self.a
        if op in ("and", "or"):
            self.sev(e["l"], sc, mod)
            a.test_rr("rax", "rax")
            lab1, lab2 = self.new_tmp("b"), self.new_tmp("b")
            if op == "and":
                a.jcc("e", lab1)
                self.sev(e["r"], sc, mod)
                a.test_rr("rax", "rax")
                a.setcc_al("ne")
                a.movzx_eax_al()
                a.jmp(lab2)
                a.label(lab1)
                a.mov_ri32("rax", 0)
                a.label(lab2)
            else:
                a.jcc("ne", lab1)
                self.sev(e["r"], sc, mod)
                a.test_rr("rax", "rax")
                a.setcc_al("ne")
                a.movzx_eax_al()
                a.jmp(lab2)
                a.label(lab1)
                a.mov_ri32("rax", 1)
                a.label(lab2)
            return
        self.sev(e["l"], sc, mod)
        a.push_r("rax")
        self.sev(e["r"], sc, mod)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")
        if op == "+":
            a.add_rr("rax", "rcx")
        elif op == "-":
            a.sub_rr("rax", "rcx")
        elif op == "*":
            a.imul_rr("rax", "rcx")
        elif op in ("/", "%"):
            a.push_r("rdx")
            if not self.freestanding:
                # hosted: clean divide error; freestanding: hardware #DE
                a.test_rr("rcx", "rcx")
                lab_dz = self.new_tmp("dz")
                a.jcc("ne", lab_dz)
                a.add_ri32("rsp", 8)  # drop saved rdx; divzero never returns
                a.jmp("divzero")
                a.label(lab_dz)
            a.cqo()
            a.idiv_r("rcx")
            if op == "%":
                a.mov_rr("rax", "rdx")
            a.pop_r("rdx")
        elif op in ("==", "!=", "<", ">", "<=", ">="):
            a.cmp_rr("rax", "rcx")
            cc = {"==": "e", "!=": "ne", "<": "l", ">": "g",
                  "<=": "le", ">=": "ge"}[op]
            a.setcc_al(cc)
            a.movzx_eax_al()
        else:
            raise HSErr(f"bad operator {op}", ln)

    def is_raw_expr(self, e):
        """True when the expression is already an untagged machine value."""
        t = e["t"]
        if t in ("num", "deref", "field", "sizeof", "bin", "neg", "not"):
            return True
        if t == "call" and e["fn"]["t"] == "var" and e["fn"]["name"] in (
                "alloc", "load8", "load32", "store8", "store32",
                "as_ptr", "as_int"):
            return True
        return False

    def sev_call(self, name, args, sc, mod, ln):
        a = self.a
        if name == "alloc":
            if len(args) != 1:
                raise HSErr("alloc wants alloc(n)", ln)
            self.sev(args[0], sc, mod)
            a.push_r("rax")
            a.call("x_alloc")
            a.add_ri32("rsp", 8)
            return
        if name in ("load8", "load32"):
            if len(args) != 1:
                raise HSErr(f"{name} wants {name}(p)", ln)
            self.sev(args[0], sc, mod)
            if name == "load8":
                # movzx rax, byte [rax]
                a.code += bytes([0x48, 0x0F, 0xB6, 0x00])
            else:
                # mov eax, [rax] (zero-extends)
                a.code += bytes([0x8B, 0x00])
            return
        if name in ("store8", "store32"):
            if len(args) != 2:
                raise HSErr(f"{name} wants {name}(p, v)", ln)
            self.sev(args[1], sc, mod)
            a.push_r("rax")
            self.sev(args[0], sc, mod)
            a.pop_r("rcx")
            if name == "store8":
                a.code += bytes([0x88, 0x08])  # mov [rax], cl
            else:
                a.code += bytes([0x89, 0x08])  # mov [rax], ecx
            a.mov_rr("rax", "rcx")
            return
        if name in ("as_ptr", "as_int"):
            if len(args) != 1:
                raise HSErr(f"{name} wants 1 arg", ln)
            self.sev(args[0], sc, mod)
            if self.is_raw_expr(args[0]):
                return  # already a machine value (literal / unsafe expression)
            # tagged Int -> raw payload; heap Str/Func -> raw address
            lab_heap, lab_bad, lab_done = (self.new_tmp("az"), self.new_tmp("az"),
                                           self.new_tmp("az"))
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.cmp_ri32("r11", Gen.TAG_INT)
            a.jcc("ne", lab_heap)
            a.sar_ri8("rax", 2)
            a.jmp(lab_done)
            a.label(lab_heap)
            a.test_rr("r11", "r11")   # low bits clear -> heap pointer
            a.jcc("ne", lab_bad)
            a.jmp(lab_done)
            a.label(lab_bad)
            self.type_err()
            a.label(lab_done)
            return
        raise HSErr(f"{name} not in x64 subset", ln)

    # ----- statements -----
    def ex(self, s, sc, mod, depth):
        t = s["t"]
        ln = s["line"]
        a = self.a
        if t == "pass":
            return
        if t == "expr":
            self.ev(s["val"], sc, mod)
            return
        if t == "print":
            self.ev_print(s["args"], sc, mod, ln)
            return
        if t == "set":
            self.ev(s["val"], sc, mod)
            self.var_set(s["name"], sc, mod, ln)
            return
        if t == "return":
            if depth == 0:
                raise HSErr("return outside function", ln)
            if s["val"] is not None:
                self.ev(s["val"], sc, mod)
            else:
                a.mov_ri64("rax", Gen.HS_NULL)
            a.mov_rr("rsp", "rbp")
            a.pop_r("rbp")
            a.ret()
            return
        if t == "break":
            if not self.loop_stack:
                raise HSErr("break outside loop", ln)
            a.jmp(self.loop_stack[-1][0])
            return
        if t == "continue":
            if not self.loop_stack:
                raise HSErr("continue outside loop", ln)
            a.jmp(self.loop_stack[-1][1])
            return
        if t == "def":
            fs = s["_fs"]
            lab = self.flabels[id(fs)]
            n = len(fs.caplist)
            for nm in fs.caplist:
                self.var_get(nm, sc, mod, ln)
                a.push_r("rax")
            a.mov_ri32("rdi", 8 * (2 + n))
            a.call("x_malloc")
            for i in reversed(range(n)):
                a.pop_r("rcx")
                a.mov_mr("rax", "rcx", 8 * (i + 2))
            a.mov_ri32("rcx", 1)
            a.mov_mr("rax", "rcx", 0)          # kind = K_FUNC
            a.lea_rip("rcx", lab)
            a.mov_mr("rax", "rcx", 8)          # code address
            self.var_set(s["name"], sc, mod, ln)
            return
        if t == "if":
            lab_e, lab_x = self.new_tmp("if"), self.new_tmp("if")
            n = len(s["elifs"])
            labs = [self.new_tmp("if") for _ in range(n)]
            self.ev(s["cond"], sc, mod)
            self.truthy_br(labs[0] if n else lab_e)
            self.ex_body(s["then"], sc, mod, depth)
            a.jmp(lab_x)
            for i, (ec, eb) in enumerate(s["elifs"]):
                a.label(labs[i])
                self.ev(ec, sc, mod)
                self.truthy_br(labs[i + 1] if i + 1 < n else lab_e)
                self.ex_body(eb, sc, mod, depth)
                a.jmp(lab_x)
            a.label(lab_e)
            if s["els"]:
                self.ex_body(s["els"], sc, mod, depth)
            a.label(lab_x)
            return
        if t == "while":
            lab_t, lab_c, lab_x = (self.new_tmp("w"), self.new_tmp("w"), self.new_tmp("w"))
            a.label(lab_t)
            self.ev(s["cond"], sc, mod)
            self.truthy_br(lab_x)
            self.loop_stack.append((lab_x, lab_t))
            self.ex_body(s["body"], sc, mod, depth + 1)
            self.loop_stack.pop()
            a.jmp(lab_t)
            a.label(lab_x)
            return
        if t == "for":
            raise HSErr("for not in x64 subset (use while)", ln)
        if t in ("global", "import", "extern", "try", "unsafe", "struct",
                 "udecl", "store", "fstore", "raise", "setindex", "setattr"):
            raise HSErr(f"{t} handled elsewhere or not in x64 subset", ln)
        raise HSErr(f"bad stmt {t}", ln)

    def var_set(self, name, sc, mod, ln):
        # value in rax
        a = self.a
        kind, ref = self.resolve_var(name, sc, mod, ln)
        if kind in ("param", "uloc", "loc"):
            a.mov_mr("rbp", "rax", ref)
            return
        if kind in ("guloc", "gloc"):
            a.push_r("rax")
            a.lea_rip("rcx", self.glabel(mod, name))
            a.pop_r("rax")
            a.mov_mr("rcx", "rax", 0)
            return
        raise HSErr(f"unknown variable '{name}'", ln)

    def ex_body(self, body, sc, mod, depth):
        for s in body:
            if s["t"] == "unsafe":
                self.ex_unsafe(s, sc, mod, depth)
            else:
                self.ex(s, sc, mod, depth)

    def ex_unsafe(self, s, sc, mod, depth):
        for x in s["body"]:
            t = x["t"]
            ln = x["line"]
            a = self.a
            if t == "udecl":
                if x["init"] is not None:
                    self.sev(x["init"], sc, mod)
                else:
                    a.mov_ri32("rax", 0)
                self.var_set(x["name"], sc, mod, ln)
            elif t == "store":
                self.sev(x["ptr"], sc, mod)
                a.push_r("rax")
                self.sev(x["val"], sc, mod)
                a.mov_rr("rcx", "rax")
                a.pop_r("rax")
                a.mov_mr("rax", "rcx", 0)  # [rax] = rcx (64-bit)
            elif t == "fstore":
                from interp import HS_STRUCTS
                xs = self.field_base(x["obj"], sc, ln)
                L = HS_STRUCTS[xs]
                f = L["fields"].get(x["name"])
                if f is None:
                    raise HSErr(f"struct '{xs}' has no field '{x['name']}'", ln)
                ft, off, count = f
                self.sev(x["obj"], sc, mod)
                a.push_r("rax")
                if not self.freestanding:
                    lab_nn = self.new_tmp("nn")
                    a.test_rr("rax", "rax")
                    a.jcc("ne", lab_nn)
                    self.rt_die("null pointer dereference")
                    a.label(lab_nn)
                a.pop_r("rax")  # base; the single pop for the push above
                if count > 1:
                    if x["idx"] is None:
                        raise HSErr(f"array field '{x['name']}' needs an index", ln)
                    a.push_r("rax")  # save base across idx eval
                    self.sev(x["idx"], sc, mod)
                    a.mov_rr("rcx", "rax")
                    a.pop_r("rax")  # base
                    if not self.freestanding:
                        a.cmp_ri32("rcx", count)
                        lab_ok = self.new_tmp("bd")
                        a.jcc("b", lab_ok)
                        self.rt_die(f"index out of range for '{x['name']}'")
                        a.label(lab_ok)
                    a.lea_m("rax", "rax", off, "rcx", 8)
                else:
                    if x["idx"] is not None:
                        raise HSErr(f"field '{x['name']}' is not an array", ln)
                    a.lea_m("rax", "rax", off)
                a.push_r("rax")
                self.sev(x["val"], sc, mod)
                a.mov_rr("rcx", "rax")
                a.pop_r("rax")
                a.mov_mr("rax", "rcx", 0)
            elif t == "struct":
                pass
            elif t == "expr":
                self.sev(x["val"], sc, mod)
            elif t == "print":
                # unsafe print: raw Int / Str literal (no value tagging)
                for i, ar in enumerate(x["args"]):
                    if i > 0:
                        a.lea_rip("rdi", "sp_")
                        a.mov_ri32("rsi", 1)
                        self.rt_out()
                    if ar["t"] == "str":
                        b = ar["val"].encode()
                        lab = self.rstr(ar["val"])
                        a.lea_rip("rdi", lab)
                        a.mov_ri32("rsi", len(b))
                        self.rt_out()
                    else:
                        self.sev(ar, sc, mod)
                        a.push_r("rax")
                        a.call("print_int")
                        a.add_ri32("rsp", 8)
                a.lea_rip("rdi", "nl_")
                a.mov_ri32("rsi", 1)
                self.rt_out()
            elif t in ("if", "while"):
                # static conditions
                if t == "if":
                    lab_e, lab_x = self.new_tmp("if"), self.new_tmp("if")
                    n = len(x["elifs"])
                    labs = [self.new_tmp("if") for _ in range(n)]
                    self.sev(x["cond"], sc, mod)
                    a.test_rr("rax", "rax")
                    a.jcc("e", labs[0] if n else lab_e)
                    for st in x["then"]:
                        self.ex_unsafe_one(st, sc, mod, depth)
                    a.jmp(lab_x)
                    for i, (ec, eb) in enumerate(x["elifs"]):
                        a.label(labs[i])
                        self.sev(ec, sc, mod)
                        a.test_rr("rax", "rax")
                        a.jcc("e", labs[i + 1] if i + 1 < n else lab_e)
                        for st in eb:
                            self.ex_unsafe_one(st, sc, mod, depth)
                    a.label(lab_e)
                    if x["els"]:
                        for st in x["els"]:
                            self.ex_unsafe_one(st, sc, mod, depth)
                    a.label(lab_x)
                else:
                    lab_t, lab_x = self.new_tmp("w"), self.new_tmp("w")
                    a.label(lab_t)
                    self.sev(x["cond"], sc, mod)
                    a.test_rr("rax", "rax")
                    a.jcc("e", lab_x)
                    self.loop_stack.append((lab_x, lab_t))
                    for st in x["body"]:
                        self.ex_unsafe_one(st, sc, mod, depth + 1)
                    self.loop_stack.pop()
                    a.jmp(lab_t)
                    a.label(lab_x)
            elif t in ("return", "break", "continue"):
                self.ex(x, sc, mod, depth)
            elif t == "set":
                self.sev(x["val"], sc, mod)
                self.var_set(x["name"], sc, mod, ln)
            else:
                raise HSErr(f"{t} not allowed in unsafe (x64)", ln)

    def ex_unsafe_one(self, s, sc, mod, depth):
        # single unsafe-level statement (shared with ex_unsafe body)
        t = s["t"]
        if t in ("udecl", "store", "fstore", "struct", "expr", "print",
                 "if", "while", "return", "break", "continue", "set"):
            # re-dispatch through a one-item unsafe wrapper path
            self.ex_unsafe({"t": "unsafe", "line": s["line"], "body": [s]},
                           sc, mod, depth)
            return
        raise HSErr(f"{t} not allowed in unsafe (x64)", s["line"])

    def rt_die(self, msg):
        # write msg to stderr and exit(1); clobbers rax/rcx/rdx/rsi/rdi
        a = self.a
        lab = self.rstr(msg + "\n")
        a.lea_rip("rsi", lab)
        a.mov_ri32("rdx", len((msg + "\n").encode()))
        if self.freestanding:
            self.k_write()
            a.call("k_halt")
        else:
            a.mov_ri32("rdi", 2)
            a.mov_ri32("rax", 1)
            a.syscall()
            a.mov_ri32("rdi", 1)
            a.mov_ri32("rax", 60)
            a.syscall()

    # ----- tagged-value codegen helpers -----
    def tag_int(self, v):
        """Python int -> tagged 64-bit pattern (62-bit payload)."""
        return ((v * 4) + 1) & ((1 << 64) - 1)

    def tag_box(self):
        """rax = raw int -> rax = tagged Int"""
        a = self.a
        a.shl_ri8("rax", 2)
        a.or_ri8("rax", 1)

    def box_bool_al(self):
        """al = 0/1 -> rax = tagged Bool (HS_FALSE / HS_TRUE)"""
        a = self.a
        a.movzx_eax_al()
        a.shl_ri8("rax", 3)
        a.or_ri8("rax", 2)

    def tag_check_int(self, reg="rax"):
        """Die with a type error unless reg holds a tagged Int."""
        a = self.a
        lab_ok = self.new_tmp("tc")
        a.mov_rr("r11", reg)
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("e", lab_ok)
        a.jmp("type_err")
        a.label(lab_ok)

    def truthy(self):
        """rax = tagged value -> al = 0/1 truthiness (hs rules)."""
        a = self.a
        a.mov_rr("rdi", "rax")
        a.call("x_truth")

    def truthy_br(self, lab_false):
        """rax = tagged value; jump lab_false when falsy (Int fast path)."""
        a = self.a
        lab_int, lab_true, lab_slow = (self.new_tmp("tb"), self.new_tmp("tb"),
                                       self.new_tmp("tb"))
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", lab_slow)
        a.cmp_ri32("rax", 1)      # tagged zero is 0<<2|1 == 1
        a.jcc("ne", lab_true)
        a.jmp(lab_false)
        a.label(lab_true)
        a.label(lab_slow)
        self.truthy()
        a.jcc("e", lab_false)

    def type_err(self):
        self.a.jmp("type_err")

    # ----- functions / main / link -----
    def emit_func(self, label, node, fscope, mod):
        a = self.a
        a.label(label)
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        n = fscope.nloc
        if n:
            a.sub_ri32("rsp", 8 * n)
        self.ex_body(node["body"], fscope, mod, 1)
        a.mov_ri64("rax", Gen.HS_NULL)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()

    def emit_data(self, mod):
        a = self.a
        ms = mod["scope"]
        for name in sorted(set(ms.loc) | set(ms.uloc)):
            a.data_label(self.glabel(mod, name))
            a.data_qword(Gen.HS_UNBOUND if name in ms.loc else 0)

    def emit_main(self, mod):
        a = self.a
        ms = mod["scope"]
        if self.freestanding:
            self.emit_longmode_tail(mod)
        a.label("hs_kernel_main" if self.freestanding else "hs_main")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        if ms.nloc:
            a.sub_ri32("rsp", 8 * ms.nloc)
        self.ex_body(mod["prog"], ms, mod, 0)
        if self.freestanding:
            # return to the boot trampoline, which halts
            a.mov_rr("rsp", "rbp")
            a.pop_r("rbp")
            a.ret()
            return
        a.mov_ri32("rax", 0)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # _start: align stack, call hs_main, exit(code)
        a.label("_start")
        a.and_ri32("rsp", -16)
        a.call("hs_main")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rax", 60)
        a.syscall()

    def emit_longmode_tail(self, mod):
        # 64-bit entry reached via far jmp from boot32: set segments + stack,
        # init COM1, call hs_kernel_main, halt. STACK_TOP patched by builder.
        a = self.a
        a.label("long_mode")
        a.mov_ax_imm16(0x10)
        for seg in (3, 0, 4, 5, 2):  # ds es fs gs ss
            a.mov_seg16(seg, 0)  # ax
        a.mov_ri64("rsp", 0)  # patched: STACK_TOP (abs64 placeholder)
        self._stack_patch_pos = len(a.code) - 8
        for port, val in ((0x3F9, 0x00), (0x3FB, 0x80), (0x3F8, 0x03),
                          (0x3F9, 0x00), (0x3FB, 0x03), (0x3FA, 0xC7),
                          (0x3FC, 0x0B)):
            a.mov_ri16("dx", port)
            a.mov_ri32("rax", val)
            a.out_dx_al()
        # PIC remap: master 0x20, slave 0x28, 8086 mode, unmask IRQ0+1
        for port, val in ((0x20, 0x11), (0xA0, 0x11), (0x21, 0x20),
                          (0xA1, 0x28), (0x21, 0x04), (0xA1, 0x02),
                          (0x21, 0x01), (0xA1, 0x01), (0x21, 0xFC),
                          (0xA1, 0xFF)):
            a.mov_ri16("dx", port)
            a.mov_ri32("rax", val)
            a.out_dx_al()
        # PIT ch0, mode 3, 100Hz
        for port, val in ((0x43, 0x36), (0x40, 0x9B), (0x40, 0x2E)):
            a.mov_ri16("dx", port)
            a.mov_ri32("rax", val)
            a.out_dx_al()
        a.lidt_rip("idtr_")
        a.sti()
        a.call("hs_kernel_main")
        a.cli()
        lab_h = self.new_tmp("kh")
        a.label(lab_h)
        a.hlt()
        a.jmp(lab_h)

    def build_image(self, mod):
        # assign function labels, collect, emit everything, link
        ms = mod["scope"]
        self.collect(mod["prog"], ms)
        for i, fs in enumerate(self.all_fs):
            self.flabels[id(fs)] = f"hsF_{i}"
        self.finalize(mod)
        self.emit_data(mod)
        if self.freestanding:
            self.emit_runtime_fs()
        else:
            self.emit_runtime()
        if self.freestanding:
            self.emit_irq_stubs()
        for s in self._def_nodes(mod):
            self.emit_func(self.flabels[id(s["_fs"])], s, s["_fs"], mod)
        self.emit_main(mod)
        # rodata: strings + sp/nl (sp_/nl_ labels for separators)
        self.a.label("sp_")
        self.a.code += b" "
        self.a.label("nl_")
        self.a.code += b"\n"
        if self.freestanding:
            self.a.label("oom_")
            self.a.code += b"out of memory\0"
            self.a.label("dzm_")
            self.a.code += b"division by zero\0"
            self.a.label("exc_")
            self.a.code += b"EXC "
            self.a.label("kbdmap_")
            # set-1 make-code -> ascii (0 = ignore)
            kb = bytearray(256)
            for code, ch in ((0x02, "1"), (0x03, "2"), (0x04, "3"), (0x05, "4"),
                             (0x06, "5"), (0x07, "6"), (0x08, "7"), (0x09, "8"),
                             (0x0A, "9"), (0x0B, "0"), (0x10, "q"), (0x11, "w"),
                             (0x12, "e"), (0x13, "r"), (0x14, "t"), (0x15, "y"),
                             (0x16, "u"), (0x17, "i"), (0x18, "o"), (0x19, "p"),
                             (0x1E, "a"), (0x1F, "s"), (0x20, "d"), (0x21, "f"),
                             (0x22, "g"), (0x23, "h"), (0x24, "j"), (0x25, "k"),
                             (0x26, "l"), (0x2C, "z"), (0x2D, "x"), (0x2E, "c"),
                             (0x2F, "v"), (0x30, "b"), (0x31, "n"), (0x32, "m"),
                             (0x39, " "), (0x1C, "\n")):
                kb[code] = ord(ch)
            self.a.code += bytes(kb)
        self.emit_str_table()
        # print buffer + bump allocator state in data
        self.a.data_label("pbuf_")
        self.a.data_bytes(b"\0" * 32)
        self.a.data_label("pbuf_e")
        self.a.data_label("nbuf_")
        self.a.data_bytes(b"\0" * 32)
        self.a.data_label("nbuf_e")
        self.a.data_label("bump_ptr_")
        if self.freestanding:
            self.a.data_qword(Gen.KHEAP_BASE)
            self.a.data_label("bump_end_")
            self.a.data_qword(Gen.KHEAP_BASE + Gen.KHEAP_SIZE)
            # kernel device state: timer ticks, keyboard slot+flag, pmm
            for nm in ("ticks_", "keycode_", "keyflag_", "pmm_next_"):
                self.a.data_label(nm)
                self.a.data_qword(0)
            self.a.data_label("pmm_free_")
            self.a.data_qword(32768)
            # IDT (48 gates) + IDTR filled by build_xkernel
            self.reserve("idt_", 48 * 16)
            self.reserve("idtr_", 10)
        else:
            self.a.data_qword(0)
            self.a.data_label("bump_end_")
            self.a.data_qword(0)
        from x64 import layout, pack
        if self.freestanding:
            # kernel link done by build_xkernel (needs raw Asm + labels)
            return self.a
        lo = layout(len(self.a.code), len(self.a.data))
        code = self.a.resolve(lo["text_vaddr"], lo["data_vaddr"])
        start_off = self.a.labels["_start"]
        return pack(code, bytes(self.a.data), start_off, lo)

    def _def_nodes(self, mod):
        out = []
        def walk(body):
            for s in body:
                if s["t"] == "def":
                    out.append(s)
                    walk(s["body"])
                elif s["t"] == "if":
                    walk(s["then"])
                    for _, eb in s["elifs"]:
                        walk(eb)
                    walk(s["els"])
                elif s["t"] == "while":
                    walk(s["body"])
                elif s["t"] == "unsafe":
                    walk(s["body"])
        walk(mod["prog"])
        return out

    def k_write(self):
        # rsi=ptr, rdx=len -> serial bytes; clobbers rax rcx rdx rsi
        a = self.a
        a.mov_rr("rcx", "rdx")
        lab_l, lab_d = self.new_tmp("kw"), self.new_tmp("kw")
        a.label(lab_l)
        a.test_rr("rcx", "rcx")
        a.jcc("e", lab_d)
        a.movzx_eax_m8("rsi", 0)
        a.push_r("rsi")
        a.push_r("rcx")
        a.call("x_putc")
        a.pop_r("rcx")
        a.pop_r("rsi")
        a.add_ri32("rsi", 1)
        a.sub_ri32("rcx", 1)
        a.jmp(lab_l)
        a.label(lab_d)

    GPREGS = ("rax", "rcx", "rdx", "rbx", "rbp", "rsi", "rdi",
              "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15")

    def emit_irq_stubs(self):
        # IDT stubs for vectors 0..47. Timer(32)/keyboard(33) handled inline;
        # everything else reports EXC <n> and halts. Error-code vectors pop it.
        a = self.a
        ERRCODE = {8, 10, 11, 12, 13, 14, 17, 21, 29, 30}
        # common exception entry: rdi = vector (all GPRs already pushed)
        a.label("k_exc")
        a.lea_rip("rsi", "exc_")
        a.mov_ri32("rdx", 4)
        self.k_write()
        a.push_r("rdi")
        a.call("print_int")
        a.add_ri32("rsp", 8)
        a.mov_ri32("rax", 10)
        a.call("x_putc")
        a.call("k_halt")
        for vec in range(48):
            if vec in (32, 33):
                continue
            a.label(f"irq_stub_{vec}")
            if vec in ERRCODE:
                # drop CPU-pushed error code first (sits above our pushes)
                a.add_ri32("rsp", 8)
            for r in Gen.GPREGS:
                a.push_r(r)
            a.mov_ri32("rdi", vec)
            a.call("k_exc")
            # unreachable (k_exc halts)
        # timer IRQ0 -> vec 32: ticks_++, EOI, iret
        a.label("irq_stub_32")
        a.push_r("rax")
        a.inc_mrip("ticks_")
        a.mov_ri32("rax", 0x20)
        a.mov_ri16("dx", 0x20)
        a.out_dx_al()
        a.pop_r("rax")
        a.iretq()
        # keyboard IRQ1 -> vec 33: map scancode, store, EOI, iret
        a.label("irq_stub_33")
        for r in Gen.GPREGS:
            a.push_r(r)
        a.mov_ri16("dx", 0x60)
        a.in_al_dx()
        a.push_r("rax")  # save scancode
        a.lea_rip("rcx", "kbdmap_")
        a.pop_r("rax")
        a.movzx_eax_mx("rcx", "rax", 1, 0)  # al = map[scancode] (0 = unknown)
        a.test_rr("rax", "rax")
        lab_ign = self.new_tmp("kb")
        a.jcc("e", lab_ign)
        a.lea_rip("rcx", "keycode_")
        a.mov_mr8("rcx", 0, 0)  # keycode_ = al
        a.mov_ri32("rax", 1)
        a.lea_rip("rcx", "keyflag_")
        a.mov_mr("rcx", "rax", 0)  # flag = 1
        a.label(lab_ign)
        a.mov_ri32("rax", 0x20)
        a.mov_ri16("dx", 0x20)
        a.out_dx_al()  # EOI (al = 0x20)
        for r in reversed(Gen.GPREGS):
            a.pop_r(r)
        a.iretq()

    # ----- output primitives -----
    def rt_out(self, fd=1):
        """rdi = ptr, rsi = len -> write(fd). Clobbers caller-saved regs."""
        a = self.a
        a.mov_rr("rdx", "rsi")   # len
        a.mov_rr("rsi", "rdi")   # buf
        if self.freestanding:
            self.k_write()
        else:
            a.mov_ri32("rdi", fd)
            a.mov_ri32("rax", 1)
            a.syscall()

    def copy_bytes(self):
        """rsi = src, rdi = dst, rcx = len -> copy. Clobbers rax."""
        a = self.a
        lab_top, lab_done = self.new_tmp("cp"), self.new_tmp("cp")
        a.label(lab_top)
        a.test_rr("rcx", "rcx")
        a.jcc("e", lab_done)
        a.movzx_eax_m8("rsi", 0)
        a.mov_mr8("rdi", 0, 0)
        a.add_ri32("rsi", 1)
        a.add_ri32("rdi", 1)
        a.sub_ri32("rcx", 1)
        a.jmp(lab_top)
        a.label(lab_done)

    # ----- freestanding base runtime (serial COM1, fixed bump heap, halt) -----
    KHEAP_BASE = 0x2000000
    KHEAP_SIZE = 16 << 20

    def emit_runtime_fs(self):
        a = self.a
        # x_putc: al = char
        a.label("x_putc")
        a.push_r("rax")
        a.mov_ri16("dx", 0x3FD)
        lab_w = self.new_tmp("sw")
        a.label(lab_w)
        a.in_al_dx()
        a.test_al_imm8(0x20)
        a.jcc("e", lab_w)
        a.mov_ri16("dx", 0x3F8)
        a.pop_r("rax")
        a.out_dx_al()
        a.ret()
        # k_halt: cli; hlt forever
        a.label("k_halt")
        a.cli()
        lab_h = self.new_tmp("hh")
        a.label(lab_h)
        a.hlt()
        a.jmp(lab_h)
        # x_malloc: rdi = bytes -> fixed bump heap; halts on exhaustion
        a.label("x_malloc")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.mov_rr("rax", "rdi")
        a.add_ri32("rax", 15)
        a.and_ri32("rax", -16)
        a.push_r("rax")
        a.lea_rip("rcx", "bump_ptr_")
        a.mov_rm("rcx", "rcx", 0)
        a.mov_rm("rax", "rbp", -8)
        a.add_rr("rax", "rcx")
        a.push_r("rax")
        a.push_r("rcx")
        a.lea_rip("rdx", "bump_end_")
        a.mov_rm("rdx", "rdx", 0)
        a.pop_r("rcx")
        a.pop_r("rax")
        a.cmp_rr("rax", "rdx")
        lab_fit = self.new_tmp("ba")
        a.jcc("be", lab_fit)
        a.lea_rip("rsi", "oom_")
        a.call("k_puts_cstr")
        a.call("k_halt")
        a.label(lab_fit)
        a.lea_rip("rdx", "bump_ptr_")
        a.mov_mr("rdx", "rax", 0)
        a.mov_rr("rax", "rcx")
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # k_puts_cstr: rsi = NUL-terminated cstr -> serial; clobbers rax rcx rdx
        a.label("k_puts_cstr")
        a.push_r("rsi")
        lab_kl = self.new_tmp("kc")
        a.label(lab_kl)
        a.movzx_eax_m8("rsi", 0)
        a.test_rr("rax", "rax")
        lab_kd = self.new_tmp("kc")
        a.jcc("e", lab_kd)
        a.push_r("rsi")
        a.call("x_putc")
        a.pop_r("rsi")
        a.add_ri32("rsi", 1)
        a.jmp(lab_kl)
        a.label(lab_kd)
        a.pop_r("rsi")
        a.ret()
        # x_alloc wrapper
        a.label("x_alloc")
        a.mov_rm("rdi", "rsp", 8)
        a.call("x_malloc")
        a.ret()
        # divzero trap (freestanding: #DE is caught by the IDT stub)
        a.label("divzero")
        a.lea_rip("rsi", "dzm_")
        a.call("k_puts_cstr")
        a.call("k_halt")
        self.emit_fmt_int()
        self.emit_print_int()
        self.emit_val_runtime()
        # oom_ / dzm_ cstrs emitted with rodata in build_image

    def emit_runtime(self):
        a = self.a
        # x_malloc: rdi = bytes -> bump pointer over 16MB mmap arenas.
        # Never frees (arena semantics, like the kernel heap). exit(99) on failure.
        a.label("x_malloc")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.mov_rr("rax", "rdi")
        a.add_ri32("rax", 15)
        a.and_ri32("rax", -16)
        a.push_r("rax")  # [rbp-8] = aligned size
        a.lea_rip("rcx", "bump_ptr_")
        a.mov_rm("rcx", "rcx", 0)
        a.test_rr("rcx", "rcx")
        lab_have = self.new_tmp("ba")
        a.jcc("ne", lab_have)
        a.label("new_arena_")
        a.mov_rm("rsi", "rbp", -8)
        a.cmp_ri32("rsi", 16777216)
        lab_mg = self.new_tmp("ba")
        a.jcc("ae", lab_mg)
        a.mov_ri32("rsi", 16777216)
        a.label(lab_mg)
        a.push_r("rsi")  # mapped len
        a.mov_ri32("rdi", 0)
        a.mov_ri32("rdx", 3)
        a.mov_ri32("r10", 0x22)
        a.mov_ri32("r8", -1)
        a.mov_ri32("r9", 0)
        a.mov_ri32("rax", 9)
        a.syscall()
        a.test_rr("rax", "rax")
        lab_ok = self.new_tmp("ba")
        a.jcc("ns", lab_ok)
        a.mov_ri32("rdi", 99)
        a.mov_ri32("rax", 60)
        a.syscall()
        a.label(lab_ok)
        a.pop_r("rsi")  # mapped len
        a.mov_rr("rcx", "rax")
        a.add_rr("rcx", "rsi")  # rcx = end
        a.lea_rip("rdx", "bump_end_")
        a.mov_mr("rdx", "rcx", 0)
        a.lea_rip("rdx", "bump_ptr_")
        a.mov_mr("rdx", "rax", 0)
        a.mov_rr("rcx", "rax")  # rcx = base for the have path
        a.label(lab_have)
        a.mov_rm("rax", "rbp", -8)  # size
        a.add_rr("rax", "rcx")  # rax = base + size
        a.push_r("rax")
        a.push_r("rcx")
        a.lea_rip("rdx", "bump_end_")
        a.mov_rm("rdx", "rdx", 0)
        a.pop_r("rcx")
        a.pop_r("rax")
        a.cmp_rr("rax", "rdx")
        lab_fit = self.new_tmp("ba")
        a.jcc("be", lab_fit)
        a.jmp("new_arena_")  # abandon the old arena (size still at [rbp-8])
        a.label(lab_fit)
        a.lea_rip("rdx", "bump_ptr_")
        a.mov_mr("rdx", "rax", 0)
        a.mov_rr("rax", "rcx")  # return base
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_alloc: [rsp+8] = bytes (unsafe calling convention)
        a.label("x_alloc")
        a.mov_rm("rdi", "rsp", 8)
        a.call("x_malloc")
        a.ret()
        # divzero: clean division-by-zero trap
        a.label("divzero")
        lab_dz = self.rstr("division by zero\n")
        a.lea_rip("rdi", lab_dz)
        a.mov_ri32("rsi", 17)
        self.rt_out(2)
        a.mov_ri32("rdi", 1)
        a.mov_ri32("rax", 60)
        a.syscall()
        self.emit_fmt_int()
        self.emit_print_int()
        self.emit_val_runtime()

    def emit_fmt_int(self):
        """fmt_int: rdi = i64, rsi = buf_end -> rsi = start, rdx = length."""
        a = self.a
        a.label("fmt_int")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.push_r("rsi")            # [rbp-8] = buf_end
        a.mov_rr("rax", "rdi")
        a.test_rr("rax", "rax")
        lab_nz, lab_lp, lab_dn = (self.new_tmp("fi"), self.new_tmp("fi"),
                                  self.new_tmp("fi"))
        a.jcc("ne", lab_nz)
        a.sub_ri32("rsi", 1)
        a.mov_ri32("rcx", 48)      # '0'
        a.mov_mr8("rsi", 1, 0)     # [rsi] = cl
        a.jmp(lab_dn)
        a.label(lab_nz)
        a.mov_ri32("rcx", 0)       # sign flag
        a.jcc("ns", lab_lp)
        a.neg_r("rax")
        a.mov_ri32("rcx", 1)
        a.label(lab_lp)
        a.mov_ri32("r8", 10)
        a.mov_ri32("rdx", 0)
        a.div_r("r8")              # rax = q, rdx = digit
        a.add_ri8("rdx", 48)
        a.push_r("rax")
        a.mov_rr("rax", "rdx")
        a.sub_ri32("rsi", 1)
        a.mov_mr8("rsi", 0, 0)     # [rsi] = al (the digit)
        a.pop_r("rax")
        a.test_rr("rax", "rax")
        a.jcc("ne", lab_lp)
        a.test_rr("rcx", "rcx")
        a.jcc("e", lab_dn)
        a.sub_ri32("rsi", 1)
        a.mov_ri32("rcx", 45)      # '-'
        a.mov_mr8("rsi", 1, 0)
        a.label(lab_dn)
        a.mov_rm("rdx", "rbp", -8)
        a.sub_rr("rdx", "rsi")     # length
        a.add_ri32("rsp", 8)
        a.pop_r("rbp")
        a.ret()                    # rsi = start, rdx = length

    def emit_print_int(self):
        """print_int: [rsp+8] = i64 -> decimal to stdout (or serial)."""
        a = self.a
        a.label("print_int")
        a.mov_rm("rdi", "rsp", 8)
        a.lea_rip("rsi", "pbuf_e")
        a.call("fmt_int")
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rdx")
        self.rt_out()
        a.ret()

    # ----- tagged-value runtime (shared: hosted stdout + freestanding serial) -----
    def emit_val_runtime(self):
        a = self.a
        I, B, N, KS = Gen.TAG_INT, Gen.TAG_BOOL, Gen.TAG_NULL, Gen.K_STR
        # type_err: report then die
        a.label("type_err")
        lab = self.rstr("type error\n")
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", 11)
        self.rt_out(2)
        if self.freestanding:
            a.call("k_halt")
        else:
            a.mov_ri32("rdi", 1)
            a.mov_ri32("rax", 60)
            a.syscall()
        # x_truth: rdi = tagged -> rax = 0/1
        a.label("x_truth")
        a.mov_rr("rax", "rdi")
        a.and_ri32("rax", 3)
        lab_int, lab_bool, lab_null, lab_heap = (self.new_tmp("tr"),
                                                 self.new_tmp("tr"),
                                                 self.new_tmp("tr"),
                                                 self.new_tmp("tr"))
        lab_bad_truth = self.new_tmp("tr")
        a.cmp_ri32("rax", I)
        a.jcc("e", lab_int)
        a.cmp_ri32("rax", B)
        a.jcc("e", lab_bool)
        a.cmp_ri32("rax", N)
        a.jcc("e", lab_null)
        a.test_rr("rax", "rax")
        a.jcc("e", lab_heap)
        a.jmp("type_err")
        a.label(lab_int)
        a.mov_rr("rax", "rdi")
        a.sar_ri8("rax", 2)
        a.test_rr("rax", "rax")
        a.setcc_al("ne")
        a.movzx_eax_al()
        a.ret()
        a.label(lab_bool)
        a.mov_rr("rax", "rdi")
        a.and_ri32("rax", 8)
        a.shr_ri8("rax", 3)
        a.ret()
        a.label(lab_null)
        a.xor_rr("rax", "rax")
        a.ret()
        a.label(lab_heap)
        a.mov_rm("rax", "rdi", 0)       # kind
        a.cmp_ri32("rax", KS)
        a.jcc("ne", lab_bad_truth)
        a.mov_rm("rax", "rdi", 8)       # len
        a.test_rr("rax", "rax")
        a.setcc_al("ne")
        a.movzx_eax_al()
        a.ret()
        a.label(lab_bad_truth)
        a.jmp("type_err")
        # print_val: rdi = tagged -> prints without newline
        a.label("print_val")
        a.mov_rr("r10", "rdi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        lab_pv_int, lab_pv_bool = self.new_tmp("pv"), self.new_tmp("pv")
        lab_pv_null, lab_pv_heap, lab_pv_out = (self.new_tmp("pv"),
                                                self.new_tmp("pv"),
                                                self.new_tmp("pv"))
        lab_pv_unb, lab_pv_bad = self.new_tmp("pv"), self.new_tmp("pv")
        lab_pv_done = self.new_tmp("pv")
        a.cmp_ri32("rax", I)
        a.jcc("e", lab_pv_int)
        a.cmp_ri32("rax", B)
        a.jcc("e", lab_pv_bool)
        a.cmp_ri32("rax", N)
        a.jcc("e", lab_pv_null)
        a.test_rr("rax", "rax")
        a.jcc("e", lab_pv_heap)
        a.jmp("type_err")
        a.label(lab_pv_int)
        a.mov_rr("rdi", "r10")
        a.sar_ri8("rdi", 2)
        a.push_r("rdi")
        a.call("print_int")
        a.add_ri32("rsp", 8)
        a.ret()
        a.label(lab_pv_bool)
        a.lea_rip("rdi", self.rstr("false"))
        a.mov_ri32("rsi", 5)
        a.cmp_ri32("r10", Gen.HS_TRUE)
        a.jcc("ne", lab_pv_out)
        a.lea_rip("rdi", self.rstr("true"))
        a.mov_ri32("rsi", 4)
        a.jmp(lab_pv_out)
        a.label(lab_pv_null)
        a.lea_rip("rdi", self.rstr("null"))
        a.mov_ri32("rsi", 4)
        a.cmp_ri32("r10", Gen.HS_NULL)
        a.jcc("ne", lab_pv_unb)
        a.jmp(lab_pv_out)
        a.label(lab_pv_unb)
        a.lea_rip("rdi", self.rstr("unbound"))
        a.mov_ri32("rsi", 7)
        a.jmp(lab_pv_out)
        a.label(lab_pv_heap)
        a.mov_rm("rax", "r10", 0)
        a.cmp_ri32("rax", KS)
        a.jcc("ne", lab_pv_bad)
        a.mov_rm("rsi", "r10", 8)      # len
        a.mov_rr("rdi", "r10")
        a.add_ri32("rdi", 16)          # bytes
        a.label(lab_pv_out)
        a.test_rr("rsi", "rsi")
        a.jcc("e", lab_pv_done)
        self.rt_out()
        a.label(lab_pv_done)
        a.ret()
        a.label(lab_pv_bad)
        a.jmp("type_err")
        # x_str_at: rdi = bytes, rsi = len -> rax = Str object
        a.label("x_str_at")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 32)
        a.mov_mr("rbp", "rdi", -8)     # src
        a.mov_mr("rbp", "rsi", -16)    # len
        a.mov_rr("rax", "rsi")
        a.add_ri32("rax", 48)          # 16 header + payload + slack
        a.and_ri32("rax", -16)
        a.mov_rr("rdi", "rax")
        a.call("x_malloc")
        a.mov_mr("rbp", "rax", -24)    # obj
        a.mov_ri32("rcx", 0)
        a.mov_mr("rax", "rcx", 0)      # kind = K_STR
        a.mov_rm("rcx", "rbp", -16)
        a.mov_mr("rax", "rcx", 8)      # len
        a.lea_m("rdi", "rax", 16)
        a.mov_rm("rsi", "rbp", -8)
        a.mov_rm("rcx", "rbp", -16)
        self.copy_bytes()
        a.mov_rm("rax", "rbp", -24)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_str_cat: rdi = a, rsi = b -> rax = Str
        a.label("x_str_cat")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 40)
        a.mov_mr("rbp", "rdi", -8)
        a.mov_mr("rbp", "rsi", -16)
        a.mov_rm("rax", "rdi", 8)      # len a
        a.mov_rm("rcx", "rsi", 8)      # len b
        a.mov_mr("rbp", "rcx", -24)    # len b
        a.mov_mr("rbp", "rax", -32)    # len a
        a.add_rr("rax", "rcx")
        a.add_ri32("rax", 48)
        a.and_ri32("rax", -16)
        a.mov_rr("rdi", "rax")
        a.call("x_malloc")
        a.mov_mr("rbp", "rax", -40)    # obj
        a.mov_ri32("rcx", 0)
        a.mov_mr("rax", "rcx", 0)
        a.mov_rm("rcx", "rbp", -32)
        a.mov_rm("r11", "rbp", -24)
        a.add_rr("rcx", "r11")
        a.mov_mr("rax", "rcx", 8)      # len = la + lb
        # copy a: src = a.data (obj + 16), dst = new + 16
        a.lea_m("rdi", "rax", 16)
        a.mov_rm("rsi", "rbp", -8)
        a.add_ri32("rsi", 16)
        a.mov_rm("rcx", "rbp", -32)
        self.copy_bytes()
        # copy b: src = b.data, dst = new + 16 + len_a
        a.mov_rm("rax", "rbp", -40)
        a.mov_rm("rcx", "rbp", -32)
        a.lea_m("rdi", "rax", 16, "rcx", 1)
        a.mov_rm("rsi", "rbp", -16)
        a.add_ri32("rsi", 16)
        a.mov_rm("rcx", "rbp", -24)
        self.copy_bytes()
        a.mov_rm("rax", "rbp", -40)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_str_cmp: rdi = a, rsi = b -> eax in {-1, 0, 1}
        a.label("x_str_cmp")
        a.mov_rr("r10", "rdi")
        a.mov_rr("r11", "rsi")
        a.mov_rm("rax", "r10", 8)      # len a
        a.mov_rm("rcx", "r11", 8)      # len b
        a.cmp_rr("rax", "rcx")
        lab_len, lab_eq = self.new_tmp("sm"), self.new_tmp("sm")
        lab_loop, lab_diff = self.new_tmp("sm"), self.new_tmp("sm")
        lab_fin = self.new_tmp("sm")
        a.jcc("ne", lab_len)
        a.mov_ri32("rcx", 0)
        a.label(lab_loop)
        a.cmp_rr("rcx", "rax")
        a.jcc("ae", lab_eq)
        a.movzx_eax_mx("r10", "rcx", 1, 16)
        a.movzx_edx_mx("r11", "rcx", 1, 16)
        a.code += bytes([0x38, 0xD0])  # cmp al, dl
        a.jcc("ne", lab_diff)
        a.add_ri32("rcx", 1)
        a.jmp(lab_loop)
        a.label(lab_diff)
        a.code += bytes([0x38, 0xD0])  # cmp al, dl (flags again)
        a.mov_ri32("rax", 1)
        a.jcc("g", lab_fin)           # al > dl -> 1
        a.mov_ri32("rax", -1)
        a.jmp(lab_fin)
        a.label(lab_eq)
        a.mov_ri32("rax", 0)
        a.jmp(lab_fin)
        a.label(lab_len)
        a.mov_rm("rax", "r10", 8)
        a.mov_rm("rcx", "r11", 8)
        a.cmp_rr("rax", "rcx")
        a.mov_ri32("rax", 1)
        a.jcc("a", lab_fin)           # len a > len b -> 1
        a.mov_ri32("rax", -1)
        a.label(lab_fin)
        a.ret()
        # x_eq: rdi = a, rsi = b -> al = 0/1
        a.label("x_eq")
        a.mov_rr("r10", "rdi")
        a.mov_rr("r11", "rsi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.cmp_ri32("rax", I)
        lab_eq_h1, lab_eq_h2 = self.new_tmp("eq"), self.new_tmp("eq")
        a.jcc("ne", lab_eq_h1)
        a.mov_rr("rax", "r11")
        a.and_ri32("rax", 3)
        a.cmp_ri32("rax", I)
        a.jcc("ne", lab_eq_h2)
        a.mov_rr("rax", "r10")
        a.sar_ri8("rax", 2)
        a.mov_rr("rcx", "r11")
        a.sar_ri8("rcx", 2)
        a.cmp_rr("rax", "rcx")
        a.setcc_al("e")
        a.movzx_eax_al()
        a.ret()
        a.label(lab_eq_h1)
        a.mov_rr("rax", "r11")
        a.and_ri32("rax", 3)
        a.cmp_ri32("rax", I)
        a.jcc("ne", lab_eq_h2)
        a.mov_ri32("rax", 0)   # Int vs non-Int
        a.ret()
        a.label(lab_eq_h2)
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.jcc("ne", "eq_raw")      # not a heap value -> raw tag compare
        a.mov_rr("rax", "r11")
        a.and_ri32("rax", 3)
        a.jcc("ne", "eq_raw")
        a.mov_rm("rax", "r10", 0)
        a.mov_rm("rcx", "r11", 0)
        a.cmp_rr("rax", "rcx")
        a.jcc("ne", "eq_raw")
        a.cmp_ri32("rax", KS)
        a.jcc("ne", "eq_raw")
        a.mov_rr("rdi", "r10")
        a.mov_rr("rsi", "r11")
        a.call("x_str_cmp")
        a.test_rr("rax", "rax")
        a.setcc_al("e")
        a.movzx_eax_al()
        a.ret()
        a.label("eq_raw")
        a.cmp_rr("r10", "r11")
        a.setcc_al("e")
        a.movzx_eax_al()
        a.ret()
        # x_cmp: rdi = a, rsi = b -> eax in {-1, 0, 1} (Int or Str only)
        a.label("x_cmp")
        a.mov_rr("r10", "rdi")
        a.mov_rr("r11", "rsi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.cmp_ri32("rax", I)
        a.jcc("ne", "cm_str")
        a.mov_rr("rax", "r11")
        a.and_ri32("rax", 3)
        a.cmp_ri32("rax", I)
        a.jcc("ne", "cm_str")
        a.mov_rr("rax", "r10")
        a.sar_ri8("rax", 2)
        a.mov_rr("rcx", "r11")
        a.sar_ri8("rcx", 2)
        a.cmp_rr("rax", "rcx")
        a.mov_ri32("rax", 1)
        a.jcc("g", "cm_fin")
        a.mov_ri32("rax", 0)
        a.jcc("e", "cm_fin")
        a.mov_ri32("rax", -1)
        a.jmp("cm_fin")
        a.label("cm_str")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.jcc("ne", "cm_bad")
        a.mov_rr("rax", "r11")
        a.and_ri32("rax", 3)
        a.jcc("ne", "cm_bad")
        a.mov_rm("rax", "r10", 0)
        a.mov_rm("rcx", "r11", 0)
        a.cmp_rr("rax", "rcx")
        a.jcc("ne", "cm_bad")
        a.cmp_ri32("rax", KS)
        a.jcc("ne", "cm_bad")
        a.mov_rr("rdi", "r10")
        a.mov_rr("rsi", "r11")
        a.call("x_str_cmp")
        a.jmp("cm_fin")
        a.label("cm_bad")
        a.jmp("type_err")
        a.label("cm_fin")
        a.ret()
        # x_len: rdi = Str -> rax = tagged Int
        a.label("x_len")
        lab_len_bad = self.new_tmp("ln")
        a.mov_rr("r10", "rdi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.test_rr("rax", "rax")
        a.jcc("ne", lab_len_bad)
        a.mov_rm("rcx", "r10", 0)
        a.cmp_ri32("rcx", KS)
        a.jcc("ne", lab_len_bad)
        a.mov_rm("rax", "r10", 8)
        a.shl_ri8("rax", 2)
        a.or_ri8("rax", 1)
        a.ret()
        a.label(lab_len_bad)
        a.jmp("type_err")
        # x_str: rdi = any tagged value -> rax = Str
        a.label("x_str")
        a.mov_rr("r10", "rdi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.cmp_ri32("rax", I)
        a.jcc("e", "st_int")
        a.cmp_ri32("rax", B)
        a.jcc("e", "st_bool")
        a.cmp_ri32("rax", N)
        a.jcc("e", "st_null")
        a.test_rr("rax", "rax")
        a.jcc("ne", "st_bad")
        a.mov_rm("rax", "r10", 0)
        a.cmp_ri32("rax", KS)
        a.jcc("ne", "st_bad")
        a.mov_rr("rax", "r10")
        a.ret()
        a.label("st_int")
        a.mov_rr("rdi", "r10")
        a.sar_ri8("rdi", 2)
        a.lea_rip("rsi", "nbuf_e")
        a.call("fmt_int")
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rdx")
        a.jmp("st_make")
        a.label("st_bool")
        a.lea_rip("rdi", self.rstr("false"))
        a.mov_ri32("rsi", 5)
        a.cmp_ri32("r10", Gen.HS_TRUE)
        a.jcc("ne", "st_make")
        a.lea_rip("rdi", self.rstr("true"))
        a.mov_ri32("rsi", 4)
        a.jmp("st_make")
        a.label("st_null")
        a.lea_rip("rdi", self.rstr("null"))
        a.mov_ri32("rsi", 4)
        a.cmp_ri32("r10", Gen.HS_NULL)
        a.jcc("ne", "st_ub")
        a.jmp("st_make")
        a.label("st_ub")
        a.lea_rip("rdi", self.rstr("unbound"))
        a.mov_ri32("rsi", 7)
        a.jmp("st_make")
        a.label("st_make")
        a.call("x_str_at")
        a.ret()
        a.label("st_bad")
        a.jmp("type_err")
        # x_num_to_str: rdi = raw i64 -> rax = Str
        a.label("x_num_to_str")
        a.lea_rip("rsi", "nbuf_e")
        a.call("fmt_int")
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rdx")
        a.call("x_str_at")
        a.ret()


def build_x64(prog_path, out_path):
    import os as _os
    interp.reset_parse_state()
    try:
        with open(prog_path, encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"error: cannot read {prog_path}: {e.strerror or e}", file=sys.stderr)
        return 1
    try:
        prog = interp.parse_program(src)
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    g = Gen(prog, prog_path)
    mod = {"name": "<main>", "prog": prog, "pfx": "",
           "scope": Gen.Scope(),
           "dir": _os.path.dirname(_os.path.abspath(prog_path))}
    try:
        img = g.build_image(mod)
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    with open(out_path, "wb") as f:
        f.write(img)
    _os.chmod(out_path, 0o755)
    print(f"ok: x64 -> {out_path} ({len(img)} bytes, no gcc)")
    return 0


# ---------- freestanding kernel link ----------
KBASE = 0x100000
KSTACK_SIZE = 16384
KTABLE_PAGES = 3


def build_xkernel(prog_path, out_path):
    import os as _os
    import struct as _st
    from x64 import Asm32, link_elf32
    interp.reset_parse_state()
    try:
        with open(prog_path, encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"error: cannot read {prog_path}: {e.strerror or e}", file=sys.stderr)
        return 1
    try:
        prog = interp.parse_program(src)
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    g = Gen(prog, prog_path, freestanding=True)
    mod = {"name": "<main>", "prog": prog, "pfx": "",
           "scope": Gen.Scope(),
           "dir": _os.path.dirname(_os.path.abspath(prog_path))}
    try:
        asm64 = g.build_image(mod)
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    # ---- layout (file offset == vaddr offset from KBASE) ----
    HDR = 52 + 2 * 32
    mb2 = _st.pack("<IIII", 0xE85250D6, 0, 24, (-(0xE85250D6 + 24)) & 0xFFFFFFFF)
    mb2 += _st.pack("<HHI", 0, 0, 8)
    mb1 = _st.pack("<III", 0x1BADB002, 0, (-0x1BADB002) & 0xFFFFFFFF)
    off = HDR
    while off % 8:
        off += 1
    mb_off, off = off, off + len(mb2)
    mb1_off, off = off, off + len(mb1)
    boot_off = off
    # assemble boot32 (labels relative; abs resolved at link)
    b = Asm32()
    b.label("_start")
    b.cli()
    b.mov_ri32_abs(4, "STACK_TOP")  # esp; patched below (abs32 to constant)
    b.mov_rr(6, 0)   # esi = eax (magic)
    b.mov_rr(2, 3)   # edx = ebx (info)
    b.mov_ri32_abs(0, "PML4")
    b.mov_cr(3, 0)
    b.mov_rcr(0, 4)
    b.or_ri32(0, 0x620)
    b.mov_cr(4, 0)
    b.mov_ri32(1, 0xC0000080)
    b.rdmsr()
    b.or_ri32(0, 0x100)
    b.wrmsr()
    b.mov_rcr(0, 0)
    b.or_ri32(0, 0x80000001)
    b.mov_cr(0, 0)
    b.lgdt_abs("GDT_PTR")
    b.jmp_far_abs(0x08, 0)  # patched below
    boot_len = None  # filled after resolve
    # gdt + payload + data + tables + stack
    gdt = (b"\0" * 8 + _st.pack("<Q", 0x00209A0000000000)
           + _st.pack("<Q", 0x0000920000000000))
    # payload/data/table/stack offsets computed after boot assembled
    boot_code = b.code  # labels relative; resolve later with abs map
    off = boot_off + len(boot_code)
    while off % 8:
        off += 1
    gdt_off, off = off, off + len(gdt) + 10  # + gdt_ptr (limit16+base64)
    pay_off = off
    pay_len = len(asm64.code)
    off += pay_len
    dat_off = off
    dat_len = len(asm64.data)
    off += dat_len
    while off % 4096:
        off += 1
    tbl_off, off = off, off + 4096 * KTABLE_PAGES
    stack_size = KSTACK_SIZE
    stack_top = KBASE + off + stack_size
    # absolute addresses
    A = lambda o: KBASE + o
    # patch boot32 symbolic constants: use abs32 labels mapped to constants
    b.labels["STACK_TOP"] = stack_top - KBASE  # abs32 -> base + this
    b.labels["PML4"] = (A(tbl_off) - KBASE)
    b.labels["GDT_PTR"] = (A(gdt_off + len(gdt)) - KBASE)
    boot_bin = b.resolve(KBASE)
    # far jmp target: long_mode at payload start
    lm_addr = A(pay_off) + asm64.labels["long_mode"]
    # jmp_far_abs emitted with addr 0; patch last 6 bytes
    boot_bin = boot_bin[:-6] + _st.pack("<IH", lm_addr, 0x08)
    # stack_top mov: patch abs32
    # (mov_ri32_abs STACK_TOP already resolved via labels map above)
    # gdt_ptr bytes
    gdt_ptr = _st.pack("<H", len(gdt) + 10 - 1 - 10 + 24 - 1)  # limit = 24-1
    gdt_ptr = _st.pack("<H", 23) + _st.pack("<Q", A(gdt_off))
    # page tables (prefilled): PML4[0]->PDPT, PDPT[0]->PD, PD identity 1GB
    tbl = bytearray(4096 * KTABLE_PAGES)
    pdpt_a, pd_a = A(tbl_off + 4096), A(tbl_off + 8192)
    _st.pack_into("<Q", tbl, 0, pdpt_a | 3)
    _st.pack_into("<Q", tbl, 4096, pd_a | 3)
    for i in range(512):
        _st.pack_into("<Q", tbl, 8192 + 8 * i, (i * 0x200000) | 0x83)
    # resolve payload rip-relative labels, then patch stack_top placeholder
    pay_vaddr, dat_vaddr = A(pay_off), A(dat_off)
    # IDT (48 gates) + IDTR into reserved payload data
    idt_off = asm64.data_labels["idt_"]
    idtr_off = asm64.data_labels["idtr_"]
    idt = bytearray(48 * 16)
    for vec in range(48):
        addr = pay_vaddr + asm64.labels[f"irq_stub_{vec}"]
        idt[vec * 16:vec * 16 + 16] = _st.pack(
            "<HHBBHI", addr & 0xFFFF, 0x08, 0, 0x8E,
            (addr >> 16) & 0xFFFF, (addr >> 32) & 0xFFFFFFFF) + b"\0\0\0\0"
    asm64.data[idt_off:idt_off + 768] = idt
    asm64.data[idtr_off:idtr_off + 10] = (
        _st.pack("<H", 48 * 16 - 1) + _st.pack("<Q", dat_vaddr + idt_off))
    code = bytearray(asm64.resolve(pay_vaddr, dat_vaddr))
    code[g._stack_patch_pos:g._stack_patch_pos + 8] = _st.pack("<Q", stack_top)
    code = bytes(code)
    data = bytes(asm64.data)
    # text segment: headers area + mb + boot + gdt + payload, ending at dat_off
    # ---- assemble file: seg1 RX covers [0, T), seg2 RW covers [T, ...) ----
    # vaddr == KBASE + fileoff everywhere (single identity space).
    text = b"\0" * (mb_off - 116)
    text += mb2 + mb1
    text += b"\0" * (boot_off - (mb_off + len(mb2) + len(mb1)))
    text += boot_bin
    text += b"\0" * (gdt_off - 116 - len(text))
    text += gdt + gdt_ptr
    text += b"\0" * (pay_off - 116 - len(text))
    text += code
    text += b"\0" * (dat_off - 116 - len(text))
    assert 116 + len(text) == dat_off
    file_data = data + b"\0" * (tbl_off - dat_off - len(data)) + bytes(tbl)
    assert dat_off + len(file_data) == tbl_off + 4096 * KTABLE_PAGES
    t_filesz = 116 + len(text)
    d_off = t_filesz
    eh = _st.pack("<16sHHIIIIIHHHHHH", b"\x7fELF\x01\x01\x01" + b"\0" * 9,
                  2, 3, 1, KBASE + boot_off, 52, 0, 0, 52, 32, 2, 0, 0, 0)
    ph1 = _st.pack("<IIIIIIII", 1, 0, KBASE, KBASE,
                   t_filesz, t_filesz, 5, 0x1000)
    ph2 = _st.pack("<IIIIIIII", 1, d_off, KBASE + d_off, KBASE + d_off,
                   len(file_data), len(file_data) + stack_size, 6, 0x1000)
    img = bytearray()
    img += eh + ph1 + ph2
    assert len(img) == 116
    img += text + file_data
    with open(out_path, "wb") as f:
        f.write(bytes(img))
    print(f"ok: xkernel -> {out_path} ({len(img)} bytes, no gcc/as/ld)")
    return 0

