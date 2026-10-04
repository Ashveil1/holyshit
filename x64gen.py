#!/usr/bin/env python3
"""x64gen: holyshit subset -> x86-64 machine code (no gcc/as/ld/libc).

Subset (compile error otherwise): Int/Str/List/Bool/Null values,
def/call/recursion (closures supported via caps), if/while/for/break/continue,
try/except/finally is BANNED, modules/import, unsafe I64/U64/Ptr + structs,
print/int()/argv(), no Float/Dict/extern/slice/attr.
`/` is truncating int division (differs from main backends: documented).

Values are tagged with the low 2 bits (see TAG_* below):
  00 heap object ptr (8-aligned) | 01 Int (62-bit payload, value = word >> 2)
  10 Bool: 0x02 false, 0x0A true | 11 Null 0x03 / Unbound 0x0B
  Heap obj: [kind:u64][payload...]; kind 0 = Str{len,bytes},
  1 = Func{code,caps}, 2 = List{len,cap,buf}.
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
        self.loop_trys = []  # try_depth at each enclosing loop
        self.try_n = 0
        self.try_depth = 0  # lexical try nesting during emission
        self.exc_used = False  # try or raise present: emit exception runtime
        self._fin_stack = []  # (loop_depth, fbody) lexically enclosing emission
        self._fin_active = set()  # ids of fbody nodes currently being emitted
        self._except_stack = []  # HSTry frame vars lexically enclosing emission
        self.reads = []  # (scope, name) var reads for capture analysis
        self.all_fs = []  # function scopes in scan order
        self.flabels = {}  # id(fs) -> code label
        self.mod_bindings = {}  # (id(scope), name) -> mod dict (import bindings)
        self.shell_mods = {}  # dotted name -> empty package mod (no body)

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
    K_STR, K_FUNC, K_LIST = 0, 1, 2

    class Scope:
        def __init__(self, parent=None, is_func=False):
            self.parent = parent
            self.is_func = is_func
            self._mod = None  # owning module dict (set by collect/build_image)
            self.parent = parent
            self.is_func = is_func
            self.params = []
            self.loc = {}  # dynamic name -> rbp offset (negative)
            self.uloc = {}  # unsafe static name -> rbp offset (negative)
            self.utypes = {}  # unsafe static name -> I64/U64/Ptr/Ptr:X
            self.globs = set()  # names declared global here
            # names whose slot holds a raw machine word (assigned inside
            # `unsafe:`), so unsafe reads must not unbox them
            self.raw_names = set()
            self.nloc = 0

    def slot(self, sc):
        sc.nloc += 1
        return -8 * sc.nloc

    def collect(self, body, sc):
        for s in body:
            t = s["t"]
            if t == "def":
                self.decl(sc, s["name"])
                self.drop_binding(sc, s["name"])
                fs = Gen.Scope(parent=sc, is_func=True)
                fs._mod = sc._mod
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
                self.drop_binding(sc, s["name"])
                self.decl(sc, s["name"])
            elif t == "for":
                self.ann_expr(s["iter"], sc)
                self.drop_binding(sc, s["var"])
                self.decl(sc, s["var"])
                # hidden loop state (frame slots, allocated now so the
                # function prologue reserves them): range end / str obj+idx
                s["_f0"] = self.slot(sc)
                s["_f1"] = self.slot(sc)
                self.collect(s["body"], sc)
            elif t == "try":
                self.exc_used = True
                self.collect(s["body"], sc)
                if s.get("ebody") is not None:
                    if s.get("ename") is not None:
                        # `as e` binds in the current scope (blocks share it);
                        # same-scope rebinding needs save/restore around ebody
                        s["_eshadow"] = (s["ename"] in sc.loc or
                                         s["ename"] in sc.uloc or
                                         s["ename"] in sc.params)
                        s["_esave"] = self.slot(sc)
                        self.decl(sc, s["ename"])
                    self.collect(s["ebody"], sc)
                if s.get("fbody") is not None:
                    self.collect(s["fbody"], sc)
            elif t == "raise":
                self.exc_used = True
                if s["val"] is not None:
                    self.ann_expr(s["val"], sc)
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
                srcmod = sc._mod
                from_dir = srcmod["dir"] if srcmod else None
                topmod, chain = self.ensure_prefixes(s["name"], from_dir, s["line"])
                for m in chain:
                    if m.get("collected"):
                        continue
                    if m.get("busy"):
                        raise HSErr(f"circular import '{m['name']}'", s["line"])
                    m["busy"] = True
                    msc = Gen.Scope()
                    msc._mod = m
                    m["scope"] = msc
                    try:
                        self.collect(m["prog"], msc)
                    finally:
                        del m["busy"]
                    m["collected"] = True
                s["_mods"] = chain  # real mods, parent-first: init in order
                top = s["name"].split(".")[0]
                if self.resolve_var(top, sc, srcmod, s["line"])[0] is not None:
                    raise HSErr(f"cannot import '{s['name']}': '{top}' is already defined",
                                s["line"])
                self.mod_bindings[(id(sc), top)] = topmod
                # mirror interp: the imported name is also visible as an
                # attribute of the importing module (mid.leaf works)
                if srcmod is not None:
                    srcmod.setdefault("imports", {})[top] = topmod
            elif t == "return":
                if s["val"] is not None:
                    self.ann_expr(s["val"], sc)
            elif t == "setindex":
                self.ann_expr(s["obj"], sc)
                self.ann_expr(s["idx"], sc)
                self.ann_expr(s["val"], sc)
            elif t == "setattr":
                self.ann_expr(s["obj"], sc)
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
                    sc.raw_names.add(s["name"])
                    # module-visible: a name assigned raw in ANY function of
                    # this module holds a raw word for every reader in it
                    # (e.g. std.heap.free_head, written by malloc/free but
                    # only read by heap_free/heap_nblocks)
                    m = sc
                    while m.parent is not None:
                        m = m.parent
                    m.raw_names.add(s["name"])
                elif t == "global":
                    sc.globs.update(s["names"])
                elif t == "print":
                    for ar in s["args"]:
                        self.ann_expr(ar, sc, True)
                elif t == "return" and s["val"] is not None:
                    self.ann_expr(s["val"], sc, True)
                elif t == "expr":
                    self.ann_expr(s["val"], sc, True)
            elif t == "raise":
                self.exc_used = True
                if s["val"] is not None:
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
        if t in ("neg", "not", "unot", "deref"):
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
        if t == "list":
            for x in e["items"]:
                self.ann_expr(x, sc, ux)
            return
        if t == "index":
            self.ann_expr(e["obj"], sc, ux)
            self.ann_expr(e["idx"], sc, ux)
            return
        if t == "attr":
            # module attribute: base recorded for capture analysis; the
            # attribute itself resolves statically at emit time
            self.ann_expr(e["obj"], sc, ux)
            return
        if t == "slice":
            self.ann_expr(e["obj"], sc, ux)
            if e["start"] is not None:
                self.ann_expr(e["start"], sc, ux)
            if e["stop"] is not None:
                self.ann_expr(e["stop"], sc, ux)
            return
        if t == "dict":
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

    XBUILTINS = {"print", "int", "len", "str", "range", "append",
                 "split", "find", "join",
                 "alloc", "load8", "load32", "load64", "store8",
                 "store32", "store64", "as_ptr", "as_int"}

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
        if t == "list":
            items = e["items"]
            for it in items:
                self.ev(it, sc, mod)
                a.push_r("rax")
            a.mov_ri32("rdi", len(items))
            a.call("x_list_new")
            if items:
                a.mov_rm("rdx", "rax", 24)  # buf
                for i in reversed(range(len(items))):
                    a.pop_r("rcx")
                    a.mov_mr("rdx", "rcx", 8 * i)
            return
        if t == "dict":
            raise HSErr("dict not in x64 subset", ln)
        if t == "neg":
            self.ev(e["val"], sc, mod)
            self.check_int(lambda: self.raise_unop(6, ln))
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
        if t == "unot":
            self.ev(e["val"], sc, mod)
            lab_bad, lab_done = self.new_tmp("un"), self.new_tmp("un")
            self.check_int(lambda: a.jmp(lab_bad))
            a.sar_ri8("rax", 2)
            a.not_rr("rax")
            self.trunc62()
            self.tag_box()
            a.jmp(lab_done)
            a.label(lab_bad)
            self.raise_unop(9, ln)  # 9 = "cannot bitwise-not T"
            a.label(lab_done)
            return
        if t == "bin":
            self.ev_bin(e, sc, mod)
            return
        if t == "call":
            self.ev_call(e, sc, mod)
            return
        if t == "index":
            self.ev_index(e, sc, mod)
            return
        if t == "attr":
            m = self.resolve_mod_base(e["obj"], sc, mod, ln)
            target, lab = self.mod_global(m, e["name"], ln)
            if lab is None:
                raise HSErr(f"module '{target['name']}' is not a first-class value"
                            " in x64 subset (use mod.attr)", ln)
            a.lea_rip("rax", lab)
            a.mov_rm("rax", "rax", 0)
            return
        if t == "slice":
            self.ev_slice(e, sc, mod)
            return
        if t in ("deref", "sizeof", "field"):
            self.sev(e, sc, mod)
            return
        raise HSErr(f"{t} not in x64 subset", ln)

    def ev_slice(self, e, sc, mod):
        """s[a:b] / s[a:] / s[:b] / s[:] for Str (bytes) and List.
        Bounds clamp like interp; a missing bound defaults (0 / len)."""
        ln = e["line"]
        a = self.a
        self.ev(e["obj"], sc, mod)
        a.push_r("rax")                # obj
        mask = 0
        if e["start"] is not None:
            self.ev(e["start"], sc, mod)
            self.check_int(lambda: self.raise_static("slice index must be Int", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            mask |= 1
        else:
            a.mov_ri32("rax", 0)
            a.push_r("rax")
        if e["stop"] is not None:
            self.ev(e["stop"], sc, mod)
            self.check_int(lambda: self.raise_static("slice index must be Int", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            mask |= 2
        else:
            a.mov_ri32("rax", 0)
            a.push_r("rax")
        a.pop_r("rdx")                 # b (raw)
        a.pop_r("rsi")                 # a (raw)
        a.pop_r("rdi")                 # obj
        # obj must be Str or List here (else "cannot slice X")
        lab_sok, lab_sbad = self.new_tmp("sl"), self.new_tmp("sl")
        a.mov_rr("r11", "rdi")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_sbad)
        a.mov_rm("r11", "rdi", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_sok)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_sok)
        a.label(lab_sbad)
        a.mov_rr("rax", "rdi")
        self.raise_unop(7, ln)
        a.label(lab_sok)
        a.mov_ri32("rcx", mask)
        a.call("x_slice")

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

    def resolve_mod_base(self, e, sc, mod, ln):
        """Attribute base -> module dict. Base is a var bound by import,
        or a chained attr through submodules. Anything else is an error:
        x64 values have no attributes."""
        if e["t"] == "var":
            cur = mod if mod is not None else sc._mod
            if self.resolve_var(e["name"], sc, cur, ln)[0] is not None:
                raise HSErr("attribute access is only supported on modules (x64)", ln)
            m = self.find_binding(e["name"], sc)
            if m is None:
                raise HSErr(f"unknown variable '{e['name']}'", ln)
            return m
        if e["t"] == "attr":
            m = self.resolve_mod_base(e["obj"], sc, mod, ln)
            sub = m.get("submods", {}).get(e["name"])
            if sub is None:
                sub = m.get("imports", {}).get(e["name"])
            if sub is None:
                raise HSErr(f"module '{m['name']}' has no attribute '{e['name']}'", ln)
            return sub
        raise HSErr("attribute access is only supported on modules (x64)", ln)

    def mod_global(self, m, name, ln):
        """(target_mod, global_label) for attribute `name` on module m."""
        sub = m.get("submods", {}).get(name)
        if sub is not None:
            return (sub, None)  # a submodule: first-class use is an error
        sub = m.get("imports", {}).get(name)
        if sub is not None:
            return (sub, None)  # an imported module re-exported as attribute
        msc = m.get("scope")
        if msc is not None and (name in msc.loc or name in msc.uloc):
            return (m, self.glabel(m, name))
        raise HSErr(f"module '{m['name']}' has no attribute '{name}'", ln)

    def try_mod_value(self, e, sc, mod):
        """If e is a bare module reference (var/attr chain to a module),
        return the mod dict, else None. No errors raised."""
        try:
            if e["t"] == "var":
                cur = mod if mod is not None else sc._mod
                if self.resolve_var(e["name"], sc, cur, e["line"])[0] is not None:
                    return None
                return self.find_binding(e["name"], sc)
            if e["t"] == "attr":
                m = self.resolve_mod_base(e["obj"], sc, mod, e["line"])
                sub = m.get("submods", {}).get(e["name"])
                if sub is not None:
                    return sub
                return None
        except HSErr:
            return None
        return None

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

    def auto_global(self, name, sc, mod):
        """A read of a name assigned nowhere: give it a module global slot
        (init UNBOUND) so the read fails at runtime like interp, instead of
        at compile time. Returns ("gloc", name)."""
        ms = mod["scope"]
        if name not in ms.loc and name not in ms.uloc:
            ms.loc[name] = 0  # offset unused for globals (data label is used)
            self.a.data_label(self.glabel(mod, name))
            self.a.data_qword(Gen.HS_UNBOUND)
        return ("gloc", name)

    def var_get(self, name, sc, mod, ln, check=True):
        a = self.a
        kind, ref = self.resolve_var(name, sc, mod, ln)
        if kind is None:
            # builtin-as-value and module bindings stay compile errors;
            # genuinely unknown reads become unbound globals (runtime error).
            if name in ("print", "len", "range", "str", "int", "float", "input",
                        "open", "read", "write", "close", "argv", "env", "system",
                        "append", "split", "find", "join", "ticks", "readkey",
                        "pmm_alloc", "meminfo", "tcp_connect", "tcp_send",
                        "tcp_recv", "tcp_close", "tcp_listen", "tcp_accept",
                        "http_get", "json_parse", "json_str", "read_text",
                        "write_text", "append_text", "exists", "ls", "mkdir",
                        "json_load", "json_save", "alloc", "load8", "load32",
                        "load64", "store8", "store32", "store64",
                        "as_ptr", "as_int", "asm"):
                raise HSErr(f"builtin '{name}' is not a value (call it)", ln)
            if self.find_binding(name, sc) is not None:
                raise HSErr(f"module '{name}' is not a first-class value"
                            " in x64 subset (use mod.attr)", ln)
            kind, ref = self.auto_global(name, sc, mod)
        # Bound checks only where unbound can actually occur: frame locals
        # and globals. Params arrive bound from the caller (arity is a
        # separate, documented gap); caps are checked when captured; unsafe
        # statics are raw machine words by design.
        if kind in ("param", "uloc", "loc"):
            a.mov_rm("rax", "rbp", ref)
            if check and kind == "loc":
                self.check_bound(name, ln)
            return
        if kind == "cap":
            a.mov_rm("rax", "r15", 8 * ref)
            return
        if kind in ("guloc", "gloc"):
            a.lea_rip("rax", self.glabel(mod, name))
            a.mov_rm("rax", "rax")
            if check and kind == "gloc":
                self.check_bound(name, ln)
            return
        raise HSErr(f"bad var kind {kind} for '{name}'", ln)

    def ensure_prefixes(self, fullname, from_dir, line):
        """Load every dotted prefix of `fullname` (real file or shell package).

        Returns (top_mod, chain): the bound top module and the real (non-shell)
        modules in prefix order, so the importer can init them parent-first."""
        if not __import__("re").match(
                r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$", fullname):
            raise HSErr(f"bad module name '{fullname}'", line)
        parts = fullname.split(".")
        chain = []
        parent = None
        for i, part in enumerate(parts):
            dotted = ".".join(parts[:i + 1])
            last = (i == len(parts) - 1)
            try:
                m = self.load_module(dotted, from_dir, line)
                is_shell = False
            except HSErr as e:
                # only intermediate parents may be virtual packages; the
                # imported leaf itself must exist (mirrors interp)
                if last or f"cannot find module '{dotted}'" not in str(e):
                    raise
                m = self.shell_mods.get(dotted)
                if m is None:
                    m = {"name": dotted, "prog": [], "dir": from_dir,
                         "pfx": "", "scope": None, "shell": True, "submods": {}}
                    self.shell_mods[dotted] = m
                is_shell = True
            m.setdefault("submods", {})
            if parent is not None:
                parent.setdefault("submods", {})[part] = m
            parent = m
            if not is_shell:
                chain.append(m)
        topmod = self.shell_mods.get(parts[0])
        if topmod is None:
            # top prefix was real: find it in chain
            topmod = next(m for m in chain if m["name"] == parts[0])
        return topmod, chain

    def find_binding(self, name, sc):
        """Walk scope chain for an import binding -> mod dict or None."""
        s = sc
        while s is not None:
            m = self.mod_bindings.get((id(s), name))
            if m is not None:
                return m
            s = s.parent
        return None

    def drop_binding(self, sc, name):
        self.mod_bindings.pop((id(sc), name), None)

    def ev_bin(self, e, sc, mod):
        op, ln = e["op"], e["line"]
        a = self.a
        if op in ("and", "or"):
            # hs returns the operand itself, not a Bool
            self.ev(e["l"], sc, mod)
            a.push_r("rax")            # save left (tagged)
            self.truthy()              # rax = 0/1, flags set
            lab_keep, lab_end = self.new_tmp("bo"), self.new_tmp("bo")
            if op == "and":
                a.jcc("e", lab_keep)    # falsy left -> result is the left value
            else:
                a.jcc("ne", lab_keep)   # truthy left -> result is the left value
            a.add_ri32("rsp", 8)       # drop saved left
            self.ev(e["r"], sc, mod)
            a.jmp(lab_end)
            a.label(lab_keep)
            a.pop_r("rax")             # restore left
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
            # Int/Int or Str/Str go to x_cmp; anything else raises with
            # operand type names (matches interp's cannot compare).
            lab_cmpno, lab_cmperr, lab_cmpok = (self.new_tmp("co"), self.new_tmp("co"),
                                               self.new_tmp("co"))
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.cmp_ri32("r11", Gen.TAG_INT)
            a.jcc("ne", lab_cmpno)
            a.mov_rr("r11", "rcx")
            a.and_ri32("r11", 3)
            a.cmp_ri32("r11", Gen.TAG_INT)
            a.jcc("e", lab_cmpok)
            a.label(lab_cmpno)
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.jcc("ne", lab_cmperr)
            a.mov_rr("r11", "rcx")
            a.and_ri32("r11", 3)
            a.jcc("ne", lab_cmperr)
            a.mov_rm("r11", "rax", 0)
            a.cmp_ri32("r11", Gen.K_STR)
            a.jcc("ne", lab_cmperr)
            a.mov_rm("r11", "rcx", 0)
            a.cmp_ri32("r11", Gen.K_STR)
            a.jcc("e", lab_cmpok)
            a.label(lab_cmperr)
            self.raise_binop(5, ln)
            a.label(lab_cmpok)
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
            self.emit_add(ln)
            return
        if op in ("<<", ">>", "&", "|", "^"):
            self.emit_bitop(op, e, sc, mod, ln, True)
            return
        # - * / % : Int only (else "operator OP needs numbers, got A and B")
        opcodes = {"-": 1, "*": 2, "/": 3, "%": 4}
        self.ev(e["l"], sc, mod)
        a.push_r("rax")                # tagged l
        self.ev(e["r"], sc, mod)       # tagged r
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")                 # rax = l, rcx = r (both tagged)
        lab_aerr = self.new_tmp("ae")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", lab_aerr)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", lab_aerr)
        a.sar_ri8("rax", 2)
        a.sar_ri8("rcx", 2)
        lab_aok = self.new_tmp("ae")
        a.jmp(lab_aok)
        a.label(lab_aerr)
        self.raise_binop(opcodes[op], ln)
        a.label(lab_aok)
        if op == "-":
            a.sub_rr("rax", "rcx")
        elif op == "*":
            a.imul_rr("rax", "rcx")
        elif op in ("/", "%"):
            a.push_r("rdx")
            if not self.freestanding:
                # hosted: catchable divide error; freestanding: hardware #DE
                a.test_rr("rcx", "rcx")
                lab_dz = self.new_tmp("dz")
                a.jcc("ne", lab_dz)
                self.raise_static("division by zero", ln)
                a.label(lab_dz)
            a.cqo()
            a.idiv_r("rcx")
            if op == "%":
                a.mov_rr("rax", "rdx")
            a.pop_r("rdx")
        else:
            raise HSErr(f"bad operator {op}", ln)
        self.tag_box()

    def emit_add(self, ln):
        """rax/rcx tagged -> rax = Int+Int, Str+Str or List+List, else raise."""
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
        lab_list = self.new_tmp("ad")
        a.jcc("ne", lab_list)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("ne", lab_err)
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rcx")
        a.call("x_str_cat")
        a.jmp(lab_end)
        a.label(lab_list)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("ne", lab_err)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("ne", lab_err)
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rcx")
        a.call("x_list_cat")
        a.jmp(lab_end)
        a.label(lab_err)
        self.raise_binop(0, ln)
        a.label(lab_end)

    def ev_index(self, e, sc, mod):
        """obj[idx] for Str (1-char Str) and List (item)."""
        ln = e["line"]
        a = self.a
        self.ev(e["obj"], sc, mod)
        a.push_r("rax")
        self.ev(e["idx"], sc, mod)
        a.mov_rr("rcx", "rax")  # idx (tagged)
        a.pop_r("rax")          # obj
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        lab_ok = self.new_tmp("ix")
        a.jcc("e", lab_ok)
        self.raise_static("index must be Int", ln)
        a.label(lab_ok)
        a.sar_ri8("rcx", 2)     # raw idx
        lab_heap, lab_bad = self.new_tmp("ix"), self.new_tmp("ix")
        lab_str, lab_list = self.new_tmp("ix"), self.new_tmp("ix")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rax", 0)  # kind
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_str)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_list)
        a.label(lab_bad)
        self.raise_unop(1, ln)
        a.label(lab_str)
        a.mov_rm("r11", "rax", 8)  # len
        a.cmp_ri32("rcx", 0)
        lab_pos = self.new_tmp("ix")
        a.jcc("ge", lab_pos)
        a.add_rr("rcx", "r11")
        a.label(lab_pos)
        a.cmp_ri32("rcx", 0)
        a.jcc("l", lab_heap)    # reuse as idx-fail label
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_heap)
        a.lea_m("rdi", "rax", 16, "rcx", 1)
        a.mov_ri32("rsi", 1)
        a.call("x_str_at")
        lab_done = self.new_tmp("ix")
        a.jmp(lab_done)
        a.label(lab_list)
        a.mov_rm("r11", "rax", 8)  # len
        a.cmp_ri32("rcx", 0)
        lab_pos2 = self.new_tmp("ix")
        a.jcc("ge", lab_pos2)
        a.add_rr("rcx", "r11")
        a.label(lab_pos2)
        a.cmp_ri32("rcx", 0)
        a.jcc("l", lab_heap)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_heap)
        a.mov_rm("rdx", "rax", 24)  # buf
        a.mov_rmx("rax", "rdx", "rcx", 8, 0)
        a.jmp(lab_done)
        a.label(lab_heap)
        self.raise_static("index out of range", ln)
        a.label(lab_done)

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
            self.check_int(lambda: self.raise_unop(4, ln))
            return
        if fn["t"] == "var" and fn["name"] in ("str", "len"):
            if len(e["args"]) != 1:
                raise HSErr(f"{fn['name']} wants 1 arg", ln)
            self.ev(e["args"][0], sc, mod)
            if fn["name"] == "len":
                # Str or List here; anything else reports `len of X`
                lab_lok, lab_lck = self.new_tmp("ln"), self.new_tmp("ln")
                a.mov_rr("r11", "rax")
                a.and_ri32("r11", 3)
                a.test_rr("r11", "r11")
                a.jcc("ne", lab_lck)
                a.mov_rm("r11", "rax", 0)
                a.cmp_ri32("r11", Gen.K_STR)
                a.jcc("e", lab_lok)
                a.cmp_ri32("r11", Gen.K_LIST)
                a.jcc("e", lab_lok)
                a.label(lab_lck)
                self.raise_unop(0, ln)
                a.label(lab_lok)
            a.mov_rr("rdi", "rax")
            a.call("x_str" if fn["name"] == "str" else "x_len")
            return
        if fn["t"] == "var" and fn["name"] == "as_int" and e["args"]:
            # dynamic as_int yields a real Int (tagged); inside unsafe it stays
            # a raw machine word
            self.sev_call("as_int", e["args"], sc, mod, ln)
            self.tag_box()
            return
        if fn["t"] == "var" and fn["name"] in (
                "alloc", "load8", "load32", "load64", "store8", "store32",
                "store64", "as_ptr"):
            self.sev_call(fn["name"], e["args"], sc, mod, ln)
            return
        if fn["t"] == "var" and fn["name"] == "range":
            if len(e["args"]) == 1:
                self.ev(e["args"][0], sc, mod)
                self.check_int(lambda: self.raise_static(
                    "range wants range(n) or range(a, b) with Ints", ln))
                a.mov_rr("rdi", "rax")
                a.call("x_range1")
            elif len(e["args"]) == 2:
                self.ev(e["args"][0], sc, mod)
                self.check_int(lambda: self.raise_static(
                    "range wants range(n) or range(a, b) with Ints", ln))
                a.push_r("rax")
                self.ev(e["args"][1], sc, mod)
                self.check_int(lambda: self.raise_static(
                    "range wants range(n) or range(a, b) with Ints", ln))
                a.mov_rr("rsi", "rax")
                a.pop_r("rdi")
                a.call("x_range2")
            else:
                raise HSErr("range wants range(n) or range(a, b)", ln)
            return
        if fn["t"] == "var" and fn["name"] == "append":
            if len(e["args"]) != 2:
                raise HSErr("append wants append(list, x)", ln)
            self.ev(e["args"][0], sc, mod)
            lab_apok, lab_apbad = self.new_tmp("ap"), self.new_tmp("ap")
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            a.jcc("ne", lab_apbad)
            a.mov_rm("r11", "rax", 0)
            a.cmp_ri32("r11", Gen.K_LIST)
            a.jcc("e", lab_apok)
            a.label(lab_apbad)
            self.raise_static("append wants append(list, x)", ln)
            a.label(lab_apok)
            a.push_r("rax")
            self.ev(e["args"][1], sc, mod)
            a.mov_rr("rsi", "rax")
            a.pop_r("rdi")
            a.call("x_append")
            return
        if fn["t"] == "var" and fn["name"] == "split":
            if len(e["args"]) not in (1, 2):
                raise HSErr("split wants split(s) or split(s, sep)", ln)
            self.ev(e["args"][0], sc, mod)
            lab_spok, lab_spbad = self.new_tmp("sp"), self.new_tmp("sp")
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            a.jcc("ne", lab_spbad)
            a.mov_rm("r11", "rax", 0)
            a.cmp_ri32("r11", Gen.K_STR)
            a.jcc("e", lab_spok)
            a.label(lab_spbad)
            self.raise_static("split wants split(s) or split(s, sep)", ln)
            a.label(lab_spok)
            if len(e["args"]) == 1:
                a.mov_rr("rdi", "rax")
                a.call("x_split1")
            else:
                a.push_r("rax")
                self.ev(e["args"][1], sc, mod)
                lab_spok2, lab_spbad2 = self.new_tmp("sp"), self.new_tmp("sp")
                a.mov_rr("r11", "rax")
                a.and_ri32("r11", 3)
                a.test_rr("r11", "r11")
                a.jcc("ne", lab_spbad2)
                a.mov_rm("r11", "rax", 0)
                a.cmp_ri32("r11", Gen.K_STR)
                a.jcc("e", lab_spok2)
                a.label(lab_spbad2)
                self.raise_static("split wants split(s) or split(s, sep)", ln)
                a.label(lab_spok2)
                a.mov_rr("rsi", "rax")
                a.pop_r("rdi")
                a.mov_ri32("rdx", ln)
                a.call("x_split2")
            return
        if fn["t"] == "var" and fn["name"] == "find":
            if len(e["args"]) != 2:
                raise HSErr("find wants find(s, sub)", ln)
            self.ev(e["args"][0], sc, mod)
            a.push_r("rax")
            self.ev(e["args"][1], sc, mod)
            a.mov_rr("rsi", "rax")
            a.pop_r("rdi")
            lab_fok, lab_fbad = self.new_tmp("fn"), self.new_tmp("fn")
            for rr in ("rdi", "rsi"):
                a.mov_rr("r11", rr)
                a.and_ri32("r11", 3)
                a.test_rr("r11", "r11")
                a.jcc("ne", lab_fbad)
                a.mov_rm("r11", rr, 0)
                a.cmp_ri32("r11", Gen.K_STR)
                a.jcc("ne", lab_fbad)
            a.jmp(lab_fok)
            a.label(lab_fbad)
            self.raise_static("find wants find(s, sub)", ln)
            a.label(lab_fok)
            a.call("x_find")
            return
        if fn["t"] == "var" and fn["name"] == "join":
            if len(e["args"]) != 2:
                raise HSErr("join wants join(sep, list)", ln)
            self.ev(e["args"][0], sc, mod)
            a.push_r("rax")
            self.ev(e["args"][1], sc, mod)
            a.mov_rr("rsi", "rax")
            a.pop_r("rdi")
            lab_jok, lab_jbad = self.new_tmp("jn"), self.new_tmp("jn")
            a.mov_rr("r11", "rdi")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            a.jcc("ne", lab_jbad)
            a.mov_rm("r11", "rdi", 0)
            a.cmp_ri32("r11", Gen.K_STR)
            a.jcc("ne", lab_jbad)
            a.mov_rr("r11", "rsi")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            a.jcc("ne", lab_jbad)
            a.mov_rm("r11", "rsi", 0)
            a.cmp_ri32("r11", Gen.K_LIST)
            a.jcc("e", lab_jok)
            a.label(lab_jbad)
            self.raise_static("join wants join(sep, list)", ln)
            a.label(lab_jok)
            a.mov_ri32("rdx", ln)
            a.call("x_join")
            return
        if fn["t"] == "var" and fn["name"] in (
                "float", "input", "open", "read",
                "write", "close", "argv", "env", "system", "ticks",
                "readkey", "pmm_alloc", "pmm_total",
                "pmm_free", "meminfo", "mb_info", "mb_magic",
                "image_end", "cr2", "cr3", "set_cr3", "invlpg", "tlb_flush",
                "ctx_swap", "task_run", "task_init",
                "irq_off", "irq_on",
                "sched_on_tick", "sched_tick_clear",
                "tcp_connect", "tcp_send", "tcp_recv", "tcp_close",
                "tcp_listen", "tcp_accept", "http_get", "json_parse",
                "json_str", "read_text", "write_text", "append_text",
                "exists", "ls", "mkdir", "json_load", "json_save", "asm"):
            if self.freestanding and fn["name"] in (
                    "ticks", "readkey", "pmm_alloc", "pmm_total", "pmm_free",
                    "mb_info", "mb_magic", "image_end", "cr2", "cr3",
                    "set_cr3", "invlpg", "tlb_flush",
                    "ctx_swap", "task_run", "task_init",
                    "irq_off", "irq_on",
                    "sched_on_tick", "sched_tick_clear"):
                self.ev_kdev(fn["name"], e["args"], sc, mod, ln)
                return
            raise HSErr(f"builtin '{fn['name']}' not in x64 subset", ln)
        # user function: indirect through value (uniform caps in r15)
        self.ev(fn, sc, mod)  # rax = func struct ptr
        lab_fnok = self.new_tmp("fn")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        lab_fnb = self.new_tmp("fn")
        a.jcc("ne", lab_fnb)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_FUNC)
        a.jcc("e", lab_fnok)
        a.label(lab_fnb)
        self.raise_unop(3, ln)
        a.label(lab_fnok)
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
            self.check_int(lambda: self.raise_static("pmm_alloc wants pmm_alloc(npages)", ln))
            a.sar_ri8("rax", 2)
            lab_paok = self.new_tmp("pa")
            a.cmp_ri32("rax", 0)
            a.jcc("ge", lab_paok)
            self.raise_static("pmm_alloc wants pmm_alloc(npages)", ln)
            a.label(lab_paok)
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
        # --- memory introspection / paging primitives (raw machine words) ---
        if name == "image_end":
            if args:
                raise HSErr("image_end takes no args", ln)
            # first physical address after the kernel image
            a.lea_rip("rax", "imageend_")
            a.mov_rm("rax", "rax", 0)
            self.tag_box()
            return
        if name in ("mb_info", "mb_magic"):
            if args:
                raise HSErr(f"{name} takes no args", ln)
            # physical address of the multiboot info struct (EBX) and the boot
            # magic (EAX), both saved by the 32-bit stub before it switched modes
            a.lea_rip("rax", "mbinfo_" if name == "mb_info" else "mbmagic_")
            a.mov_rm("rax", "rax", 0)
            self.tag_box()
            return
        if name in ("cr2", "cr3"):
            if args:
                raise HSErr(f"{name} takes no args", ln)
            a.mov_rcr64("rax", 2 if name == "cr2" else 3)
            self.tag_box()
            return
        if name == "set_cr3":
            if len(args) != 1:
                raise HSErr("set_cr3 wants set_cr3(pml4)", ln)
            self.sev(args[0], sc, mod)  # raw pointer value
            a.mov_cr64(3, "rax")
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "invlpg":
            if len(args) != 1:
                raise HSErr("invlpg wants invlpg(vaddr)", ln)
            self.sev(args[0], sc, mod)  # raw vaddr in rax
            a.code += bytes([0x0F, 0x01, 0x38])  # invlpg [rax]
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "tlb_flush":
            if args:
                raise HSErr("tlb_flush takes no args", ln)
            # reload CR3 with itself: drops every non-global TLB entry.
            # Needed after a huge-page split, which changes translations for
            # a whole 2MB/1GB range that invlpg(vaddr) alone cannot cover.
            a.mov_rcr64("rax", 3)
            a.mov_cr64(3, "rax")
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "ctx_swap":
            # ctx_swap(save, load): save this context, resume the other one.
            # Both are ctx blocks (see emit_task_runtime); raw addresses
            # arrive as tagged Ints and are unboxed here.
            if len(args) != 2:
                raise HSErr("ctx_swap wants ctx_swap(save, load)", ln)
            self.ev(args[0], sc, mod)
            self.check_int(lambda: self.raise_static(
                "ctx_swap wants ctx_swap(save, load)", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            self.ev(args[1], sc, mod)
            self.check_int(lambda: self.raise_static(
                "ctx_swap wants ctx_swap(save, load)", ln))
            a.sar_ri8("rax", 2)
            a.mov_rr("rsi", "rax")
            a.pop_r("rdi")
            a.call("ctx_swap_inner")
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "task_run":
            # task_run(sched, task): like ctx_swap, but also records the
            # scheduler block so a returning task finds its way back.
            if len(args) != 2:
                raise HSErr("task_run wants task_run(sched, task)", ln)
            self.ev(args[0], sc, mod)
            self.check_int(lambda: self.raise_static(
                "task_run wants task_run(sched, task)", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            self.ev(args[1], sc, mod)
            self.check_int(lambda: self.raise_static(
                "task_run wants task_run(sched, task)", ln))
            a.sar_ri8("rax", 2)
            a.mov_rr("rsi", "rax")
            a.pop_r("rdi")
            a.lea_rip("rax", "sched_ret_")
            a.mov_mr("rax", "rdi", 0)
            a.call("ctx_swap_inner")
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "task_init":
            # task_init(ctx, stack_top, func): prepare a fresh context block
            # for a task whose entry is the Func value func (closures work:
            # caps ride along in r15). The fresh stack gets the task_exit
            # stub as its return address, so returning also exits cleanly.
            if len(args) != 3:
                raise HSErr("task_init wants task_init(ctx, top, func)", ln)
            self.ev(args[0], sc, mod)
            self.check_int(lambda: self.raise_static(
                "task_init wants task_init(ctx, top, func)", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")  # ctx
            self.ev(args[1], sc, mod)
            self.check_int(lambda: self.raise_static(
                "task_init wants task_init(ctx, top, func)", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")  # stack_top
            self.ev(args[2], sc, mod)  # rax = func struct (raw address)
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            lab_tiok = self.new_tmp("ti")
            lab_tib = self.new_tmp("ti")
            a.jcc("ne", lab_tib)
            a.mov_rm("r11", "rax", 0)
            a.cmp_ri32("r11", Gen.K_FUNC)
            a.jcc("e", lab_tiok)
            a.label(lab_tib)
            self.raise_unop(3, ln)  # not callable
            a.label(lab_tiok)
            a.mov_rm("r10", "rax", 8)  # code addr
            a.lea_m("r11", "rax", 16)  # caps addr
            a.pop_r("rsi")  # stack_top
            a.pop_r("rdi")  # ctx
            a.mov_ri32("rax", 0)
            a.mov_mr("rdi", "rax", 0)
            a.mov_mr("rdi", "rax", 8)
            a.mov_mr("rdi", "rax", 16)
            a.mov_mr("rdi", "rax", 24)
            a.mov_mr("rdi", "rax", 32)
            a.mov_mr("rdi", "r11", 40)  # r15 = caps
            a.lea_rip("rax", "task_exit")
            a.mov_mr("rsi", "rax", -8)  # return address on the fresh stack
            a.mov_rr("rax", "rsi")
            a.sub_ri32("rax", 8)
            a.mov_mr("rdi", "rax", 48)  # rsp
            a.mov_mr("rdi", "r10", 56)  # rip = entry code
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "irq_off":
            # cli: mask timer/keyboard IRQs around scheduler critical
            # sections. Tasks always run with IF=1; never swap with IF=0
            # (the target would keep running deaf to ticks).
            if args:
                raise HSErr("irq_off takes no args", ln)
            a.cli()
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "irq_on":
            if args:
                raise HSErr("irq_on takes no args", ln)
            a.sti()
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "sched_on_tick":
            # sched_on_tick(func): register the 0-arg Func the timer stub
            # calls on every tick (or 0/unregister via sched_tick(null)).
            if len(args) != 1:
                raise HSErr("sched_on_tick wants sched_on_tick(func)", ln)
            self.ev(args[0], sc, mod)  # rax = func struct (raw address)
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            lab_sok = self.new_tmp("so")
            lab_sob = self.new_tmp("so")
            a.jcc("ne", lab_sob)
            a.mov_rm("r11", "rax", 0)
            a.cmp_ri32("r11", Gen.K_FUNC)
            a.jcc("e", lab_sok)
            a.label(lab_sob)
            self.raise_unop(3, ln)  # not callable
            a.label(lab_sok)
            a.lea_rip("rcx", "sched_tick_fn_")
            a.mov_mr("rcx", "rax", 0)
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        if name == "sched_tick_clear":
            # unregister the tick handler (preemption off, timer still ticks)
            if args:
                raise HSErr("sched_tick_clear takes no args", ln)
            a.lea_rip("rcx", "sched_tick_fn_")
            a.mov_ri32("rax", 0)
            a.mov_mr("rcx", "rax", 0)
            a.mov_ri64("rax", Gen.HS_NULL)
            return
        raise HSErr(f"bad kdev {name}", ln)

    def print_unsafe(self, args, sc, mod, ln):
        """print inside unsafe: operands are raw machine words -> box each as
        a dynamic Int (an unsafe value has no tag of its own)."""
        a = self.a
        for i, ar in enumerate(args):
            if i > 0:
                a.lea_rip("rdi", "sp_")
                a.mov_ri32("rsi", 1)
                self.rt_out()
            if ar["t"] == "str":
                raise HSErr("strings not allowed in unsafe (use unsafe: outside)",
                            ln)
            self.sev(ar, sc, mod)
            self.tag_box()
            a.call("print_val")

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
            elif self.try_mod_value(ar, sc, mod) is not None:
                m = self.try_mod_value(ar, sc, mod)
                disp = f"<module {m['name']}>".encode()
                lab = self.rstr(f"<module {m['name']}>")
                a.lea_rip("rdi", lab)
                a.mov_ri32("rsi", len(disp))
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
            # Slots that hold dynamic (tagged) values must be unboxed when
            # unsafe code reads them as machine words. Names assigned inside
            # `unsafe:` (and unsafe typed locals) hold raw words already.
            kind, _ref = self.resolve_var(e["name"], sc, mod, ln)
            self.var_get(e["name"], sc, mod, ln)
            if kind == "param" or self.holds_dynamic(e["name"], sc, mod):
                self.unbox_int_here(ln)
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
        if t == "unot":
            self.sev(e["val"], sc, mod)
            a.not_rr("rax")
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
                    "alloc", "load8", "load32", "load64", "store8",
                    "store32", "store64", "as_ptr", "as_int"):
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
            self.raise_static("null pointer dereference", ln)
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
                self.raise_struct_oob(e["name"], count, ln)
                a.label(lab_ok)
            a.mov_rmx("rax", "rax", "rcx", 8, off)
            return
        if e["idx"] is not None:
            raise HSErr(f"field '{e['name']}' is not an array", ln)
        a.mov_rm("rax", "rax", off)

    def sev_idx(self, e, sc, mod):
        self.sev(e, sc, mod)
        self.a.push_r("rax")

    BIT_OPS = ("<<", ">>", "&", "|", "^")

    def trunc62(self):
        """Keep the low 62 bits of rax as a signed value (x64 Int payload).
        shl 2 drops the top two bits; sar 2 re-sign-extends from bit 61."""
        a = self.a
        a.shl_ri8("rax", 2)
        a.sar_ri8("rax", 2)

    def emit_bitop(self, op, e, sc, mod, ln, dynamic):
        """bitwise on Ints.

        dynamic=True  -> operands/results are tagged Ints (safe code path)
        dynamic=False -> operands/results are raw machine words (unsafe path)
        Type and shift-count errors use interp's wording.
        """
        a = self.a
        evalfn = self.ev if dynamic else self.sev
        evalfn(e["l"], sc, mod)
        a.push_r("rax")
        evalfn(e["r"], sc, mod)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")               # rax = l, rcx = r
        if dynamic:
            lab_body, lab_err = self.new_tmp("be"), self.new_tmp("be")
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.cmp_ri32("r11", Gen.TAG_INT)
            a.jcc("ne", lab_err)
            a.mov_rr("r11", "rcx")
            a.and_ri32("r11", 3)
            a.cmp_ri32("r11", Gen.TAG_INT)
            a.jcc("ne", lab_err)
            a.jmp(lab_body)
            a.label(lab_err)         # never returns
            a.lea_rip("rdi", self.rstr(op))
            a.mov_ri32("r8", len(op))
            a.mov_rr("rsi", "rax")
            a.mov_rr("rdx", "rcx")
            a.mov_ri32("r9", ln)
            a.jmp("hs_bitop_err")
            a.label(lab_body)
            a.sar_ri8("rax", 2)
            a.sar_ri8("rcx", 2)
        if op in ("<<", ">>"):
            lab_sh, lab_bad = self.new_tmp("be"), self.new_tmp("be")
            a.cmp_ri32("rcx", 63)      # interp range: 0..63
            a.jcc("le", lab_sh)
            a.jmp(lab_bad)
            a.label(lab_sh)
            a.test_rr("rcx", "rcx")
            a.jcc("s", lab_bad)        # negative count -> interp's error
            lab_end = self.new_tmp("be")
            if op == "<<":
                a.shl_cl("rax")
                self.trunc62()
            else:
                a.sar_cl("rax")       # arithmetic, like C on signed Int
            a.jmp(lab_end)
            a.label(lab_bad)
            a.mov_rr("rdi", "rcx")     # raw count -> build the message
            a.mov_ri32("rsi", ln)
            a.jmp("hs_shift_err")     # never returns
            a.label(lab_end)
        elif op == "&":
            a.and_rr("rax", "rcx")
        elif op == "|":
            a.or_rr("rax", "rcx")
        else:
            a.xor_rr("rax", "rcx")
        if dynamic:
            self.tag_box()

    def sev_bin(self, e, sc, mod):
        op, ln = e["op"], e["line"]
        a = self.a
        if op in self.BIT_OPS:
            self.emit_bitop(op, e, sc, mod, ln, False)
            return
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
                # hosted: catchable divide error; freestanding: hardware #DE
                a.test_rr("rcx", "rcx")
                lab_dz = self.new_tmp("dz")
                a.jcc("ne", lab_dz)
                self.raise_static("division by zero", ln)
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
        if t in ("num", "deref", "field", "sizeof", "bin", "neg", "not",
                 "unot"):
            return True
        if t == "call" and e["fn"]["t"] == "var" and e["fn"]["name"] in (
                "alloc", "load8", "load32", "load64", "store8", "store32",
                "store64", "as_ptr", "as_int"):
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
        if name in ("load8", "load32", "load64"):
            if len(args) != 1:
                raise HSErr(f"{name} wants {name}(p)", ln)
            self.sev(args[0], sc, mod)
            if name == "load8":
                # movzx rax, byte [rax]
                a.code += bytes([0x48, 0x0F, 0xB6, 0x00])
            elif name == "load32":
                # mov eax, [rax] (zero-extends)
                a.code += bytes([0x8B, 0x00])
            else:
                # mov rax, [rax] -- raw 64-bit, no tagging
                a.code += bytes([0x48, 0x8B, 0x00])
            return
        if name in ("store8", "store32", "store64"):
            if len(args) != 2:
                raise HSErr(f"{name} wants {name}(p, v)", ln)
            self.sev(args[1], sc, mod)
            a.push_r("rax")
            self.sev(args[0], sc, mod)
            a.pop_r("rcx")
            if name == "store8":
                a.code += bytes([0x88, 0x08])  # mov [rax], cl
            elif name == "store32":
                a.code += bytes([0x89, 0x08])  # mov [rax], ecx
            else:
                a.code += bytes([0x48, 0x89, 0x08])  # mov [rax], rcx
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
    def ex(self, s, sc, mod, depth, ux=False):
        """ux=True: inside `unsafe:` -- values are raw machine words."""
        t = s["t"]
        ln = s["line"]
        a = self.a
        if t == "pass":
            return
        if t == "expr":
            self.ev(s["val"], sc, mod)
            return
        if t == "print":
            if ux:
                self.print_unsafe(s["args"], sc, mod, ln)
            else:
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
                if ux:
                    # unsafe values are raw: evaluate statically, then box the
                    # machine word as the dynamic Int the caller expects
                    self.sev(s["val"], sc, mod)
                    self.tag_box()
                else:
                    self.ev(s["val"], sc, mod)
            else:
                a.mov_ri64("rax", Gen.HS_NULL)
            # value first (interp order), then unwind this function's trys
            a.push_r("rax")
            self._emit_finallies(sc, mod, depth)
            for _ in range(self.try_depth):
                a.call("hs_try_pop")
            a.pop_r("rax")
            a.mov_rr("rsp", "rbp")
            a.pop_r("rbp")
            a.ret()
            return
        if t == "break":
            if not self.loop_stack:
                raise HSErr("break outside loop", ln)
            self._emit_finallies(sc, mod, depth, for_break=True)
            for _ in range(self.try_depth - self.loop_trys[-1]):
                a.call("hs_try_pop")
            a.jmp(self.loop_stack[-1][0])
            return
        if t == "continue":
            if not self.loop_stack:
                raise HSErr("continue outside loop", ln)
            self._emit_finallies(sc, mod, depth, for_break=True)
            for _ in range(self.try_depth - self.loop_trys[-1]):
                a.call("hs_try_pop")
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
            self.loop_trys.append(self.try_depth)
            self.ex_body(s["body"], sc, mod, depth + 1)
            self.loop_trys.pop()
            self.loop_stack.pop()
            a.jmp(lab_t)
            a.label(lab_x)
            return
        if t == "for":
            self.ex_for(s, sc, mod, depth)
            return
        if t == "setindex":
            self.ex_setindex(s, sc, mod)
            return
        if t == "import":
            # run each imported module body once (guarded init, parent-first)
            for m in s["_mods"]:
                a.call(f"hsM_init_{m['pfx']}")
            return
        if t == "global":
            # declaration only: resolve_var already routes globals to storage
            return
        if t == "setattr":
            # module attribute assignment only (x64 values have no attrs);
            # the base must statically resolve to a module
            if s["obj"]["t"] not in ("var", "attr"):
                raise HSErr("attribute assignment only supported on modules (x64)", ln)
            m = self.resolve_mod_base(s["obj"], sc, mod, ln)
            target, lab = self.mod_global(m, s["name"], ln)
            if lab is None:
                raise HSErr(f"module '{target['name']}' is not a first-class value"
                            " in x64 subset (use mod.attr)", ln)
            self.ev(s["val"], sc, mod)
            a.push_r("rax")
            a.lea_rip("rcx", lab)
            a.pop_r("rax")
            a.mov_mr("rcx", "rax", 0)
            return
        if t == "try":
            self.ex_try(s, sc, mod, depth)
            return
        if t == "raise":
            if s["val"] is None:
                if not self._except_stack:
                    raise HSErr("raise without active exception", ln)
                a.call("hs_reraise")
            else:
                v = s["val"]
                if v["t"] == "str":
                    b = v["val"].encode()
                    slab = self.rstr(v["val"])
                    a.lea_rip("rdi", slab)
                    a.mov_ri32("rsi", len(b))
                    a.mov_ri32("rdx", ln)
                    a.call("hs_raise_raw")
                else:
                    self.ev(v, sc, mod)
                    lab_rstr = self.new_tmp("rz")
                    a.mov_rr("r11", "rax")
                    a.and_ri32("r11", 3)
                    a.test_rr("r11", "r11")
                    lab_rbad = self.new_tmp("rz")
                    a.jcc("ne", lab_rbad)
                    a.mov_rm("r11", "rax", 0)
                    a.cmp_ri32("r11", Gen.K_STR)
                    a.jcc("e", lab_rstr)
                    a.label(lab_rbad)
                    self.raise_static("raise wants Str", ln)
                    a.label(lab_rstr)
                    a.mov_rm("rsi", "rax", 8)
                    a.lea_m("rdi", "rax", 16)
                    a.mov_ri32("rdx", ln)
                    a.call("hs_error")
            return
        if t in ("extern", "unsafe", "struct",
                 "udecl", "store", "fstore"):
            raise HSErr(f"{t} handled elsewhere or not in x64 subset", ln)
        raise HSErr(f"bad stmt {t}", ln)

    def ex_setindex(self, s, sc, mod):
        """lst[i] = v (List only; Str/Dict assignment is a runtime error)."""
        ln = s["line"]
        a = self.a
        self.ev(s["obj"], sc, mod)
        a.push_r("rax")
        self.ev(s["idx"], sc, mod)
        a.push_r("rax")
        self.ev(s["val"], sc, mod)
        a.mov_rr("rdx", "rax")  # val
        a.pop_r("rcx")          # idx (tagged)
        a.pop_r("rax")          # obj
        lab_ok = self.new_tmp("sx")
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("e", lab_ok)
        self.raise_static("index must be Int", ln)
        a.label(lab_ok)
        a.sar_ri8("rcx", 2)     # raw idx
        lab_bad, lab_list = self.new_tmp("sx"), self.new_tmp("sx")
        lab_pos, lab_oob, lab_done = (self.new_tmp("sx"), self.new_tmp("sx"),
                                      self.new_tmp("sx"))
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rax", 0)  # kind
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_list)
        a.label(lab_bad)
        self.raise_unop(2, ln)
        a.label(lab_list)
        a.mov_rm("r11", "rax", 8)  # len
        a.cmp_ri32("rcx", 0)
        a.jcc("ge", lab_pos)
        a.add_rr("rcx", "r11")
        a.label(lab_pos)
        a.cmp_ri32("rcx", 0)
        a.jcc("l", lab_oob)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_oob)
        a.mov_rm("r11", "rax", 24)  # buf
        a.mov_mrx("r11", "rcx", 8, 0, "rdx")
        a.jmp(lab_done)
        a.label(lab_oob)
        self.raise_static("index out of range", ln)
        a.label(lab_done)

    def ex_for(self, s, sc, mod, depth):
        """for var in range([a,] b) | for var in <Str/List expr>.
        range() lowers to a raw counter loop; Str yields 1-char Str
        values, List yields items. Anything else is a runtime error."""
        ln = s["line"]
        a = self.a
        it = s["iter"]
        if (it["t"] == "call" and it["fn"]["t"] == "var"
                and it["fn"]["name"] == "range"
                and len(it["args"]) in (1, 2)):
            args = it["args"]
            start_e = None if len(args) == 1 else args[0]
            end_e = args[0] if len(args) == 1 else args[1]
            # end (raw) -> _f0, counter (raw) -> _f1 (evaluated once,
            # like Python's iter). The loop var is assigned from the
            # counter each pass, so after the loop it keeps the last
            # value (interp parity) instead of the end value.
            self.ev(end_e, sc, mod)
            self.check_int(lambda: self.raise_static("range wants range(n) or range(a, b) with Ints", ln))
            a.sar_ri8("rax", 2)
            a.mov_mr("rbp", "rax", s["_f0"])
            # counter = start (raw)
            if start_e is None:
                a.mov_ri32("rax", 0)
            else:
                self.ev(start_e, sc, mod)
                self.check_int(lambda: self.raise_static("range wants range(n) or range(a, b) with Ints", ln))
                a.sar_ri8("rax", 2)
            a.mov_mr("rbp", "rax", s["_f1"])
            lab_top = self.new_tmp("fr")
            lab_step = self.new_tmp("fr")
            lab_brk = self.new_tmp("fr")
            a.label(lab_top)
            a.mov_rm("rax", "rbp", s["_f1"])
            a.mov_rm("rcx", "rbp", s["_f0"])
            a.cmp_rr("rax", "rcx")
            a.jcc("ge", lab_brk)
            self.tag_box()
            self.var_set(s["var"], sc, mod, ln)
            self.loop_stack.append((lab_brk, lab_step))
            self.loop_trys.append(self.try_depth)
            self.ex_body(s["body"], sc, mod, depth + 1)
            self.loop_trys.pop()
            self.loop_stack.pop()
            a.label(lab_step)
            a.mov_rm("rax", "rbp", s["_f1"])
            a.add_ri32("rax", 1)
            a.mov_mr("rbp", "rax", s["_f1"])
            a.jmp(lab_top)
            a.label(lab_brk)
            return
        # Str/List iteration: obj -> _f0, index (raw) -> _f1.
        # The element load dispatches on the object kind every pass.
        self.ev(it, sc, mod)
        a.mov_mr("rbp", "rax", s["_f0"])
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", s["_f1"])
        lab_top, lab_step, lab_brk = (self.new_tmp("fs"), self.new_tmp("fs"),
                                      self.new_tmp("fs"))
        lab_bad, lab_str, lab_list, lab_elem = (self.new_tmp("fs"),
                                                self.new_tmp("fs"),
                                                self.new_tmp("fs"),
                                                self.new_tmp("fs"))
        a.label(lab_top)
        a.mov_rm("rax", "rbp", s["_f0"])  # obj
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")   # heap object?
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rax", 0)  # kind
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_str)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_list)
        a.label(lab_bad)
        self.raise_unop(5, ln)
        a.label(lab_str)
        a.mov_rm("rcx", "rax", 8)         # len
        a.mov_rm("rdx", "rbp", s["_f1"])  # idx
        a.cmp_rr("rdx", "rcx")
        a.jcc("ae", lab_brk)
        a.lea_m("rdi", "rax", 16, "rdx", 1)  # src = data + idx
        a.mov_ri32("rsi", 1)
        a.call("x_str_at")
        a.jmp(lab_elem)
        a.label(lab_list)
        a.mov_rm("rcx", "rax", 8)         # len
        a.mov_rm("rdx", "rbp", s["_f1"])  # idx
        a.cmp_rr("rdx", "rcx")
        a.jcc("ae", lab_brk)
        a.mov_rm("rax", "rax", 24)        # buf
        a.mov_rmx("rax", "rax", "rdx", 8, 0)  # item
        a.label(lab_elem)
        self.var_set(s["var"], sc, mod, ln)
        self.loop_stack.append((lab_brk, lab_step))
        self.loop_trys.append(self.try_depth)
        self.ex_body(s["body"], sc, mod, depth + 1)
        self.loop_trys.pop()
        self.loop_stack.pop()
        a.label(lab_step)
        a.mov_rm("rax", "rbp", s["_f1"])
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", s["_f1"])
        a.jmp(lab_top)
        a.label(lab_brk)

    def _emit_finallies(self, sc, mod, depth, for_break=False):
        # Emit pending finally bodies, innermost first. return exits every
        # enclosing try; break/continue only those inside the current loop.
        # A finally being emitted never re-runs itself (no infinite recursion).
        nloops = len(self.loop_trys)
        for ldep, fb in reversed(self._fin_stack):
            if id(fb) in self._fin_active:
                continue
            if for_break and ldep != nloops:
                continue
            self._fin_active.add(id(fb))
            try:
                self.ex_body(fb, sc, mod, depth)
            finally:
                self._fin_active.discard(id(fb))

    def ex_try(self, s, sc, mod, depth):
        ln = s["line"]
        a = self.a
        has_except = s.get("ebody") is not None
        has_finally = s.get("fbody") is not None
        ename = s.get("ename")
        if has_finally:
            self._fin_stack.append((len(self.loop_trys), s["fbody"]))
        try:
            lab_handler, lab_done = self.new_tmp("tr"), self.new_tmp("tr")
            a.call("hs_try_push0")
            a.test_rr("rax", "rax")
            a.jcc("ne", lab_handler)
            self.try_depth += 1
            try:
                self.ex_body(s["body"], sc, mod, depth)
            finally:
                self.try_depth -= 1
            a.call("hs_try_pop")
            if has_finally:
                self._emit_fbody(sc, mod, depth, s["fbody"])
            a.jmp(lab_done)
            a.label(lab_handler)
            # the error sits on top of the exception value stack
            if has_except:
                lab_hfail = lab_hok = None
                if has_finally:
                    # an error inside the handler must still run this try's
                    # finally: guard the handler with its own frame, run the
                    # finally, then rethrow (interp parity)
                    lab_hfail, lab_hok = self.new_tmp("tr"), self.new_tmp("tr")
                    a.call("hs_try_push0")
                    a.test_rr("rax", "rax")
                    a.jcc("ne", lab_hfail)
                self._except_stack.append(lab_handler)
                try:
                    if ename is not None:
                        a.call("hs_exc_str")   # rax = "msg at line N"
                        if s.get("_eshadow"):
                            a.push_r("rax")    # exc str
                            self.var_get(ename, sc, mod, ln, check=False)
                            a.mov_mr("rbp", "rax", s["_esave"])
                            a.pop_r("rax")     # exc str
                        self.var_set(ename, sc, mod, ln)
                    self.ex_body(s["ebody"], sc, mod, depth)
                    if ename is not None:
                        if s.get("_eshadow"):
                            a.mov_rm("rax", "rbp", s["_esave"])
                            self.var_set(ename, sc, mod, ln)
                        else:
                            a.mov_ri64("rax", Gen.HS_UNBOUND)
                            self.var_set(ename, sc, mod, ln)
                finally:
                    self._except_stack.pop()
                if has_finally:
                    a.call("hs_try_pop")
                    a.jmp(lab_hok)
                    a.label(lab_hfail)
                    # the stale original error below the new one is dropped by
                    # the rethrow's stack truncation; no explicit pop needed
                    self._emit_fbody(sc, mod, depth, s["fbody"])
                    a.call("hs_reraise")
                    a.label(lab_hok)
                a.call("hs_exc_pop")
                if has_finally:
                    self._emit_fbody(sc, mod, depth, s["fbody"])
            else:
                # try/finally without except: run finally, then re-raise
                if has_finally:
                    self._emit_fbody(sc, mod, depth, s["fbody"])
                a.call("hs_reraise")
            a.label(lab_done)
        finally:
            if has_finally:
                self._fin_stack.pop()

    def _emit_fbody(self, sc, mod, depth, fbody):
        # Emit one finally body; it never re-runs itself, outers still apply.
        self._fin_active.add(id(fbody))
        try:
            self.ex_body(fbody, sc, mod, depth)
        finally:
            self._fin_active.discard(id(fbody))

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
                    self.raise_static("null pointer dereference", ln)
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
                        self.raise_struct_oob(x["name"], count, ln)
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
                    self.loop_trys.append(self.try_depth)
                    for st in x["body"]:
                        self.ex_unsafe_one(st, sc, mod, depth + 1)
                    self.loop_trys.pop()
                    self.loop_stack.pop()
                    a.jmp(lab_t)
                    a.label(lab_x)
            elif t in ("return", "break", "continue"):
                self.ex(x, sc, mod, depth, ux=True)
            elif t == "raise":
                # raise is always dynamic: same codegen inside unsafe
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
        if t == "raise":
            # raise is always dynamic: same codegen inside or outside unsafe
            self.ex(s, sc, mod, depth)
            return
        raise HSErr(f"{t} not allowed in unsafe (x64)", s["line"])

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

    def holds_dynamic(self, name, sc, mod):
        """True when `name`'s slot holds a tagged dynamic value (not a raw
        machine word): anything not assigned inside `unsafe:`."""
        cur = sc
        while cur is not None:
            if name in cur.raw_names or name in cur.uloc:
                return False
            if name in cur.loc or name in cur.params:
                return True
            if name in cur.globs:
                break
            cur = cur.parent
        # module-level: dynamic unless the module assigned it inside unsafe
        ms = mod["scope"]
        return name not in ms.raw_names

    def unbox_int_here(self, ln):
        """rax = tagged value -> raw Int payload (raise when not an Int)."""
        a = self.a
        lab_bad, lab_end = self.new_tmp("ub"), self.new_tmp("ub")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", lab_bad)
        a.sar_ri8("rax", 2)
        a.jmp(lab_end)
        a.label(lab_bad)
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr("cannot use "))
        a.mov_ri32("rsi", 11)
        a.call("x_str_at")
        a.pop_r("rcx")
        a.call("x_tname")
        a.mov_rr("rsi", "rax")
        a.lea_rip("rdi", self.rstr("cannot use "))
        a.mov_ri32("rdx", 11)
        a.call("x_str_cat")
        a.lea_rip("rdi", self.rstr(" as I64"))
        a.mov_ri32("rdx", 7)
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rsi", ln)
        a.jmp("hs_raise_msg")
        a.label(lab_end)

    def check_int(self, err, reg="rax"):
        """If reg is not a tagged Int, run err() (a zero-arg callable emitting
        the failure path); otherwise fall through."""
        a = self.a
        lab_ok = self.new_tmp("tc")
        a.mov_rr("r11", reg)
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("e", lab_ok)
        err()
        a.label(lab_ok)

    def truthy(self):
        """rax = tagged value -> rax = 0/1 truthiness, flags set (hs rules)."""
        a = self.a
        a.mov_rr("rdi", "rax")
        a.call("x_truth")
        a.test_rr("rax", "rax")

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

    # ----- raisable errors (uniform with or without try; catchable when
    # a handler is live). Conventions: hs_raise_raw(ptr,len,line),
    # hs_raise_msg(Str,line). Callers hold values in rax/rcx unless noted.
    def raise_static(self, msg, ln):
        """Raise a static message + line."""
        a = self.a
        lab = self.rstr(msg)
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", len(msg.encode()))
        a.mov_ri32("rdx", ln)
        a.call("hs_raise_raw")

    def raise_static_rdx(self, msg):
        """Raise a static message; line already in rdx."""
        a = self.a
        lab = self.rstr(msg)
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", len(msg.encode()))
        a.call("hs_raise_raw")

    def raise_unop(self, code, ln):
        """rax = tagged value -> hs_unop_err(code, val, ln)."""
        a = self.a
        a.mov_rr("rsi", "rax")
        a.mov_ri32("rdi", code)
        a.mov_ri32("rdx", ln)
        a.call("hs_unop_err")

    def raise_binop(self, code, ln):
        """rax = left, rcx = right (both tagged) -> hs_binop_err(code,l,r,ln)."""
        a = self.a
        a.mov_rr("rsi", "rax")
        a.mov_rr("rdx", "rcx")
        a.mov_ri32("rdi", code)
        a.mov_ri32("rcx", ln)
        a.call("hs_binop_err")

    def raise_struct_oob(self, name, count, ln):
        """rcx = raw idx -> raise `index {i} out of range for '{name}'[{count}]`."""
        a = self.a
        a.push_r("rcx")                # idx
        lab = self.rstr("index ")
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", 6)
        a.call("x_str_at")
        a.push_r("rax")
        a.mov_rm("rdi", "rsp", 8)
        a.call("x_num_to_str")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.push_r("rax")
        lab = self.rstr(" out of range for '")
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", 20)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.push_r("rax")
        lab = self.rstr(name)
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", len(name.encode()))
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.push_r("rax")
        lab = self.rstr("'[")
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", 2)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.push_r("rax")
        a.mov_ri64("rdi", count)
        a.call("x_num_to_str")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.push_r("rax")
        lab = self.rstr("]")
        a.lea_rip("rdi", lab)
        a.mov_ri32("rsi", 1)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rsi", ln)
        a.call("hs_raise_msg")

    def check_bound(self, name, ln):
        """rax = dynamic value -> raise unknown variable if unbound."""
        a = self.a
        lab_ok = self.new_tmp("ub")
        a.cmp_ri32("rax", Gen.HS_UNBOUND)
        a.jcc("ne", lab_ok)
        self.raise_static(f"unknown variable '{name}'", ln)
        a.label(lab_ok)

    # ----- functions / main / link -----
    def frame_init_unbound(self, n):
        # locals start as UNBOUND so reads-before-write raise instead of
        # returning stack garbage (matches interp's unknown variable).
        a = self.a
        if not n:
            return
        a.mov_ri64("rcx", Gen.HS_UNBOUND)
        for i in range(1, n + 1):
            a.mov_mr("rbp", "rcx", -8 * i)

    def emit_func(self, label, node, fscope, mod):
        a = self.a
        a.label(label)
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        n = fscope.nloc
        if n:
            a.sub_ri32("rsp", 8 * n)
        self.frame_init_unbound(n)
        self.ex_body(node["body"], fscope, mod, 1)
        a.mov_ri64("rax", Gen.HS_NULL)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()

    def emit_mod_init(self, m):
        # guarded one-time module body: first call runs it, later calls ret
        a = self.a
        done = f"hsM_done_{m['pfx']}"
        a.label(f"hsM_init_{m['pfx']}")
        a.lea_rip("rax", done)
        a.mov_rm("rcx", "rax", 0)
        a.test_rr("rcx", "rcx")
        lab_done = self.new_tmp("mi")
        a.jcc("ne", lab_done)
        a.mov_ri32("rcx", 1)
        a.mov_mr("rax", "rcx", 0)
        n = m["scope"].nloc
        if n:
            a.push_r("rbp")
            a.mov_rr("rbp", "rsp")
            a.sub_ri32("rsp", 8 * n)
            self.frame_init_unbound(n)
        self.ex_body(m["prog"], m["scope"], m, 0)
        if n:
            a.mov_rr("rsp", "rbp")
            a.pop_r("rbp")
        a.label(lab_done)
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
        self.frame_init_unbound(ms.nloc)
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
        ms._mod = mod
        self.collect(mod["prog"], ms)
        for i, fs in enumerate(self.all_fs):
            self.flabels[id(fs)] = f"hsF_{i}"
        self.finalize(mod)
        for m in [mod] + [x for x in self.modules if x.get("collected")]:
            self.emit_data(m)
            if m is not mod:
                self.a.data_label(f"hsM_done_{m['pfx']}")
                self.a.data_qword(0)
        if self.freestanding:
            self.emit_runtime_fs()
        else:
            self.emit_runtime()
        self.emit_fatal_line()
        self.emit_err_builders()
        if self.exc_used:
            self.emit_exc_runtime()
        if self.freestanding:
            self.emit_irq_stubs()
            self.emit_task_runtime()
        for m in [x for x in self.modules if x.get("collected")]:
            self.emit_mod_init(m)
        for s, themod in self._def_nodes(mod):
            self.emit_func(self.flabels[id(s["_fs"])], s, s["_fs"], themod)
        self.emit_main(mod)
        assert self.try_depth == 0 and not self.loop_trys, "try/loop stack unbalanced"
        assert not self._fin_stack and not self._except_stack, "fin/except stack unbalanced"
        # rodata: strings + sp/nl (sp_/nl_ labels for separators)
        self.a.label("sp_")
        self.a.code += b" "
        self.a.label("nl_")
        self.a.code += b"\n"
        # wspace_: 1 for split() separators (" \t\n\v\f\r" + \x1c-\x1f,
        # matching interp; bytes >= 0x80 never split: ASCII-only)
        self.a.label("wspace_")
        ws = bytearray(256)
        for c in b" \t\n\v\f\r\x1c\x1d\x1e\x1f":
            ws[c] = 1
        self.a.code += bytes(ws)
        if self.freestanding:
            self.a.label("oom_")
            self.a.code += b"out of memory\0"
            self.a.label("excrip_")
            self.a.code += b" rip="
            self.a.label("exccr2_")
            self.a.code += b" cr2="
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
            # physical address of the multiboot info struct, written by the
            # 32-bit stub (EBX) before the long-mode jump, plus the boot magic
            # from EAX so the kernel can tell multiboot1 from multiboot2
            self.a.data_label("mbinfo_")
            self.a.data_qword(0)
            self.a.data_label("mbmagic_")
            self.a.data_qword(0)
            # scheduler return target: ctx block recorded by task_run, read by
            # the task_exit stub when a task function returns
            self.a.data_label("sched_ret_")
            self.a.data_qword(0)
            # preemptive scheduler slots (see emit_task_runtime + irq_stub_32):
            # sched_cur_ = block of the running task (every swap records it),
            # sched_tick_fn_ = registered tick Func or 0,
            # sched_depth_ = live timer-stub frames (nesting guard)
            self.a.data_label("sched_cur_")
            self.a.data_qword(0)
            self.a.data_label("sched_tick_fn_")
            self.a.data_qword(0)
            self.a.data_label("sched_depth_")
            self.a.data_qword(0)
            # physical end of the kernel image; patched by build_xkernel once
            # the final file size is known (the memory manager reserves it)
            self.a.data_label("imageend_")
            self.a.data_qword(0)
            # IDT (48 gates) + IDTR filled by build_xkernel
            self.reserve("idt_", 48 * 16)
            self.reserve("idtr_", 10)
        else:
            self.a.data_qword(0)
            self.a.data_label("bump_end_")
            self.a.data_qword(0)
        if self.exc_used:
            # exception handler stack + active-error value stack
            self.a.data_label("exc_depth")
            self.a.data_qword(0)
            self.a.data_label("exc_frames")
            self.a.data_bytes(b"\0" * (Gen.EXC_FRSZ * Gen.EXC_MAX))
            self.a.data_label("exc_vlen")
            self.a.data_qword(0)
            self.a.data_label("exc_vals")
            self.a.data_bytes(b"\0" * (Gen.EXC_VSZ * Gen.EXC_VMAX))
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
        def walk(body, themod):
            for s in body:
                if s["t"] == "def":
                    out.append((s, themod))
                    walk(s["body"], themod)
                elif s["t"] == "if":
                    walk(s["then"], themod)
                    for _, eb in s["elifs"]:
                        walk(eb, themod)
                    walk(s["els"], themod)
                elif s["t"] == "while":
                    walk(s["body"], themod)
                elif s["t"] == "for":
                    walk(s["body"], themod)
                elif s["t"] == "try":
                    walk(s["body"], themod)
                    if s.get("ebody") is not None:
                        walk(s["ebody"], themod)
                    if s.get("fbody") is not None:
                        walk(s["fbody"], themod)
                elif s["t"] == "unsafe":
                    walk(s["body"], themod)
        walk(mod["prog"], mod)
        for m in self.modules:
            if m.get("collected"):
                walk(m["prog"], m)
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
        # fault RIP: above our 15 pushed regs + the call's return address
        a.lea_rip("rsi", "excrip_")
        a.mov_ri32("rdx", 5)
        self.k_write()
        a.mov_rm("rax", "rsp", 128)
        a.push_r("rax")
        a.call("print_int")
        a.add_ri32("rsp", 8)
        # CR2: fault address (meaningful for EXC 14, garbage otherwise)
        a.lea_rip("rsi", "exccr2_")
        a.mov_ri32("rdx", 5)
        self.k_write()
        a.mov_rcr64("rax", 2)
        a.push_r("rax")
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
        # timer IRQ0 -> vec 32: ticks_++, then drive the .hs scheduler when
        # one is registered. The stub fully saves the interrupted task into
        # sched_cur_ (maintained by every ctx_swap_inner), runs the tick
        # handler on a dedicated stack, and either restores+irets (handler
        # returned: keep running) or never comes back (handler swapped away).
        # Nesting is handled by a depth counter: only depth 1 proceeds,
        # deeper ticks EOI+iret on the current stack (no slots touched, so
        # no state to corrupt). The skip path uses the stack only, which is
        # always valid here. Full state (all 15 regs + rsp + rip) is saved,
        # so the interrupted point is resumable no matter what it was doing.
        # No cli anywhere: .hs critical sections mask IRQs themselves, and
        # every shared slot below is reached by exactly one live stub frame.
        a.label("irq_stub_32")
        # Timer tick. Nesting is linearized by sched_depth_: only depth 1
        # proceeds; deeper ticks EOI and bail on the current stack (no slots
        # touched, nothing to corrupt). .hs critical sections mask IRQs
        # themselves around queue mutations; everything the handler touches
        # is read-only otherwise.
        a.push_r("rax")  # stash live rax (stack always valid on entry)
        a.inc_mrip("ticks_")
        a.inc_mrip("sched_depth_")
        a.mov_rm_rip("rax", "sched_depth_")
        a.cmp_ri32("rax", 1)
        lab_tskip = self.new_tmp("tm")
        a.jcc("ne", lab_tskip)  # nested tick: bail out
        a.mov_ri32("rax", 0x20)
        a.mov_ri16("dx", 0x20)
        a.out_dx_al()  # EOI
        a.mov_rm_rip("rax", "sched_cur_")
        a.test_rr("rax", "rax")
        lab_tskip2 = self.new_tmp("tm")
        a.jcc("e", lab_tskip2)  # no task ever ran
        a.mov_rm_rip("rax", "sched_tick_fn_")
        a.test_rr("rax", "rax")
        a.jcc("e", lab_tskip2)  # preemption off
        # Full save into the cur block. Stack now holds live rax ([R0-8]);
        # push live rbx too, then read both back by offset. Saved rsp = R0
        # (recomputed with lea: no pops, nothing unbalanced).
        a.push_r("rbx")
        a.mov_rm_rip("rbx", "sched_cur_")  # base
        a.mov_rm("rax", "rsp", 8)  # live rax ([R0-8])
        a.mov_mr("rbx", "rax", 64)  # rax
        a.mov_rm("rax", "rsp", 0)  # live rbx ([R0-16])
        a.mov_mr("rbx", "rax", 0)  # rbx
        a.mov_mr("rbx", "rcx", 72)
        a.mov_mr("rbx", "rdx", 80)
        a.mov_mr("rbx", "rsi", 88)
        a.mov_mr("rbx", "rdi", 96)
        a.mov_mr("rbx", "rbp", 8)
        a.mov_mr("rbx", "r8", 104)
        a.mov_mr("rbx", "r9", 112)
        a.mov_mr("rbx", "r10", 120)
        a.mov_mr("rbx", "r11", 128)
        a.mov_mr("rbx", "r12", 16)
        a.mov_mr("rbx", "r13", 24)
        a.mov_mr("rbx", "r14", 32)
        a.mov_mr("rbx", "r15", 40)
        a.lea_m("rax", "rsp", 16)  # R0
        a.mov_mr("rbx", "rax", 48)  # rsp
        a.lea_rip("rax", "tick_back")
        a.mov_mr("rbx", "rax", 56)
        # The handler runs on the current (task) stack: bounded use and
        # nest-safe, since every frame here is balanced or travels with the
        # task being swapped. (A separate IRQ stack with an absolute reset
        # would clobber handler frames abandoned by swaps.)
        # call the registered tick handler: it returns Null (keep running
        # the interrupted task) or a task block address (switch there).
        # Same shape as a normal 0-arg call (func obj, caps in r15).
        a.mov_rm_rip("r10", "sched_tick_fn_")
        a.push_r("r10")
        a.lea_m("r15", "r10", 16)  # caps
        a.mov_rm("rax", "r10", 8)  # code
        a.call_rax()
        a.add_ri32("rsp", 8)
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_NULL)
        lab_tgo = self.new_tmp("tm")
        a.jcc("ne", lab_tgo)  # a block address: switch there
        # Null: nobody to switch to. Restore from the cur block the entry
        # saved (the handler changed nothing), drop the depth, resume.
        a.mov_rm_rip("rbx", "sched_cur_")
        a.mov_rm("rax", "rbx", 64)
        a.mov_rm("rcx", "rbx", 72)
        a.mov_rm("rdx", "rbx", 80)
        a.mov_rm("rsi", "rbx", 88)
        a.mov_rm("rdi", "rbx", 96)
        a.mov_rm("rbp", "rbx", 8)
        a.mov_rm("r8", "rbx", 104)
        a.mov_rm("r9", "rbx", 112)
        a.mov_rm("r10", "rbx", 120)
        a.mov_rm("r11", "rbx", 128)
        a.mov_rm("r12", "rbx", 16)
        a.mov_rm("r13", "rbx", 24)
        a.mov_rm("r14", "rbx", 32)
        a.mov_rm("r15", "rbx", 40)
        a.mov_rm("rsp", "rbx", 48)
        a.mov_rm("rbx", "rbx", 0)
        a.dec_mrip("sched_depth_")
        lab_tdone = self.new_tmp("tm")
        a.jmp(lab_tdone)
        # Switch: rax is the tagged target block. Unbox it, record it as
        # current, drop the depth (nobody returns through this frame), then
        # full-load the target and jump to its rip. That rip pairs with its
        # rsp by construction: fresh task -> entry code on a fresh stack,
        # preempted task -> tick_back on a hardware frame, suspended task
        # -> resume on a builtin frame. No save here: the entry already
        # saved the interrupted task.
        a.label(lab_tgo)
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        lab_tbad = self.new_tmp("tm")
        a.jcc("ne", lab_tbad)  # tick must return Null or an Int address
        a.sar_ri8("rax", 2)
        a.mov_rr("rbx", "rax")  # base: survives until the final jump
        a.lea_rip("rdi", "sched_cur_")
        a.mov_mr("rdi", "rbx", 0)  # record current
        a.mov_ri32("rax", 0)
        a.mov_mr_rip("sched_depth_", "rax")  # nobody returns via stub
        a.mov_rm("rax", "rbx", 64)
        a.mov_rm("rcx", "rbx", 72)
        a.mov_rm("rdx", "rbx", 80)
        a.mov_rm("rsi", "rbx", 88)
        a.mov_rm("rdi", "rbx", 96)
        a.mov_rm("rbp", "rbx", 8)
        a.mov_rm("r8", "rbx", 104)
        a.mov_rm("r9", "rbx", 112)
        a.mov_rm("r10", "rbx", 120)
        a.mov_rm("r11", "rbx", 128)
        a.mov_rm("r12", "rbx", 16)
        a.mov_rm("r13", "rbx", 24)
        a.mov_rm("r14", "rbx", 32)
        a.mov_rm("r15", "rbx", 40)
        a.mov_rm("rsp", "rbx", 48)
        a.push_m("rbx", 56)
        a.mov_rm("rbx", "rbx", 0)
        # The CPU cleared IF when it vectored here (interrupt gate); the
        # iret that would restore it never runs on this path, so enable
        # explicitly -- otherwise the target runs deaf to ticks. (STI takes
        # effect after the next instruction, so the ret below is atomic.)
        a.sti()
        a.ret()
        a.label(lab_tbad)
        a.call("k_halt")  # corrupt scheduler state: stop, do not jump wild
        a.label("tick_back")  # resumed preempted task lands here: a bare
        a.label(lab_tdone)  # iret, stack top already the hardware frame
        a.iretq()
        a.label(lab_tskip)  # nested tick: unwind, resume; the pending
        a.dec_mrip("sched_depth_")  # edge refires after iret (no EOI here:
        a.pop_r("rax")  # outer already EOI'd, nothing is lost)
        a.label(lab_tdone2 := self.new_tmp("tm"))
        a.iretq()
        a.label(lab_tskip2)  # outer bail (EOI done): unwind, resume
        a.dec_mrip("sched_depth_")
        a.pop_r("rax")
        a.jmp(lab_tdone2)
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

    def emit_task_runtime(self):
        # Cooperative + preemptive task switching. Context block (136 bytes,
        # .hs-managed, opaque): callee-saved + rsp + rip first (the cooperative
        # path only touches these), then the caller-saved regs the timer stub
        # needs for full preemption:
        # +0 rbx +8 rbp +16 r12 +24 r13 +32 r14 +40 r15 +48 rsp +56 rip
        # +64 rax +72 rcx +80 rdx +88 rsi +96 rdi +104 r8 +112 r9 +120 r10
        # +128 r11. Every transition funnels through ctx_swap_inner, which
        # records the incoming block in sched_cur_ so the timer stub always
        # knows whose state to save.
        a = self.a
        a.label("ctx_swap_inner")  # rdi = save block, rsi = load block
        # Full save: every reg (a preempted task may hold live values in
        # caller-saved regs). rax first: the depth reset below needs it.
        a.mov_mr("rdi", "rax", 64)
        a.mov_ri32("rax", 0)
        a.mov_mr_rip("sched_depth_", "rax")
        a.mov_mr("rdi", "rcx", 72)
        a.mov_mr("rdi", "rdx", 80)
        a.mov_mr("rdi", "rsi", 88)
        a.mov_mr("rdi", "rdi", 96)
        a.mov_mr("rdi", "rbx", 0)
        a.mov_mr("rdi", "rbp", 8)
        a.mov_mr("rdi", "r8", 104)
        a.mov_mr("rdi", "r9", 112)
        a.mov_mr("rdi", "r10", 120)
        a.mov_mr("rdi", "r11", 128)
        a.mov_mr("rdi", "r12", 16)
        a.mov_mr("rdi", "r13", 24)
        a.mov_mr("rdi", "r14", 32)
        a.mov_mr("rdi", "r15", 40)
        a.mov_mr("rdi", "rsp", 48)
        a.lea_rip("rax", "ctx_resume")
        a.mov_mr("rdi", "rax", 56)
        a.lea_rip("rax", "sched_cur_")
        a.mov_mr("rax", "rsi", 0)
        # Full load. rbx stays the base until the end; the rip goes via
        # push+ret so no scratch register is needed (all hold task state).
        # Every stored rip pairs with its rsp: fresh task -> entry on a
        # fresh stack, preempted task -> tick_back on a hardware frame,
        # suspended task -> resume on a builtin frame.
        a.mov_rr("rbx", "rsi")
        a.mov_rm("rax", "rbx", 64)
        a.mov_rm("rcx", "rbx", 72)
        a.mov_rm("rdx", "rbx", 80)
        a.mov_rm("rsi", "rbx", 88)
        a.mov_rm("rdi", "rbx", 96)
        a.mov_rm("rbp", "rbx", 8)
        a.mov_rm("r8", "rbx", 104)
        a.mov_rm("r9", "rbx", 112)
        a.mov_rm("r10", "rbx", 120)
        a.mov_rm("r11", "rbx", 128)
        a.mov_rm("r12", "rbx", 16)
        a.mov_rm("r13", "rbx", 24)
        a.mov_rm("r14", "rbx", 32)
        a.mov_rm("r15", "rbx", 40)
        a.mov_rm("rsp", "rbx", 48)
        a.push_m("rbx", 56)
        a.mov_rm("rbx", "rbx", 0)
        a.ret()
        a.label("ctx_resume")  # kept as the cooperative rip value; the
        a.ret()  # push_m/ret above lands here identically
        # task entry: a finished task function returns here, which hands
        # control back to whoever ran it last (recorded by task_run)
        a.label("task_exit")
        a.lea_rip("rdi", "exit_save_")
        a.lea_rip("rsi", "sched_ret_")
        a.mov_rm("rsi", "rsi", 0)
        a.jmp("ctx_swap_inner")
        self.reserve("exit_save_", 136)

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

    # ----- exception runtime (setjmp/longjmp over a fixed handler stack) -----
    # Handler frame (144 bytes): 0:rbx 8:rcx 16:rdx 24:rsi 32:rdi 40:rbp
    # 48:r8 56:r9 64:r10 72:r11 80:r12 88:r13 96:r14 104:r15 112:rsp 120:rip
    # 128:vlen (value-stack level at push time)
    EXC_FRSZ, EXC_MAX, EXC_VSZ, EXC_VMAX = 144, 256, 24, 256

    def emit_exc_runtime(self):
        a = self.a
        # hs_try_push0: save context into frames[depth++]; rax = 0.
        # Fatal on nesting overflow (never returns there).
        a.label("hs_try_push0")
        a.lea_rip("rax", "exc_depth")
        a.mov_rm("rax", "rax", 0)
        a.cmp_ri32("rax", Gen.EXC_MAX)
        lab_ov = self.new_tmp("ex")
        a.jcc("ae", lab_ov)
        a.mov_rr("rcx", "rax")
        a.shl_ri8("rcx", 7)            # *128
        a.shl_ri8("rax", 4)            # *16
        a.add_rr("rax", "rcx")         # *144
        a.lea_rip("rcx", "exc_frames")
        a.add_rr("rax", "rcx")
        a.mov_mr("rax", "rbx", 0)
        a.mov_mr("rax", "rcx", 8)
        a.mov_mr("rax", "rdx", 16)
        a.mov_mr("rax", "rsi", 24)
        a.mov_mr("rax", "rdi", 32)
        a.mov_mr("rax", "rbp", 40)
        a.mov_mr("rax", "r8", 48)
        a.mov_mr("rax", "r9", 56)
        a.mov_mr("rax", "r10", 64)
        a.mov_mr("rax", "r11", 72)
        a.mov_mr("rax", "r12", 80)
        a.mov_mr("rax", "r13", 88)
        a.mov_mr("rax", "r14", 96)
        a.mov_mr("rax", "r15", 104)
        a.lea_m("rcx", "rsp", 8)
        a.mov_mr("rax", "rcx", 112)
        a.mov_rm("rcx", "rsp", 0)      # return address
        a.mov_mr("rax", "rcx", 120)
        a.lea_rip("rcx", "exc_vlen")
        a.mov_rm("rcx", "rcx", 0)
        a.mov_mr("rax", "rcx", 128)
        a.inc_mrip("exc_depth")
        a.xor_rr("rax", "rax")
        a.ret()
        a.label(lab_ov)
        a.lea_rip("rdi", self.rstr("try nesting too deep\n"))
        a.mov_ri32("rsi", 21)
        a.jmp("hs_fatal")
        # hs_try_pop / hs_try_popn(rdi=n) / hs_exc_pop
        a.label("hs_try_pop")
        a.dec_mrip("exc_depth")
        a.ret()
        a.label("hs_try_popn")
        a.lea_rip("rax", "exc_depth")
        a.mov_rm("rcx", "rax", 0)
        a.sub_rr("rcx", "rdi")
        a.mov_mr("rax", "rcx", 0)
        a.ret()
        a.label("hs_exc_pop")
        a.dec_mrip("exc_vlen")
        a.ret()
        # hs_error(rdi=msg, rsi=len, rdx=line): deliver to innermost handler
        # (truncate value stack, push error, restore context, resume with 1),
        # or die with `error: msg at line N` when no handler is live.
        a.label("hs_error")
        a.push_r("rdx")                # line
        a.mov_rr("r8", "rdi")          # msg
        a.mov_rr("r9", "rsi")          # len
        a.lea_rip("rax", "exc_depth")
        a.mov_rm("rax", "rax", 0)
        a.test_rr("rax", "rax")
        lab_caught = self.new_tmp("ex")
        a.jcc("ne", lab_caught)
        a.pop_r("rdx")
        a.mov_rr("rdi", "r8")
        a.mov_rr("rsi", "r9")
        a.jmp("hs_fatal_msgline")
        a.label(lab_caught)
        a.lea_rip("rcx", "exc_depth")
        a.mov_rm("r11", "rcx", 0)
        a.sub_ri32("r11", 1)
        a.mov_mr("rcx", "r11", 0)      # depth--
        a.mov_rr("rax", "r11")
        a.mov_rr("rcx", "r11")
        a.shl_ri8("rcx", 7)
        a.shl_ri8("rax", 4)
        a.add_rr("rax", "rcx")         # depth*144
        a.lea_rip("rcx", "exc_frames")
        a.add_rr("rax", "rcx")
        a.mov_rr("r10", "rax")         # frame ptr
        a.mov_rm("rcx", "rax", 128)    # frame.vlen
        a.lea_rip("rdx", "exc_vlen")
        a.mov_mr("rdx", "rcx", 0)      # truncate
        a.mov_rr("rdx", "rcx")
        a.shl_ri8("rdx", 3)            # vlen*8
        a.shl_ri8("rcx", 4)            # vlen*16
        a.add_rr("rdx", "rcx")         # vlen*24
        a.lea_rip("rcx", "exc_vals")
        a.add_rr("rdx", "rcx")         # slot
        a.mov_mr("rdx", "r8", 0)       # msg
        a.mov_mr("rdx", "r9", 8)       # len
        a.pop_r("rcx")                 # line
        a.mov_mr("rdx", "rcx", 16)
        a.inc_mrip("exc_vlen")
        # restore context (frame ptr in r10) and resume with rax = 1
        a.mov_rm("rbx", "r10", 0)
        a.mov_rm("rcx", "r10", 8)
        a.mov_rm("rdx", "r10", 16)
        a.mov_rm("rsi", "r10", 24)
        a.mov_rm("rdi", "r10", 32)
        a.mov_rm("rbp", "r10", 40)
        a.mov_rm("r8", "r10", 48)
        a.mov_rm("r9", "r10", 56)
        a.mov_rm("r11", "r10", 72)
        a.mov_rm("r12", "r10", 80)
        a.mov_rm("r13", "r10", 88)
        a.mov_rm("r14", "r10", 96)
        a.mov_rm("r15", "r10", 104)
        a.mov_rm("rax", "r10", 120)    # rip
        a.mov_rm("rsp", "r10", 112)    # switch stacks (r10 intact: absolute addr)
        a.mov_rm("r10", "r10", 64)
        a.mov_rr("r11", "rax")         # rip -> r11
        a.mov_ri32("rax", 1)
        a.jmp_r("r11")
        # hs_fatal(rdi=ptr, rsi=len): print to stderr (or serial) and die.
        a.label("hs_fatal")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.mov_rr("rdx", "rsi")
        a.mov_rr("rsi", "rdi")
        self.rt_out(2)
        if self.freestanding:
            a.call("k_halt")
        else:
            a.mov_ri32("rdi", 1)
            a.mov_ri32("rax", 60)
            a.syscall()
        # hs_exc_str() -> rax = Str "msg at line N" for the active error.
        a.label("hs_exc_str")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.lea_rip("rax", "exc_vlen")
        a.mov_rm("rax", "rax", 0)
        a.test_rr("rax", "rax")
        lab_noexc = self.new_tmp("ex")
        a.jcc("ne", lab_noexc)
        a.lea_rip("rdi", self.rstr("<no exception>"))
        a.mov_ri32("rsi", 15)
        a.call("x_str_at")
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        a.label(lab_noexc)
        a.sub_ri32("rax", 1)
        a.mov_rr("rcx", "rax")
        a.shl_ri8("rcx", 4)            # *16
        a.mov_rr("rdx", "rax")
        a.shl_ri8("rdx", 3)            # *8
        a.add_rr("rcx", "rdx")         # *24
        a.lea_rip("rdx", "exc_vals")
        a.add_rr("rcx", "rdx")         # slot
        a.mov_rm("rdi", "rcx", 0)      # msg
        a.mov_rm("rsi", "rcx", 8)      # len
        a.mov_rm("rdx", "rcx", 16)     # line
        a.mov_mr("rbp", "rdx", -24)
        a.call("x_str_at")             # s1 = msg
        a.mov_mr("rbp", "rax", -8)
        a.mov_rm("rax", "rbp", -24)    # line == 0 -> plain msg, no suffix
        a.test_rr("rax", "rax")
        lab_nosfx = self.new_tmp("ex")
        a.jcc("e", lab_nosfx)
        a.lea_rip("rdi", self.rstr(" at line "))
        a.mov_ri32("rsi", 9)
        a.call("x_str_at")             # s2
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -8)
        a.call("x_str_cat")            # s1+s2
        a.mov_mr("rbp", "rax", -8)
        a.mov_rm("rdi", "rbp", -24)    # line (raw)
        a.call("x_num_to_str")         # s3
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -8)
        a.call("x_str_cat")
        lab_sfxdn = self.new_tmp("ex")
        a.jmp(lab_sfxdn)
        a.label(lab_nosfx)
        a.mov_rm("rax", "rbp", -8)     # s1 (line==0 path skips suffix)
        a.label(lab_sfxdn)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # hs_reraise(): re-raise the active error (bare `raise`).
        a.label("hs_reraise")
        a.lea_rip("rax", "exc_vlen")
        a.mov_rm("rax", "rax", 0)
        a.test_rr("rax", "rax")
        lab_rrok = self.new_tmp("ex")
        a.jcc("ne", lab_rrok)
        a.lea_rip("rdi", self.rstr("raise without active exception\n"))
        a.mov_ri32("rsi", 30)
        a.jmp("hs_fatal")
        a.label(lab_rrok)
        a.sub_ri32("rax", 1)
        a.mov_rr("rcx", "rax")
        a.shl_ri8("rcx", 4)
        a.mov_rr("rdx", "rax")
        a.shl_ri8("rdx", 3)
        a.add_rr("rcx", "rdx")
        a.lea_rip("rdx", "exc_vals")
        a.add_rr("rcx", "rdx")
        a.mov_rm("rdi", "rcx", 0)
        a.mov_rm("rsi", "rcx", 8)
        a.mov_rm("rdx", "rcx", 16)
        a.jmp("hs_error")
    def emit_err_builders(self):
        # Always emitted (no handler frames needed): error message builders
        # and raise trampolines.Uniform messages with or without try in play.
        a = self.a
        # hs_raise_raw(rdi=ptr, rsi=len, rdx=line): raise a static message.
        a.label("hs_raise_raw")
        if self.exc_used:
            a.jmp("hs_error")
        else:
            a.jmp("hs_fatal_msgline")
        # hs_shift_err(rdi=raw count, rsi=line): `shift count N out of range
        # (0..63)` -- never returns.
        a.label("hs_shift_err")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.mov_mr("rbp", "rdi", -8)      # count
        a.mov_mr("rbp", "rsi", -16)     # line
        a.lea_rip("rdi", self.rstr("shift count "))
        a.mov_ri32("rsi", 12)
        a.call("x_str_at")
        a.mov_mr("rbp", "rax", -24)     # t
        a.mov_rm("rdi", "rbp", -8)
        a.call("x_num_to_str")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -24)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -24)
        a.lea_rip("rdi", self.rstr(" out of range (0..63)"))
        a.mov_ri32("rsi", 21)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -24)
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_rm("rsi", "rbp", -16)
        a.jmp("hs_raise_msg")
        # hs_raise_msg(rdi=Str, rsi=line): raise an already-built message.
        a.label("hs_raise_msg")
        a.mov_rr("rdx", "rsi")         # line
        a.mov_rm("rsi", "rdi", 8)      # len
        a.lea_m("rdi", "rdi", 16)      # data
        if self.exc_used:
            a.jmp("hs_error")
        else:
            a.jmp("hs_fatal_msgline")
        # type_err: generic fallback for runtime-internal failures.
        a.label("type_err")
        a.lea_rip("rdi", self.rstr("type error"))
        a.mov_ri32("rsi", 10)
        a.mov_ri32("rdx", 0)
        if self.exc_used:
            a.jmp("hs_error")
        else:
            a.jmp("hs_fatal_msgline")
        # x_tname(rdi=tagged) -> rax = Str with the type name.
        a.label("x_tname")
        a.mov_rr("r10", "rdi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        lab_ti, lab_tb, lab_tn = self.new_tmp("tn"), self.new_tmp("tn"), self.new_tmp("tn")
        lab_th, lab_tu = self.new_tmp("tn"), self.new_tmp("tn")
        a.cmp_ri32("rax", Gen.TAG_INT)
        a.jcc("e", lab_ti)
        a.cmp_ri32("rax", Gen.TAG_BOOL)
        a.jcc("e", lab_tb)
        a.cmp_ri32("rax", Gen.TAG_NULL)
        a.jcc("e", lab_th)
        a.test_rr("rax", "rax")
        a.jcc("ne", lab_tu)            # tag 3 non-null -> Unbound
        a.mov_rm("rax", "r10", 0)      # kind
        lab_ts, lab_tl, lab_tf = (self.new_tmp("tn"), self.new_tmp("tn"),
                                  self.new_tmp("tn"))
        a.cmp_ri32("rax", Gen.K_STR)
        a.jcc("e", lab_ts)
        a.cmp_ri32("rax", Gen.K_LIST)
        a.jcc("e", lab_tl)
        a.cmp_ri32("rax", Gen.K_FUNC)
        a.jcc("e", lab_tf)
        a.lea_rip("rdi", self.rstr("?"))
        a.mov_ri32("rsi", 1)
        a.call("x_str_at")
        a.ret()
        a.label(lab_th)                # tag 3: Null vs Unbound
        a.cmp_ri32("r10", Gen.HS_NULL)
        a.jcc("e", lab_tn)
        a.jmp(lab_tu)
        for lab_nm, txt in ((lab_ti, "Int"), (lab_tb, "Bool"), (lab_tn, "Null"),
                            (lab_tu, "Unbound"), (lab_ts, "Str"),
                            (lab_tl, "List"), (lab_tf, "Func")):
            a.label(lab_nm)
            a.lea_rip("rdi", self.rstr(txt))
            a.mov_ri32("rsi", len(txt))
            a.call("x_str_at")
            a.ret()
        # hs_binop_err(rdi=code, rsi=l, rdx=r, rcx=line): dynamic binop message.
        # code: 0 = "cannot add A and B"; 1..4 = "operator 'OP' needs numbers,
        # got A and B" (OP from "+-*/"); 5 = "cannot compare A and B".
        # hs_bitop_err(rdi=op ptr, r8=op len, rsi=l, rdx=r, r9=line):
        # `operator 'OP' needs Ints, got L and R` -- never returns.
        a.label("hs_bitop_err")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 80)
        a.mov_mr("rbp", "rdi", -8)      # op ptr
        a.mov_mr("rbp", "r8", -16)      # op len
        a.mov_mr("rbp", "rsi", -24)     # l
        a.mov_mr("rbp", "rdx", -32)     # r
        a.mov_mr("rbp", "r9", -40)      # line
        # "operator '" + op + "' needs Ints, got " + tname(l) + " and " + tname(r)
        # built exactly like hs_binop_err: one live Str kept in a stack slot
        a.lea_rip("rdi", self.rstr("operator '"))
        a.mov_ri32("rsi", 10)
        a.call("x_str_at")
        a.mov_mr("rbp", "rax", -48)     # t
        a.mov_rm("rdi", "rbp", -8)      # op
        a.mov_rm("rsi", "rbp", -16)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.lea_rip("rdi", self.rstr("' needs Ints, got "))
        a.mov_ri32("rsi", 18)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.mov_rm("rdi", "rbp", -24)
        a.call("x_tname")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.lea_rip("rdi", self.rstr(" and "))
        a.mov_ri32("rsi", 5)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.mov_rm("rdi", "rbp", -32)
        a.call("x_tname")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_rm("rsi", "rbp", -40)
        a.jmp("hs_raise_msg")
        a.label("hs_binop_err")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 64)
        a.mov_mr("rbp", "rdi", -8)     # code
        a.mov_mr("rbp", "rsi", -16)    # l
        a.mov_mr("rbp", "rdx", -24)    # r
        a.mov_mr("rbp", "rcx", -32)    # line
        a.cmp_ri32("rdi", 0)
        lab_badd, lab_barith = self.new_tmp("be"), self.new_tmp("be")
        lab_bcmp, lab_bjoin = self.new_tmp("be"), self.new_tmp("be")
        a.jcc("e", lab_badd)
        a.cmp_ri32("rdi", 5)
        a.jcc("e", lab_bcmp)
        a.jmp(lab_barith)
        a.label(lab_badd)
        a.lea_rip("rdi", self.rstr("cannot add "))
        a.mov_ri32("rsi", 11)
        a.call("x_str_at")
        a.jmp(lab_bjoin)
        a.label(lab_bcmp)
        a.lea_rip("rdi", self.rstr("cannot compare "))
        a.mov_ri32("rsi", 15)
        a.call("x_str_at")
        a.jmp(lab_bjoin)
        a.label(lab_barith)
        a.mov_rm("rax", "rbp", -8)     # code 1..4 -> "-*/"[code-1]
        a.sub_ri32("rax", 1)
        a.lea_rip("rcx", self.rstr("+-*/"))
        a.add_rr("rax", "rcx")
        a.mov_mr("rbp", "rax", -40)    # op ptr
        a.lea_rip("rdi", self.rstr("operator '"))
        a.mov_ri32("rsi", 10)
        a.call("x_str_at")
        a.mov_mr("rbp", "rax", -48)    # t
        a.mov_rm("rdi", "rbp", -40)
        a.mov_ri32("rsi", 1)
        a.call("x_str_at")             # op str
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.lea_rip("rdi", self.rstr("' needs numbers, got "))
        a.mov_ri32("rsi", 22)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.label(lab_bjoin)
        a.mov_mr("rbp", "rax", -48)    # prefix
        a.mov_rm("rdi", "rbp", -16)    # l
        a.call("x_tname")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.lea_rip("rdi", self.rstr(" and "))
        a.mov_ri32("rsi", 5)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -48)
        a.mov_rm("rdi", "rbp", -24)    # r
        a.call("x_tname")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_rm("rsi", "rbp", -32)    # line
        a.call("hs_raise_msg")
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # hs_unop_err(rdi=code, rsi=val, rdx=line): prefix + tname + suffix.
        # code: 0 "len of ", 1 "cannot index ", 2 "cannot assign into ",
        # 3 "not callable: ", 4 "cannot convert "/" to Int", 5 "not iterable: ",
        # 6 "cannot negate ", 7 "cannot slice ".
        a.label("hs_unop_err")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.mov_mr("rbp", "rdi", -8)
        a.mov_mr("rbp", "rsi", -16)
        a.mov_mr("rbp", "rdx", -24)
        lab_u0, lab_u1, lab_u2 = self.new_tmp("ue"), self.new_tmp("ue"), self.new_tmp("ue")
        lab_u3, lab_u4, lab_u5 = self.new_tmp("ue"), self.new_tmp("ue"), self.new_tmp("ue")
        lab_u6, lab_u7 = self.new_tmp("ue"), self.new_tmp("ue")
        lab_u9 = self.new_tmp("ue")
        lab_ugo = self.new_tmp("ue")
        a.cmp_ri32("rdi", 0)
        a.jcc("e", lab_u0)
        a.cmp_ri32("rdi", 1)
        a.jcc("e", lab_u1)
        a.cmp_ri32("rdi", 2)
        a.jcc("e", lab_u2)
        a.cmp_ri32("rdi", 3)
        a.jcc("e", lab_u3)
        a.cmp_ri32("rdi", 4)
        a.jcc("e", lab_u4)
        a.cmp_ri32("rdi", 5)
        a.jcc("e", lab_u5)
        a.cmp_ri32("rdi", 6)
        a.jcc("e", lab_u6)
        a.cmp_ri32("rdi", 9)
        a.jcc("e", lab_u9)
        a.jmp(lab_u7)
        for lab_u, txt in ((lab_u0, "len of "), (lab_u1, "cannot index "),
                           (lab_u2, "cannot assign into "),
                           (lab_u3, "not callable: "),
                           (lab_u4, "cannot convert "),
                           (lab_u5, "not iterable: "),
                           (lab_u6, "cannot negate "),
                           (lab_u7, "cannot slice "),
                           (lab_u9, "cannot bitwise-not ")):
            a.label(lab_u)
            a.lea_rip("rdi", self.rstr(txt))
            a.mov_ri32("rsi", len(txt))
            a.call("x_str_at")
            a.jmp(lab_ugo)
        a.label(lab_ugo)
        a.mov_mr("rbp", "rax", -32)    # prefix
        a.mov_rm("rdi", "rbp", -16)
        a.call("x_tname")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -32)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -32)
        a.mov_rm("rax", "rbp", -8)
        a.cmp_ri32("rax", 4)
        lab_nosfx = self.new_tmp("ue")
        a.jcc("ne", lab_nosfx)
        a.lea_rip("rdi", self.rstr(" to Int"))
        a.mov_ri32("rsi", 7)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -32)
        a.call("x_str_cat")
        a.mov_mr("rbp", "rax", -32)
        a.label(lab_nosfx)
        a.mov_rm("rdi", "rbp", -32)
        a.mov_rm("rsi", "rbp", -24)
        a.call("hs_raise_msg")
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()

    def emit_fatal_line(self):
        a = self.a
        # hs_fatal_msgline(rdi=ptr, rsi=len, rdx=line): `error: msg at line N`.
        a.label("hs_fatal_msgline")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 32)
        a.mov_mr("rbp", "rdi", -8)
        a.mov_mr("rbp", "rsi", -16)
        a.mov_mr("rbp", "rdx", -24)
        a.lea_rip("rdi", self.rstr("error: "))
        a.mov_ri32("rsi", 7)
        self.rt_out(2)
        a.mov_rm("rdi", "rbp", -8)
        a.mov_rm("rsi", "rbp", -16)
        self.rt_out(2)
        a.mov_rm("rax", "rbp", -24)
        a.test_rr("rax", "rax")
        lab_noln = self.new_tmp("ex")
        a.jcc("e", lab_noln)
        a.lea_rip("rdi", self.rstr(" at line "))
        a.mov_ri32("rsi", 9)
        self.rt_out(2)
        a.mov_rm("rdi", "rbp", -24)
        a.lea_rip("rsi", "nbuf_e")
        a.call("fmt_int")              # rsi = start, rdx = len
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rdx")
        self.rt_out(2)
        a.label(lab_noln)
        a.lea_rip("rdi", self.rstr("\n"))
        a.mov_ri32("rsi", 1)
        self.rt_out(2)
        if self.freestanding:
            a.call("k_halt")
        else:
            a.mov_ri32("rdi", 1)
            a.mov_ri32("rax", 60)
            a.syscall()

    def copy_bytes(self):
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
        # x_truth: rdi = tagged -> rax = 0/1
        a.label("x_truth")
        a.mov_rr("rax", "rdi")
        a.and_ri32("rax", 3)
        lab_int, lab_bool, lab_null, lab_heap = (self.new_tmp("tr"),
                                                 self.new_tmp("tr"),
                                                 self.new_tmp("tr"),
                                                 self.new_tmp("tr"))
        lab_bad_truth = self.new_tmp("tr")
        lab_heap_len = self.new_tmp("tr")
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
        a.jcc("e", lab_heap_len)
        a.cmp_ri32("rax", Gen.K_LIST)
        a.jcc("e", lab_heap_len)
        a.cmp_ri32("rax", Gen.K_FUNC)  # functions are always truthy
        a.jcc("ne", lab_bad_truth)
        a.mov_ri32("rax", 1)
        a.ret()
        a.label(lab_heap_len)
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
        lab_pv_str = self.new_tmp("pv")
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
        a.jcc("e", lab_pv_str)
        a.cmp_ri32("rax", Gen.K_LIST)
        a.jcc("ne", lab_pv_bad)
        a.mov_rr("rdi", "r10")
        a.call("x_print_list")
        a.ret()
        a.label(lab_pv_str)
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
        a.mov_rm("rbx", "r10", 8)      # len a (movzx clobbers rax below)
        a.label(lab_loop)
        a.cmp_rr("rcx", "rbx")
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
        a.jcc("e", "eq_str")
        a.cmp_ri32("rax", Gen.K_LIST)
        a.jcc("ne", "eq_raw")
        a.mov_rr("rdi", "r10")
        a.mov_rr("rsi", "r11")
        a.call("x_list_eq")
        a.test_rr("rax", "rax")
        a.setcc_al("e")
        a.movzx_eax_al()
        a.ret()
        a.label("eq_str")
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
        lab_len_ok = self.new_tmp("ln")
        a.mov_rr("r10", "rdi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.test_rr("rax", "rax")
        a.jcc("ne", lab_len_bad)
        a.mov_rm("rcx", "r10", 0)
        a.cmp_ri32("rcx", KS)
        a.jcc("e", lab_len_ok)
        a.cmp_ri32("rcx", Gen.K_LIST)
        a.jcc("ne", lab_len_bad)
        a.label(lab_len_ok)
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
        a.jcc("e", "st_same")
        a.cmp_ri32("rax", Gen.K_LIST)
        a.jcc("ne", "st_bad")
        a.mov_rr("rdi", "r10")
        a.call("x_list_str")
        a.ret()
        a.label("st_same")
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
        # ----- List runtime (header [kind=2][len][cap][buf], items are tags) -----
        # x_list_new: rdi = raw count -> rax = List{len=cap=n}
        a.label("x_list_new")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 32)
        a.mov_mr("rbp", "rdi", -8)     # n
        a.mov_rr("rax", "rdi")
        a.shl_ri8("rax", 3)            # buf bytes
        a.mov_mr("rbp", "rax", -16)
        a.test_rr("rax", "rax")
        lab_nb = self.new_tmp("lq")
        a.jcc("e", lab_nb)
        a.mov_rr("rdi", "rax")
        a.call("x_malloc")
        a.mov_mr("rbp", "rax", -16)    # buf
        a.label(lab_nb)
        a.mov_ri32("rdi", 32)
        a.call("x_malloc")             # header
        a.mov_mr("rbp", "rax", -24)    # obj
        a.mov_ri32("rcx", Gen.K_LIST)
        a.mov_mr("rax", "rcx", 0)
        a.mov_rm("rcx", "rbp", -8)
        a.mov_mr("rax", "rcx", 8)      # len = n
        a.mov_mr("rax", "rcx", 16)     # cap = n
        a.mov_rm("rcx", "rbp", -16)
        a.mov_mr("rax", "rcx", 24)     # buf
        a.mov_rm("rax", "rbp", -24)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_append: rdi = List, rsi = val -> rax = Null (grows buf as needed;
        # the header address never moves, so aliases keep working)
        a.label("x_append")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.mov_mr("rbp", "rdi", -8)     # obj
        a.mov_mr("rbp", "rsi", -16)    # val
        a.mov_rr("r10", "rdi")
        a.mov_rr("rax", "r10")
        a.and_ri32("rax", 3)
        a.test_rr("rax", "rax")
        lab_ap_bad, lab_ap_fit = self.new_tmp("lq"), self.new_tmp("lq")
        a.jcc("ne", lab_ap_bad)
        a.mov_rm("rax", "r10", 0)
        a.cmp_ri32("rax", Gen.K_LIST)
        a.jcc("ne", lab_ap_bad)
        a.mov_rm("rax", "r10", 8)      # len
        a.mov_mr("rbp", "rax", -24)
        a.mov_rm("rax", "r10", 16)     # cap
        a.mov_mr("rbp", "rax", -32)
        a.mov_rm("rcx", "rbp", -24)
        a.cmp_rr("rcx", "rax")
        a.jcc("l", lab_ap_fit)
        # grow: newcap = 4 if cap == 0 else cap * 2
        a.test_rr("rax", "rax")
        lab_ap_nz = self.new_tmp("lq")
        a.jcc("ne", lab_ap_nz)
        a.mov_ri32("rax", 4)
        lab_ap_grow = self.new_tmp("lq")
        a.jmp(lab_ap_grow)
        a.label(lab_ap_nz)
        a.shl_ri8("rax", 1)
        a.label(lab_ap_grow)
        a.mov_mr("rbp", "rax", -40)    # newcap
        a.shl_ri8("rax", 3)
        a.mov_rr("rdi", "rax")
        a.call("x_malloc")             # new buf
        a.mov_rm("rcx", "rbp", -8)     # obj
        a.mov_rm("rsi", "rcx", 24)     # old buf
        a.mov_rm("rdx", "rbp", -40)    # newcap
        a.mov_mr("rcx", "rdx", 16)     # cap = newcap
        a.mov_mr("rcx", "rax", 24)     # buf = newbuf
        a.mov_rm("rdx", "rbp", -24)    # len
        a.mov_rr("rdi", "rax")         # dst
        a.mov_rr("rcx", "rdx")
        a.shl_ri8("rcx", 3)            # bytes
        self.copy_bytes()
        a.jmp(lab_ap_fit)
        a.label(lab_ap_bad)
        a.jmp("type_err")
        a.label(lab_ap_fit)
        a.mov_rm("rax", "rbp", -8)     # obj
        a.mov_rm("rdx", "rax", 24)     # buf
        a.mov_rm("rcx", "rbp", -24)    # len
        a.mov_rm("rsi", "rbp", -16)    # val
        a.mov_mrx("rdx", "rcx", 8, 0, "rsi")
        a.mov_rm("rax", "rbp", -24)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -24)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rcx", "rbp", -24)
        a.mov_mr("rax", "rcx", 8)      # len++
        a.mov_ri64("rax", Gen.HS_NULL)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_list_cat: rdi = a, rsi = b (both List) -> rax = new List
        a.label("x_list_cat")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 40)
        a.mov_mr("rbp", "rdi", -8)
        a.mov_mr("rbp", "rsi", -16)
        a.mov_rm("rax", "rdi", 8)      # la
        a.mov_rm("rcx", "rsi", 8)      # lb
        a.mov_mr("rbp", "rax", -24)
        a.mov_mr("rbp", "rcx", -32)
        a.add_rr("rax", "rcx")         # total
        a.mov_rr("rdi", "rax")
        a.call("x_list_new")
        a.mov_mr("rbp", "rax", -40)    # obj
        # copy a
        a.mov_rm("rsi", "rbp", -8)
        a.mov_rm("rsi", "rsi", 24)     # bufa
        a.mov_rm("rdi", "rbp", -40)
        a.mov_rm("rdi", "rdi", 24)     # buf
        a.mov_rm("rcx", "rbp", -24)
        a.shl_ri8("rcx", 3)
        self.copy_bytes()
        # copy b at buf + la*8
        a.mov_rm("rax", "rbp", -40)
        a.mov_rm("rax", "rax", 24)     # buf
        a.mov_rm("rcx", "rbp", -24)    # la
        a.lea_m("rdi", "rax", 0, "rcx", 8)
        a.mov_rm("rsi", "rbp", -16)
        a.mov_rm("rsi", "rsi", 24)     # bufb
        a.mov_rm("rcx", "rbp", -32)
        a.shl_ri8("rcx", 3)
        self.copy_bytes()
        a.mov_rm("rax", "rbp", -40)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_list_eq: rdi = a, rsi = b (both List) -> rax = 1/0
        a.label("x_list_eq")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 32)
        a.mov_mr("rbp", "rdi", -8)
        a.mov_mr("rbp", "rsi", -16)
        a.mov_rm("rax", "rdi", 8)
        a.mov_rm("rcx", "rsi", 8)
        a.cmp_rr("rax", "rcx")
        lab_lq_ne, lab_lq_eq = self.new_tmp("lq"), self.new_tmp("lq")
        a.jcc("ne", lab_lq_ne)
        a.mov_mr("rbp", "rax", -32)    # len
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -24)    # idx
        lab_lq_top = self.new_tmp("lq")
        a.label(lab_lq_top)
        a.mov_rm("rax", "rbp", -24)
        a.mov_rm("rcx", "rbp", -32)
        a.cmp_rr("rax", "rcx")
        a.jcc("ae", lab_lq_eq)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 24)     # bufa
        a.mov_rm("rcx", "rbp", -24)    # idx
        a.mov_rmx("rdi", "rax", "rcx", 8, 0)
        a.mov_rm("rax", "rbp", -16)
        a.mov_rm("rax", "rax", 24)     # bufb
        a.mov_rmx("rsi", "rax", "rcx", 8, 0)
        a.call("x_eq")
        a.test_rr("rax", "rax")
        a.jcc("e", lab_lq_ne)
        a.mov_rm("rax", "rbp", -24)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -24)
        a.jmp(lab_lq_top)
        a.label(lab_lq_eq)
        a.mov_ri32("rax", 0)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        a.label(lab_lq_ne)
        a.mov_ri32("rax", 1)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_slice(rdi=obj, rsi=a_raw, rdx=b_raw, rcx=mask bit0=a bit1=b).
        # Str (bytes) and List; bounds clamp like interp; empty if a >= b.
        a.label("x_slice")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.mov_mr("rbp", "rdi", -8)     # obj
        a.mov_rm("rax", "rdi", 8)
        a.mov_mr("rbp", "rax", -16)    # n
        a.mov_rr("rax", "rcx")
        a.and_ri32("rax", 1)
        a.test_rr("rax", "rax")
        lab_sna = self.new_tmp("sl")
        a.jcc("e", lab_sna)
        a.mov_mr("rbp", "rsi", -24)    # a
        lab_sha = self.new_tmp("sl")
        a.jmp(lab_sha)
        a.label(lab_sna)
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -24)
        a.label(lab_sha)
        a.mov_rr("rax", "rcx")
        a.and_ri32("rax", 2)
        a.test_rr("rax", "rax")
        lab_snb = self.new_tmp("sl")
        a.jcc("e", lab_snb)
        a.mov_mr("rbp", "rdx", -32)    # b
        lab_shb = self.new_tmp("sl")
        a.jmp(lab_shb)
        a.label(lab_snb)
        a.mov_rm("rax", "rbp", -16)
        a.mov_mr("rbp", "rax", -32)
        a.label(lab_shb)
        # negatives wrap, then clamp to [0, n]
        a.mov_rm("rax", "rbp", -24)
        a.cmp_ri32("rax", 0)
        lab_sap = self.new_tmp("sl")
        a.jcc("ge", lab_sap)
        a.mov_rm("rcx", "rbp", -16)
        a.add_rr("rax", "rcx")
        a.mov_mr("rbp", "rax", -24)
        a.label(lab_sap)
        a.mov_rm("rax", "rbp", -32)
        a.cmp_ri32("rax", 0)
        lab_sbp = self.new_tmp("sl")
        a.jcc("ge", lab_sbp)
        a.mov_rm("rcx", "rbp", -16)
        a.add_rr("rax", "rcx")
        a.mov_mr("rbp", "rax", -32)
        a.label(lab_sbp)
        a.mov_rm("rax", "rbp", -24)
        a.cmp_ri32("rax", 0)
        lab_saz = self.new_tmp("sl")
        a.jcc("ge", lab_saz)
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -24)
        a.label(lab_saz)
        a.mov_rm("rcx", "rbp", -16)
        a.cmp_rr("rax", "rcx")
        lab_sah = self.new_tmp("sl")
        a.jcc("le", lab_sah)
        a.mov_mr("rbp", "rcx", -24)
        a.label(lab_sah)
        a.mov_rm("rax", "rbp", -32)
        a.cmp_ri32("rax", 0)
        lab_sbz = self.new_tmp("sl")
        a.jcc("ge", lab_sbz)
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -32)
        a.label(lab_sbz)
        a.mov_rm("rcx", "rbp", -16)
        a.cmp_rr("rax", "rcx")
        lab_sbh = self.new_tmp("sl")
        a.jcc("le", lab_sbh)
        a.mov_mr("rbp", "rcx", -32)
        a.label(lab_sbh)
        a.mov_rm("rax", "rbp", -24)
        a.mov_rm("rcx", "rbp", -32)
        a.cmp_rr("rax", "rcx")
        lab_sempty = self.new_tmp("sl")
        a.jcc("ae", lab_sempty)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 0)      # kind
        a.cmp_ri32("rax", Gen.K_STR)
        lab_sstr = self.new_tmp("sl")
        a.jcc("e", lab_sstr)
        # list path: new list of b - a, copy buf[a*8..]
        a.mov_rm("rax", "rbp", -32)
        a.mov_rm("rcx", "rbp", -24)
        a.sub_rr("rax", "rcx")
        a.mov_rr("rdi", "rax")
        a.call("x_list_new")
        a.mov_mr("rbp", "rax", -40)    # obj2
        a.mov_rm("rcx", "rbp", -24)    # a
        a.shl_ri8("rcx", 3)            # a*8
        a.mov_rm("rdx", "rbp", -32)    # b
        a.mov_rm("rax", "rbp", -24)
        a.sub_rr("rdx", "rax")
        a.shl_ri8("rdx", 3)            # bytes
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 24)     # buf
        a.add_rr("rax", "rcx")
        a.mov_rr("rsi", "rax")         # src
        a.mov_rm("rax", "rbp", -40)
        a.mov_rm("rax", "rax", 24)     # buf2
        a.mov_rr("rdi", "rax")         # dst
        a.mov_rr("rcx", "rdx")
        self.copy_bytes()
        a.mov_rm("rax", "rbp", -40)
        lab_sdone = self.new_tmp("sl")
        a.jmp(lab_sdone)
        a.label(lab_sstr)
        a.mov_rm("rax", "rbp", -8)
        a.lea_m("rsi", "rax", 16)      # data
        a.mov_rm("rcx", "rbp", -24)    # a
        a.add_rr("rsi", "rcx")
        a.mov_rm("rcx", "rbp", -32)    # b
        a.mov_rm("rax", "rbp", -24)
        a.sub_rr("rcx", "rax")
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rcx")
        a.call("x_str_at")
        a.jmp(lab_sdone)
        a.label(lab_sempty)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 0)
        a.cmp_ri32("rax", Gen.K_STR)
        lab_sempty_s = self.new_tmp("sl")
        a.jcc("e", lab_sempty_s)
        a.mov_ri32("rdi", 0)
        a.call("x_list_new")
        a.jmp(lab_sdone)
        a.label(lab_sempty_s)
        a.mov_rm("rax", "rbp", -8)
        a.lea_m("rdi", "rax", 16)
        a.mov_ri32("rsi", 0)
        a.call("x_str_at")
        a.label(lab_sdone)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_isspace_bit(rcx=byte) -> al = 0/1 via the wspace_ table.
        # Clobbers rax/r10.
        # (inlined at use sites; table covers " \t\n\v\f\r\x1c-\x1f")
        # x_split1(rdi=Str) -> rax = List of words (whitespace runs).
        a.label("x_split1")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.mov_mr("rbp", "rdi", -8)     # obj
        a.mov_rm("rax", "rdi", 8)
        a.mov_mr("rbp", "rax", -16)    # len
        a.mov_ri32("rdi", 0)
        a.call("x_list_new")
        a.mov_mr("rbp", "rax", -32)    # res
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -24)    # i
        lab_sp1_top, lab_sp1_sk = self.new_tmp("sp"), self.new_tmp("sp")
        lab_sp1_wd, lab_sp1_em = self.new_tmp("sp"), self.new_tmp("sp")
        a.label(lab_sp1_top)
        a.mov_rm("rax", "rbp", -24)    # i
        a.mov_rm("rcx", "rbp", -16)    # len
        a.cmp_rr("rax", "rcx")
        lab_sp1_dn = self.new_tmp("sp")
        a.jcc("ae", lab_sp1_dn)
        a.mov_rm("rdx", "rbp", -8)
        a.lea_m("rdx", "rdx", 16)      # data (bytes are inline)
        a.add_rr("rdx", "rax")         # data + i
        a.movzx_eax_m8("rdx", 0)       # byte
        a.lea_rip("rdx", "wspace_")
        a.movzx_edx_mx("rdx", "rax", 1, 0)
        a.test_rr("rdx", "rdx")
        a.jcc("e", lab_sp1_wd)         # non-space -> word
        a.mov_rm("rax", "rbp", -24)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -24)
        a.jmp(lab_sp1_top)
        a.label(lab_sp1_wd)
        a.mov_rm("rax", "rbp", -24)
        a.mov_mr("rbp", "rax", -40)    # start
        a.label(lab_sp1_sk)
        a.mov_rm("rax", "rbp", -24)
        a.mov_rm("rcx", "rbp", -16)
        a.cmp_rr("rax", "rcx")
        a.jcc("ae", lab_sp1_em)
        a.mov_rm("rdx", "rbp", -8)
        a.lea_m("rdx", "rdx", 16)      # data (bytes are inline)
        a.add_rr("rdx", "rax")
        a.movzx_eax_m8("rdx", 0)
        a.lea_rip("rdx", "wspace_")
        a.movzx_edx_mx("rdx", "rax", 1, 0)
        a.test_rr("rdx", "rdx")
        a.jcc("ne", lab_sp1_em)        # space -> emit
        a.mov_rm("rax", "rbp", -24)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -24)
        a.jmp(lab_sp1_sk)
        a.label(lab_sp1_em)
        a.mov_rm("rax", "rbp", -8)
        a.lea_m("rsi", "rax", 16)
        a.mov_rm("rcx", "rbp", -40)
        a.add_rr("rsi", "rcx")         # data + start
        a.mov_rm("rax", "rbp", -24)
        a.sub_rr("rax", "rcx")         # i - start
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rax")
        a.call("x_str_at")             # word
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -32)
        a.call("x_append")
        a.jmp(lab_sp1_top)
        a.label(lab_sp1_dn)
        a.mov_rm("rax", "rbp", -32)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_split2(rdi=s, rsi=sep, rdx=line) -> rax = List of pieces.
        a.label("x_split2")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 64)
        a.mov_mr("rbp", "rdi", -8)     # s
        a.mov_mr("rbp", "rsi", -16)    # sep
        a.mov_mr("rbp", "rdx", -64)    # line
        a.mov_rm("rax", "rdi", 8)
        a.mov_mr("rbp", "rax", -24)    # slen
        a.mov_rm("rax", "rsi", 8)
        a.mov_mr("rbp", "rax", -32)    # seplen
        a.test_rr("rax", "rax")
        lab_sp2_ok = self.new_tmp("sp")
        a.jcc("ne", lab_sp2_ok)
        a.mov_rm("rdx", "rbp", -64)    # line
        self.raise_static_rdx("split with empty separator")
        a.label(lab_sp2_ok)
        a.mov_ri32("rdi", 0)
        a.call("x_list_new")
        a.mov_mr("rbp", "rax", -48)    # res
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -40)    # i
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -56)    # start
        lab_sp2_top = self.new_tmp("sp")
        a.label(lab_sp2_top)
        a.mov_rm("rax", "rbp", -40)    # i
        a.mov_rm("rcx", "rbp", -32)    # seplen
        a.add_rr("rax", "rcx")
        a.mov_rm("rcx", "rbp", -24)    # slen
        a.cmp_rr("rax", "rcx")
        lab_sp2_tail = self.new_tmp("sp")
        a.jcc("a", lab_sp2_tail)
        # memcmp(sdata+i, sepdata, seplen)
        a.mov_rm("rax", "rbp", -8)
        a.lea_m("rax", "rax", 16)      # sdata (bytes are inline)
        a.mov_rm("rcx", "rbp", -40)    # i
        a.add_rr("rax", "rcx")         # sdata + i
        a.mov_rm("rcx", "rbp", -16)
        a.lea_m("rcx", "rcx", 16)      # sepdata (bytes are inline)
        a.mov_rr("r8", "rax")          # p
        a.mov_rr("r9", "rcx")          # q
        a.mov_ri32("rcx", 0)           # j
        lab_sp2_in = self.new_tmp("sp")
        a.label(lab_sp2_in)
        a.mov_rm("rax", "rbp", -32)
        a.cmp_rr("rcx", "rax")
        lab_sp2_mt = self.new_tmp("sp")
        a.jcc("ae", lab_sp2_mt)
        a.movzx_eax_mx("r8", "rcx", 1, 0)
        a.movzx_edx_mx("r9", "rcx", 1, 0)
        a.code += bytes([0x38, 0xD0])  # cmp al, dl
        lab_sp2_nm = self.new_tmp("sp")
        a.jcc("ne", lab_sp2_nm)
        a.add_ri32("rcx", 1)
        a.jmp(lab_sp2_in)
        a.label(lab_sp2_nm)
        a.mov_rm("rax", "rbp", -40)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -40)    # i++
        a.jmp(lab_sp2_top)
        a.label(lab_sp2_mt)
        # emit s[start:i], then i += seplen, start = i
        a.mov_rm("rax", "rbp", -8)
        a.lea_m("rsi", "rax", 16)
        a.mov_rm("rcx", "rbp", -56)
        a.add_rr("rsi", "rcx")
        a.mov_rm("rax", "rbp", -40)
        a.sub_rr("rax", "rcx")
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rax")
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_append")
        a.mov_rm("rax", "rbp", -40)
        a.mov_rm("rcx", "rbp", -32)
        a.add_rr("rax", "rcx")
        a.mov_mr("rbp", "rax", -40)
        a.mov_mr("rbp", "rax", -56)
        a.jmp(lab_sp2_top)
        a.label(lab_sp2_tail)
        a.mov_rm("rax", "rbp", -8)
        a.lea_m("rsi", "rax", 16)
        a.mov_rm("rcx", "rbp", -56)
        a.add_rr("rsi", "rcx")
        a.mov_rm("rax", "rbp", -24)
        a.sub_rr("rax", "rcx")
        a.mov_rr("rdi", "rsi")
        a.mov_rr("rsi", "rax")
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.mov_rm("rdi", "rbp", -48)
        a.call("x_append")
        a.mov_rm("rax", "rbp", -48)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_find(rdi=s, rsi=sub) -> tagged Int (byte index or -1).
        # No calls inside: frameless, values stay in regs.
        a.label("x_find")
        a.mov_rm("rax", "rsi", 8)      # sublen
        a.test_rr("rax", "rax")
        lab_fn0 = self.new_tmp("fn")
        a.jcc("ne", lab_fn0)
        a.mov_ri32("rax", 1)           # tag(0)
        a.ret()
        a.label(lab_fn0)
        a.mov_rm("r11", "rdi", 8)      # slen
        a.mov_rm("rbx", "rsi", 8)      # sublen (rbx: movzx edx must not clobber it)
        a.lea_m("r8", "rdi", 16)       # sdata
        a.lea_m("r9", "rsi", 16)       # subdata
        a.mov_ri32("r10", 0)           # i
        lab_fn_top, lab_fn_in = self.new_tmp("fn"), self.new_tmp("fn")
        lab_fn_mt, lab_fn_nm = self.new_tmp("fn"), self.new_tmp("fn")
        lab_fn_nf = self.new_tmp("fn")
        a.label(lab_fn_top)
        a.mov_rr("rax", "r10")
        a.add_rr("rax", "rbx")         # i + sublen
        a.cmp_rr("rax", "r11")
        a.jcc("a", lab_fn_nf)
        a.mov_rr("rax", "r8")
        a.add_rr("rax", "r10")         # p = sdata + i
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rcx", 0)           # j
        a.label(lab_fn_in)
        a.cmp_rr("rcx", "rbx")         # j vs sublen
        a.jcc("ae", lab_fn_mt)
        a.movzx_eax_mx("rdi", "rcx", 1, 0)
        a.movzx_edx_mx("r9", "rcx", 1, 0)
        a.code += bytes([0x38, 0xD0])  # cmp al, dl
        a.jcc("ne", lab_fn_nm)
        a.add_ri32("rcx", 1)
        a.jmp(lab_fn_in)
        a.label(lab_fn_nm)
        a.add_ri32("r10", 1)
        a.jmp(lab_fn_top)
        a.label(lab_fn_mt)
        a.mov_rr("rax", "r10")
        a.shl_ri8("rax", 2)
        a.or_ri8("rax", 1)             # tag(i)
        a.ret()
        a.label(lab_fn_nf)
        a.mov_ri32("rax", -1)
        a.shl_ri8("rax", 2)
        a.or_ri8("rax", 1)             # tag(-1)
        a.ret()
        # x_join(rdi=sep, rsi=list, rdx=line) -> rax = Str.
        a.label("x_join")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 64)
        a.mov_mr("rbp", "rdi", -8)     # sep
        a.mov_mr("rbp", "rsi", -16)    # list
        a.mov_mr("rbp", "rdx", -56)    # line
        a.mov_rm("rax", "rsi", 8)
        a.mov_mr("rbp", "rax", -24)    # n
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -32)    # total
        a.mov_mr("rbp", "rax", -48)    # idx
        lab_jn_top, lab_jn_dn = self.new_tmp("jn"), self.new_tmp("jn")
        lab_jn_bad = self.new_tmp("jn")
        a.label(lab_jn_top)
        a.mov_rm("rax", "rbp", -48)
        a.mov_rm("rcx", "rbp", -24)
        a.cmp_rr("rax", "rcx")
        a.jcc("ae", lab_jn_dn)
        a.mov_rm("rax", "rbp", -16)
        a.mov_rm("rax", "rax", 24)     # buf
        a.mov_rm("rcx", "rbp", -48)
        a.mov_rmx("rax", "rax", "rcx", 8, 0)  # item
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_jn_bad)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("ne", lab_jn_bad)
        a.mov_rm("rcx", "rax", 8)
        a.mov_rm("rax", "rbp", -32)
        a.add_rr("rax", "rcx")
        a.mov_mr("rbp", "rax", -32)
        a.mov_rm("rax", "rbp", -48)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -48)
        a.jmp(lab_jn_top)
        a.label(lab_jn_bad)
        a.mov_rm("rdx", "rbp", -56)
        self.raise_static_rdx("join needs a list of Str")
        a.label(lab_jn_dn)
        a.mov_rm("rax", "rbp", -32)    # total = sum
        a.mov_rm("rcx", "rbp", -24)    # n
        a.cmp_ri32("rcx", 1)
        lab_jn_nosep = self.new_tmp("jn")
        a.jcc("be", lab_jn_nosep)
        a.mov_rm("rdx", "rbp", -8)
        a.mov_rm("rdx", "rdx", 8)      # seplen
        a.sub_ri32("rcx", 1)
        a.imul_rr("rcx", "rdx")
        a.add_rr("rax", "rcx")
        a.label(lab_jn_nosep)
        a.mov_mr("rbp", "rax", -40)    # total
        a.mov_rr("rdi", "rax")
        a.add_ri32("rdi", 16)
        a.call("x_malloc")
        a.mov_ri32("rcx", Gen.K_STR)
        a.mov_mr("rax", "rcx", 0)
        a.mov_rm("rcx", "rbp", -40)
        a.mov_mr("rax", "rcx", 8)      # len
        a.mov_mr("rbp", "rax", -40)    # out
        a.lea_m("rdx", "rax", 16)
        a.mov_mr("rbp", "rdx", -48)    # dst
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -32)    # idx
        lab_jn_tp2, lab_jn_dn2 = self.new_tmp("jn"), self.new_tmp("jn")
        a.label(lab_jn_tp2)
        a.mov_rm("rax", "rbp", -32)
        a.mov_rm("rcx", "rbp", -24)
        a.cmp_rr("rax", "rcx")
        a.jcc("ae", lab_jn_dn2)
        a.test_rr("rax", "rax")
        lab_jn_nsp = self.new_tmp("jn")
        a.jcc("e", lab_jn_nsp)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rcx", "rax", 8)      # seplen
        a.lea_m("rsi", "rax", 16)      # sepdata
        a.mov_rm("rdi", "rbp", -48)    # dst
        self.copy_bytes()
        a.mov_mr("rbp", "rdi", -48)
        a.label(lab_jn_nsp)
        a.mov_rm("rax", "rbp", -16)
        a.mov_rm("rax", "rax", 24)     # buf
        a.mov_rm("rcx", "rbp", -32)
        a.mov_rmx("rax", "rax", "rcx", 8, 0)  # item
        a.mov_rm("rcx", "rax", 8)      # item len
        a.lea_m("rsi", "rax", 16)      # item bytes
        a.mov_rm("rdi", "rbp", -48)    # dst
        self.copy_bytes()
        a.mov_mr("rbp", "rdi", -48)
        a.mov_rm("rax", "rbp", -32)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -32)
        a.jmp(lab_jn_tp2)
        a.label(lab_jn_dn2)
        a.mov_rm("rax", "rbp", -40)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_range1: rdi = end(tagged) | x_range2: rdi = start, rsi = end
        a.label("x_range1")
        a.mov_rr("r11", "rdi")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", "rg_bad")
        a.sar_ri8("rdi", 2)
        a.mov_rr("rsi", "rdi")
        a.mov_ri32("rdi", 0)
        a.jmp("x_range_core")
        a.label("x_range2")
        a.mov_rr("r11", "rdi")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", "rg_bad")
        a.mov_rr("r11", "rsi")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("ne", "rg_bad")
        a.sar_ri8("rdi", 2)
        a.sar_ri8("rsi", 2)
        a.label("x_range_core")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 32)
        a.mov_mr("rbp", "rdi", -8)     # start
        a.mov_rr("rax", "rsi")
        a.sub_rr("rax", "rdi")         # end - start
        a.mov_ri32("rcx", 0)
        a.cmp_ri32("rax", 0)
        lab_rg0 = self.new_tmp("lq")
        a.jcc("le", lab_rg0)
        a.mov_rr("rcx", "rax")
        a.label(lab_rg0)
        a.mov_mr("rbp", "rcx", -24)    # len
        a.mov_rr("rdi", "rcx")
        a.call("x_list_new")
        a.mov_mr("rbp", "rax", -32)    # obj
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -16)    # idx
        lab_rg_top = self.new_tmp("lq")
        a.label(lab_rg_top)
        a.mov_rm("rax", "rbp", -16)
        a.mov_rm("rcx", "rbp", -24)
        a.cmp_rr("rax", "rcx")
        lab_rg_dn = self.new_tmp("lq")
        a.jcc("ae", lab_rg_dn)
        a.mov_rm("rcx", "rbp", -8)     # start
        a.add_rr("rax", "rcx")         # raw value
        a.shl_ri8("rax", 2)
        a.or_ri8("rax", 1)             # tag
        a.mov_rm("rcx", "rbp", -32)    # obj
        a.mov_rm("rcx", "rcx", 24)     # buf
        a.mov_rm("rdx", "rbp", -16)    # idx
        a.mov_mrx("rcx", "rdx", 8, 0, "rax")
        a.mov_rm("rax", "rbp", -16)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -16)
        a.jmp(lab_rg_top)
        a.label(lab_rg_dn)
        a.mov_rm("rax", "rbp", -32)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        a.label("rg_bad")
        a.jmp("type_err")
        # x_list_str: rdi = List -> rax = Str like [1, x]
        a.label("x_list_str")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 48)
        a.mov_mr("rbp", "rdi", -8)     # obj
        a.mov_rm("rax", "rdi", 8)      # len
        a.mov_mr("rbp", "rax", -32)
        a.test_rr("rax", "rax")
        lab_ls_mt = self.new_tmp("lq")
        a.jcc("e", lab_ls_mt)
        # pass 1: total = 2 + sum(item lens) + 2 * (len - 1)
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -16)    # idx
        a.mov_mr("rbp", "rax", -24)    # sum
        lab_ls_t1 = self.new_tmp("lq")
        a.label(lab_ls_t1)
        a.mov_rm("rax", "rbp", -16)
        a.mov_rm("rcx", "rbp", -32)
        a.cmp_rr("rax", "rcx")
        lab_ls_t2 = self.new_tmp("lq")
        a.jcc("ae", lab_ls_t2)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 24)     # buf
        a.mov_rm("rcx", "rbp", -16)
        a.mov_rmx("rdi", "rax", "rcx", 8, 0)
        a.call("x_str")
        a.mov_mr("rbp", "rax", -40)    # item str
        a.mov_rm("rcx", "rax", 8)
        a.mov_rm("rax", "rbp", -24)
        a.add_rr("rax", "rcx")
        a.mov_mr("rbp", "rax", -24)
        a.mov_rm("rax", "rbp", -16)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -16)
        a.jmp(lab_ls_t1)
        a.label(lab_ls_t2)
        a.mov_rm("rax", "rbp", -24)    # sum
        a.add_ri32("rax", 2)
        a.mov_rm("rcx", "rbp", -32)
        a.sub_ri32("rcx", 1)
        a.shl_ri8("rcx", 1)            # 2 * (len - 1)
        a.add_rr("rax", "rcx")
        a.mov_rr("rdi", "rax")         # total
        a.add_ri32("rdi", 16)          # + header
        a.call("x_malloc")
        a.mov_ri32("rcx", Gen.K_STR)
        a.mov_mr("rax", "rcx", 0)
        a.mov_rm("rcx", "rbp", -24)
        a.mov_rm("rdx", "rbp", -32)
        a.sub_ri32("rdx", 1)
        a.shl_ri8("rdx", 1)
        a.add_rr("rcx", "rdx")
        a.add_ri32("rcx", 2)           # recompute total (sum+2+2*(n-1))
        a.mov_mr("rax", "rcx", 8)
        a.mov_mr("rbp", "rax", -40)    # out str
        a.lea_m("rdx", "rax", 16)      # dst
        a.mov_ri32("rax", 0x5B)        # '['
        a.mov_mr8("rdx", 0, 0)
        a.add_ri32("rdx", 1)
        a.mov_mr("rbp", "rdx", -48)    # dst cursor... (48 < 48? sub was 48: -48 ok)
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -16)    # idx = 0
        lab_ls_t3, lab_ls_dn = self.new_tmp("lq"), self.new_tmp("lq")
        a.label(lab_ls_t3)
        a.mov_rm("rax", "rbp", -16)
        a.mov_rm("rcx", "rbp", -32)
        a.cmp_rr("rax", "rcx")
        a.jcc("ae", lab_ls_dn)
        a.test_rr("rax", "rax")
        lab_ls_ns = self.new_tmp("lq")
        a.jcc("e", lab_ls_ns)
        a.mov_rm("rdx", "rbp", -48)
        a.mov_ri32("rax", 0x2C)        # ','
        a.mov_mr8("rdx", 0, 0)
        a.mov_ri32("rax", 0x20)        # ' '
        a.mov_mr8("rdx", 0, 1)
        a.add_ri32("rdx", 2)
        a.mov_mr("rbp", "rdx", -48)
        a.label(lab_ls_ns)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 24)
        a.mov_rm("rcx", "rbp", -16)
        a.mov_rmx("rdi", "rax", "rcx", 8, 0)
        a.call("x_str")
        a.mov_rm("rcx", "rax", 8)      # item len
        a.lea_m("rsi", "rax", 16)      # item bytes
        a.mov_rm("rdi", "rbp", -48)    # dst cursor
        self.copy_bytes()              # rdi ends at dst + len
        a.mov_mr("rbp", "rdi", -48)    # save cursor
        a.mov_rm("rax", "rbp", -16)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -16)
        a.jmp(lab_ls_t3)
        a.label(lab_ls_dn)
        a.mov_rm("rdx", "rbp", -48)
        a.mov_ri32("rax", 0x5D)        # ']'
        a.mov_mr8("rdx", 0, 0)
        a.mov_rm("rax", "rbp", -40)
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        a.label(lab_ls_mt)
        a.lea_rip("rdi", self.rstr("[]"))
        a.mov_ri32("rsi", 2)
        a.call("x_str_at")
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
        a.ret()
        # x_print_list: rdi = List -> prints [a, b] (no newline)
        a.label("x_print_list")
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        a.sub_ri32("rsp", 32)
        a.mov_mr("rbp", "rdi", -8)     # obj
        a.mov_ri32("rax", 0)
        a.mov_mr("rbp", "rax", -16)    # idx
        a.lea_rip("rdi", self.rstr("["))
        a.mov_ri32("rsi", 1)
        self.rt_out()
        lab_pl_top, lab_pl_dn = self.new_tmp("lq"), self.new_tmp("lq")
        a.label(lab_pl_top)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rcx", "rax", 8)      # len
        a.mov_rm("rax", "rbp", -16)    # idx
        a.cmp_rr("rax", "rcx")
        a.jcc("ae", lab_pl_dn)
        a.test_rr("rax", "rax")
        lab_pl_ns = self.new_tmp("lq")
        a.jcc("e", lab_pl_ns)
        a.lea_rip("rdi", self.rstr(", "))
        a.mov_ri32("rsi", 2)
        self.rt_out()
        a.label(lab_pl_ns)
        a.mov_rm("rax", "rbp", -8)
        a.mov_rm("rax", "rax", 24)     # buf
        a.mov_rm("rcx", "rbp", -16)
        a.mov_rmx("rdi", "rax", "rcx", 8, 0)
        a.call("print_val")
        a.mov_rm("rax", "rbp", -16)
        a.add_ri32("rax", 1)
        a.mov_mr("rbp", "rax", -16)
        a.jmp(lab_pl_top)
        a.label(lab_pl_dn)
        a.lea_rip("rdi", self.rstr("]"))
        a.mov_ri32("rsi", 1)
        self.rt_out()
        a.mov_rr("rsp", "rbp")
        a.pop_r("rbp")
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
    # stash the boot magic and the multiboot info pointer: eax is reused by
    # rdmsr below and edx too, so both must be parked first
    b.mov_mr_abs("MBMAGIC", 0)
    b.mov_mr_abs("MBINFO", 2)
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
    b.labels["MBINFO"] = (A(dat_off + asm64.data_labels["mbinfo_"]) - KBASE)
    b.labels["MBMAGIC"] = (A(dat_off + asm64.data_labels["mbmagic_"]) - KBASE)
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
    # physical end of the kernel image: page tables AND the main stack.
    # The loader places its own data right after the image, so the memory
    # manager reserves everything up to here and never hands those frames
    # out (a frame overlapping the main stack corrupts return addresses
    # and locals in ways that surface far away as wild jumps).
    image_end = stack_top
    ie_off = asm64.data_labels["imageend_"]
    asm64.data[ie_off:ie_off + 8] = _st.pack("<Q", image_end)
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

