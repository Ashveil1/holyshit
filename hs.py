#!/usr/bin/env python3
"""holyshit native backend (เฟส 3a) — AST (from interp.py) -> C -> gcc binary.
usage:
  python3 hs.py build prog.hs [-o prog]   # compile to native binary
  python3 hs.py run prog.hs               # build to temp + execute (JIT-like)
notes:
  - nested functions are lifted; capturing enclosing locals is a compile error
    (use `global`). Shadowing a builtin at module level is a compile error too.
  - top-level return/break/continue are compile errors (interpreter crashes).
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import interp
from interp import HSErr

RT_DIR = os.path.join(HERE, "native")
BUILTINS = {"print", "len", "range", "str", "int", "float",
            "input", "open", "read", "write", "close",
            "alloc", "load8", "load32", "store8", "store32",
            "as_ptr", "as_int",
            "ticks", "readkey", "pmm_alloc", "meminfo",
            "append", "split", "find", "join",
            "argv", "env", "system",
            "tcp_connect", "tcp_send", "tcp_recv", "tcp_close",
            "tcp_listen", "tcp_accept", "http_get",
            "json_parse", "json_str",
            "read_text", "write_text", "append_text", "exists", "ls",
            "mkdir", "json_load", "json_save"}


def cname(prefix, name):
    return f"{prefix}{name}"


def c_esc(s):
    out = []
    for ch in s:
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
        elif 32 <= o < 127:
            out.append(ch)
        else:
            out.append(f"\\{o:03o}")
    return "".join(out)


class Scope:
    def __init__(self, parent=None, module=None):
        self.parent = parent
        if module is None and parent is not None:
            module = parent.module
        self.module = module  # owning Module
        self.params = []
        self.assigned = set()
        self.globals = set()
        self.utypes = {}  # unsafe static vars: name -> I64/U64/Ptr
        self.imported = {}  # top segment -> Module
        self.submods = {}  # submodule segment -> Module (packages)
        self.externs = {}  # name -> ffi sig dict
        self.has_try = False  # function needs volatile locals (longjmp safety)
        self.is_func = False  # set for scopes created by def
        self.caps = set()  # names captured from enclosing scopes (copy at def)


class Module:
    _counter = 0

    def __init__(self, name, path, prog):
        self.name = name
        self.path = path
        self.prog = prog
        self.scope = Scope(module=self)
        if path == "<main>":
            self.cprefix = ""
            self.initfn = None
            self.statevar = None
        else:
            Module._counter += 1
            tag = f"hsM{Module._counter}_{re.sub(r'[^A-Za-z0-9_]', '_', name)}__"
            self.cprefix = tag
            self.initfn = tag + "init"
            self.statevar = tag + "state"


CTYPE = {"I64": "int64_t", "U64": "uint64_t", "Ptr": "uint8_t *"}
UZERO = {"I64": "0", "U64": "0", "Ptr": "0"}
FCTYPE = {"I64": "int64_t", "U64": "uint64_t", "F64": "double",
          "Str": "const char *", "Ptr": "void *", "U0": "void"}


class Gen:
    def __init__(self, prog, main_path="<main>"):
        self.prog = prog
        self.main_path = main_path
        self.main_mod = Module("<main>", "<main>", prog)
        self.mod = self.main_mod.scope
        self.modules = [self.main_mod]
        self.mod_by_path = {}
        self.mod_scanning = set()
        self.shell_by_name = {}
        self.funcs = []  # (cname, node, scope)
        self.gnames = set()  # module-level Val globals to declare (unused now)
        self.tmp = 0
        self.loop_tmp = 0
        self.try_tmp = 0
        self.try_used = False
        self.try_frames = []
        self.try_depth = 0  # lexical try nesting (for handler pops)
        self.loop_trys = []  # try depth at each enclosing loop
        self._fin_stack = []  # (loop_depth, fbody) lexically enclosing emission
        self._fin_active = set()  # ids of fbody nodes currently being emitted
        self._except_stack = []  # HSTry frame vars lexically enclosing emission
        self.ffi_all = []  # (varname, sig) in scan order; sig has cname/rtype/ptypes/lib
        self._deferred_attrs = []  # (node, scope) resolved after full scan
        self._func_stack = []  # scopes of funcs currently being scanned


    # ----- scope scan -----
    def scan_body(self, body, scope, ux=False):
        for s in body:
            self.scan_stmt(s, scope, ux)

    def check_no_ucapture(self, name, scope, line):
        mod = self.mod_of(scope)
        p = scope.parent if scope is not mod.scope else None
        while p is not None and p is not mod.scope:
            if name in p.utypes and name not in p.globals:
                raise HSErr(
                    f"closure capture of unsafe '{name}' not supported (use global dynamic)", line)
            if name in p.globals:
                break
            p = p.parent

    def ffi_lib_kind(self, lib, line):
        # ("default",None) | ("src",abspath) | ("file",abspath) | ("lib",name)
        import os as _os
        if lib is None:
            return ("default", None)
        if lib.endswith(".c"):
            p = lib if _os.path.isabs(lib) else _os.path.abspath(_os.path.join(self.file_dir, lib))
            if not _os.path.isfile(p):
                raise HSErr(f"cannot find ffi source '{lib}'", line)
            return ("src", p)
        if "/" in lib or lib.endswith((".so", ".o", ".a")):
            p = lib if _os.path.isabs(lib) else _os.path.abspath(_os.path.join(self.file_dir, lib))
            if not _os.path.isfile(p):
                raise HSErr(f"cannot find ffi library '{lib}'", line)
            return ("file", p)
        return ("lib", lib)

    def load_module(self, name, from_dir, line):
        import os as _os
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$", name):
            raise HSErr(f"bad module name '{name}'", line)
        hspath = [d for d in _os.environ.get("HSPATH", "").split(":") if d]
        if "." in name:
            parent, _, leaf = name.rpartition(".")
            try:
                pmod = self.load_module(parent, from_dir, line)
            except HSErr as e:
                if f"cannot find module '{parent}'" not in str(e):
                    raise
                pmod = self.shell_module(parent)
            rel = name.replace(".", "/") + ".hs"
            p = None
            for d in [from_dir] + hspath + [_os.getcwd()]:
                if not d:
                    continue
                q = _os.path.abspath(_os.path.join(d, rel))
                if _os.path.isfile(q):
                    p = q
                    break
            if p is None:
                raise HSErr(f"cannot find module '{name}'", line)
            leafmod = self._load_mod_path(name, p, line)
            pmod.scope.submods[leaf] = leafmod
            return leafmod
        if name in self.shell_by_name:
            return self.shell_by_name[name]
        rel = name + ".hs"
        for d in [from_dir] + hspath + [_os.getcwd()]:
            if not d:
                continue
            p = _os.path.abspath(_os.path.join(d, rel))
            if _os.path.isfile(p):
                break
        else:
            raise HSErr(f"cannot find module '{name}'", line)
        return self._load_mod_path(name, p, line)

    def _find_loaded(self, dname):
        for m in self.modules:
            if m.name == dname:
                return m
        return None

    def shell_module(self, name):
        m = self.shell_by_name.get(name)
        if m is None:
            m = Module(name, "<shell>", [])
            self.modules.append(m)
            self.shell_by_name[name] = m
        return m

    def _load_mod_path(self, name, p, line):
        import os as _os
        if p in self.mod_by_path:
            return self.mod_by_path[p]
        if p in self.mod_scanning:
            return None  # circular: runtime reports it
        with open(p, encoding="utf-8") as f:
            src = f.read()
        try:
            prog = interp.parse_program(src)
        except HSErr as e:
            raise HSErr(f"in module '{name}': {e.msg}", e.line)
        mod = Module(name, p, prog)
        self.modules.append(mod)
        self.mod_by_path[p] = mod
        self.mod_scanning.add(p)
        saved_dir = self.file_dir
        self.file_dir = _os.path.dirname(p)
        self.scan_body(prog, mod.scope)
        self.file_dir = saved_dir
        self.mod_scanning.discard(p)
        return mod

    def scan_stmt(self, s, scope, ux=False):
        from interp import UTYPES, UNSAFE_BUILTINS
        t = s["t"]
        if t == "unsafe":
            self.scan_body(s["body"], scope, True)
            return
        if t == "struct":
            return  # layouts registered at parse; typedefs emitted file-scope
        if t == "import":
            n = s["name"]
            top = n.split(".")[0]
            target = self.load_module(n, self.file_dir, s["line"])
            # chain of modules to init, outermost first (None = circular)
            chain = []
            acc = []
            for part in n.split("."):
                acc.append(part)
                dname = ".".join(acc)
                m = self.shell_by_name.get(dname) or self._find_loaded(dname)
                chain.append(m)
            s["_chain"] = chain
            if top in scope.params or top in scope.utypes:
                raise HSErr(f"'{top}' already defined in this scope", s["line"])
            if top in scope.imported:
                if scope.imported[top] is not chain[0] and chain[0] is not None:
                    raise HSErr(f"'{top}' already defined in this scope", s["line"])
            else:
                if top in scope.assigned:
                    raise HSErr(f"'{top}' already defined in this scope", s["line"])
                if chain[0] is not None:
                    scope.imported[top] = chain[0]
            # imported names also occupy a normal slot (holds the T_MOD value)
            scope.assigned.add(top)
            return
        if t == "try":
            self.try_used = True
            scope.has_try = True
            self.scan_body(s["body"], scope, ux)
            if s["ename"] is not None:
                scope.assigned.add(s["ename"])
            if s.get("ebody") is not None:
                self.scan_body(s["ebody"], scope, ux)
            if s.get("fbody") is not None:
                self.scan_body(s["fbody"], scope, ux)
            return
        if t == "raise":
            if s["val"] is not None:
                self.scan_expr(s["val"], scope, ux)
            return
        if t == "extern":
            if ux:
                raise HSErr("extern not allowed in unsafe (declare at top level)", s["line"])
            for d in s["decls"]:
                n = d["name"]
                if n in scope.params or n in scope.assigned or n in scope.utypes \
                        or n in scope.imported or n in scope.externs or n in BUILTINS:
                    raise HSErr(f"'{n}' already defined in this scope", d["line"])
                lib = self.ffi_lib_kind(s["lib"], s["line"])
                sig = {"cname": n, "rtype": d["rtype"], "ptypes": list(d["params"]),
                       "lib": lib, "line": d["line"],
                       "x": f"hsX_{len(self.ffi_all)}_{n}"}
                scope.externs[n] = sig
                self.ffi_all.append((n, sig))
            return
        if t == "udecl":
            n = s["name"]
            if n in scope.params or n in scope.assigned or n in scope.utypes \
                    or n in scope.imported:
                raise HSErr(f"'{n}' already defined in this scope", s["line"])
            if n in scope.globals:
                raise HSErr(f"cannot declare unsafe '{n}' as global", s["line"])
            scope.utypes[n] = s["utype"]
            if s["init"] is not None:
                self.scan_expr(s["init"], scope, True)
            return
        if t == "store":
            self.scan_expr(s["ptr"], scope, True)
            self.scan_expr(s["val"], scope, True)
            return
        if t == "def":
            if ux:
                raise HSErr("def not allowed in unsafe", s["line"])
            if s["name"] in scope.utypes or s["name"] in scope.imported:
                raise HSErr(f"'{s['name']}' already defined in this scope", s["line"])
            scope.assigned.add(s["name"])
            fs = Scope(parent=scope)
            fs.is_func = True
            fs.params = list(s["params"])
            self._func_stack.append(fs)
            self.scan_body(s["body"], fs)
            self._func_stack.pop()
            fs.caplist = sorted(fs.caps)
            s["_scope"] = fs
            s["_cf"] = f"hsF_{len(self.funcs)}"
            self.funcs.append((s["_cf"], s, fs))
            return
        if t == "setindex":
            self.scan_expr(s["obj"], scope, ux)
            self.scan_expr(s["idx"], scope, ux)
            self.scan_expr(s["val"], scope, ux)
            return
        if t == "for" and ux:
            raise HSErr("for not allowed in unsafe (use while)", s["line"])
        if t in ("set",):
            if s["name"] in scope.imported:
                raise HSErr(f"'{s['name']}' is an imported module (cannot assign)", s["line"])
            if not ux:
                self.check_no_ucapture(s["name"], scope, s["line"])
            scope.assigned.add(s["name"])
            self.scan_expr(s["val"], scope, ux)
            return
        if t == "setattr":
            self.scan_expr(s["obj"], scope, ux)
            self.scan_expr(s["val"], scope, ux)
            self._deferred_attrs.append((s, scope))
            return
        if t == "fstore":
            self.scan_expr(s["obj"], scope, ux)
            if s["idx"] is not None:
                self.scan_expr(s["idx"], scope, ux)
            self.scan_expr(s["val"], scope, ux)
            return
        if t == "for":
            if s["var"] in scope.imported:
                raise HSErr(f"'{s['var']}' is an imported module (cannot assign)", s["line"])
            scope.assigned.add(s["var"])
            self.scan_expr(s["iter"], scope, ux)
            self.scan_body(s["body"], scope, ux)
            return
        if t == "global":
            for n in s["names"]:
                if n in self.mod.utypes:
                    raise HSErr(f"cannot declare global for unsafe variable '{n}'", s["line"])
            scope.globals.update(s["names"])
            return
        if t == "expr":
            self.scan_expr(s["val"], scope, ux)
            return
        if t == "print":
            for a in s["args"]:
                self.scan_expr(a, scope, ux)
            return
        if t == "return":
            if s["val"] is not None:
                self.scan_expr(s["val"], scope, ux)
            return
        if t == "if":
            self.scan_expr(s["cond"], scope, ux)
            self.scan_body(s["then"], scope, ux)
            for ec, eb in s["elifs"]:
                self.scan_expr(ec, scope, ux)
                self.scan_body(eb, scope, ux)
            self.scan_body(s["els"], scope, ux)
            return
        if t == "while":
            self.scan_expr(s["cond"], scope, ux)
            self.scan_body(s["body"], scope, ux)
            return

    def scan_expr(self, e, scope, ux=False):
        from interp import UNSAFE_BUILTINS
        t = e["t"]
        if t in ("num", "str"):
            return
        if t == "var":
            e["_res"] = self.resolve(e["name"], scope, e["line"])
            return
        if t in ("neg", "not", "deref"):
            self.scan_expr(e["val"], scope, ux)
            return
        if t == "bin":
            self.scan_expr(e["l"], scope, ux)
            self.scan_expr(e["r"], scope, ux)
            return
        if t == "call":
            fn = e["fn"]
            if ux:
                if fn["t"] != "var" or fn["name"] not in UNSAFE_BUILTINS:
                    got = fn["name"] if fn["t"] == "var" else "expression"
                    raise HSErr(
                        f"cannot call '{got}' from unsafe "
                        f"(only: {', '.join(sorted(UNSAFE_BUILTINS))})", e["line"])
                if fn["name"] == "asm":
                    if len(e["args"]) != 1 or e["args"][0]["t"] != "str":
                        raise HSErr('asm wants asm("...") with a string literal', e["line"])
            else:
                if fn["t"] == "var" and fn["name"] == "asm":
                    raise HSErr("asm only allowed in unsafe", e["line"])
                self.scan_expr(fn, scope, ux)
                if fn["t"] == "var" and fn.get("_res", (None,))[0] == "E":
                    sig = fn["_res"][1]
                    if len(e["args"]) != len(sig["ptypes"]):
                        raise HSErr(f"ffi '{sig['cname']}' wants {len(sig['ptypes'])} args, "
                                    f"got {len(e['args'])}", e["line"])
            for a in e["args"]:
                self.scan_expr(a, scope, ux)
            return
        if t == "index":
            self.scan_expr(e["obj"], scope, ux)
            self.scan_expr(e["idx"], scope, ux)
            return
        if t == "slice":
            self.scan_expr(e["obj"], scope, ux)
            if e["start"] is not None:
                self.scan_expr(e["start"], scope, ux)
            if e["stop"] is not None:
                self.scan_expr(e["stop"], scope, ux)
            if ux:
                raise HSErr("slicing not allowed in unsafe", e["line"])
            return
        if t == "sizeof":
            from interp import HS_STRUCTS
            if e["stype"] not in ("I64", "U64", "Ptr") and e["stype"] not in HS_STRUCTS:
                raise HSErr(f"unknown struct '{e['stype']}'", e["line"])
            return
        if t == "field":
            self.scan_expr(e["obj"], scope, ux)
            if e["idx"] is not None:
                self.scan_expr(e["idx"], scope, ux)
            return
        if t == "attr":
            self.scan_expr(e["obj"], scope, ux)
            if ux:
                raise HSErr("attribute access not allowed in unsafe", e["line"])
            # module resolution deferred: imports may come later textually
            self._deferred_attrs.append((e, scope))
            return
        if t == "list":
            for x in e["items"]:
                self.scan_expr(x, scope, ux)
            return
        if t == "dict":
            for k, v in e["pairs"]:
                self.scan_expr(k, scope, ux)
                self.scan_expr(v, scope, ux)
            return

    def _capture_owner(self, use_scope, bind_scope):
        """Nearest enclosing function scope of use_scope strictly inside bind_scope.
        Returns None when the use is directly in bind_scope (no capture)."""
        q = use_scope
        while q is not None and q is not bind_scope:
            if getattr(q, "is_func", False):
                return q
            q = q.parent
        return None

    def mod_of(self, scope):
        return scope.module if scope.module is not None else self.main_mod

    def find_imported(self, name, scope):
        s = scope
        while s is not None:
            if name in s.imported:
                return s.imported[name]
            if s is self.mod_of(s).scope:
                break
            s = s.parent
        mod = self.mod_of(scope)
        return mod.scope.imported.get(name)

    def member_ref(self, mod, name, line, seen=None):
        """Resolve module.member to a C lvalue + static type info.
        Returns (code, kind) where kind in G/U (dynamic/static)."""
        seen = seen or set()
        if mod.name in seen:
            raise HSErr(f"circular module reference involving '{mod.name}'", line)
        seen.add(mod.name)
        sc = mod.scope
        if name in sc.externs:
            return (None, "E", sc.externs[name])
        if name in sc.submods:
            return ("MOD", sc.submods[name])
        if name in sc.utypes:
            return (mod.cprefix + cname("hsUG_", name), "U", sc.utypes[name])
        if name in sc.assigned:
            return (mod.cprefix + cname("hsG_", name), "G", None)
        if name in sc.imported:
            return self.member_ref(sc.imported[name], name, line, seen)
        raise HSErr(f"module '{mod.name}' has no attribute '{name}'", line)

    def resolve(self, name, scope, line):
        # returns ("L", name) | ("G", cprefix, name) | ("B", name) |
        #         ("MOD", Module) | ("UL", name, utype) | ("UG", cprefix, name, utype) |
        #         ("E", sig)
        mod = self.mod_of(scope)
        s = scope
        if s is mod.scope:
            if name in s.externs:
                return ("E", s.externs[name])
            if name in s.params:
                return ("L", name)
            if name in s.utypes:
                return ("UG", mod.cprefix, name, s.utypes[name])
            if name in s.assigned:
                self.gnames.add((mod.cprefix, name))
                return ("G", mod.cprefix, name)
            if name in s.imported:
                return ("MOD", s.imported[name])
        else:
            if name in s.globals:
                if name in mod.scope.utypes:
                    raise HSErr(
                        f"cannot declare global for unsafe variable '{name}'", line)
                self.gnames.add((mod.cprefix, name))
                return ("G", mod.cprefix, name)
            if name in s.params:
                return ("L", name)
            if name in s.externs:
                return ("E", s.externs[name])
            if name in s.utypes:
                return ("UL", name, s.utypes[name])
            if name in s.assigned:
                return ("L", name)
            if name in s.imported:
                return ("MOD", s.imported[name])
            p = s.parent
            while p is not None and p is not mod.scope:
                if name in p.externs:
                    return ("E", p.externs[name])
                if name in p.utypes and name not in p.globals:
                    raise HSErr(
                        f"closure capture of unsafe '{name}' not supported (use global dynamic)", line)
                if name in p.params or name in p.assigned:
                    if name in p.globals:
                        break
                    # capture: nearest enclosing function scope of the use site
                    # snapshots this value at def (copy semantics)
                    owner = self._capture_owner(scope, p)
                    if owner is None:
                        raise HSErr(
                            f"closure capture of '{name}' not supported yet (use global)", line)
                    if self._func_stack:
                        owner.caps.add(name)
                    return ("C", owner.caplist.index(name) if hasattr(owner, "caplist") else 0)
                if name in p.globals or name in p.imported:
                    break
                p = p.parent
            # fall through to module level below
        if name in mod.scope.externs:
            return ("E", mod.scope.externs[name])
        if name in mod.scope.utypes:
            return ("UG", mod.cprefix, name, mod.scope.utypes[name])
        if name in mod.scope.assigned:
            self.gnames.add((mod.cprefix, name))
            return ("G", mod.cprefix, name)
        if name in mod.scope.imported:
            return ("MOD", mod.scope.imported[name])
        if name in BUILTINS:
            return ("B", name)
        # unknown yet: may be defined later at module level; declare global,
        # runtime chk() reports unknown variable (same laziness as interpreter)
        self.gnames.add((mod.cprefix, name))
        return ("G", mod.cprefix, name)

    def scan(self):
        import os as _os
        if self.main_path and self.main_path != "<main>":
            self.file_dir = _os.path.dirname(_os.path.abspath(self.main_path))
        else:
            self.file_dir = _os.getcwd()
        self.scan_body(self.prog, self.main_mod.scope)
        # every module-level assigned name needs a static Val slot, even if
        # nothing references it (resolve() only registers on reference)
        for mod in self.modules:
            for n in mod.scope.assigned:
                self.gnames.add((mod.cprefix, n))
        # resolve deferred m.attr against final import tables
        for node, sc in self._deferred_attrs:
            o = node["obj"]
            mod = None
            if o["t"] == "var":
                mod = self.find_imported(o["name"], sc)
            elif o["t"] == "attr" and "_mod" in o:
                try:
                    r = self.member_ref(o["_mod"], o["name"], node["line"])
                except HSErr:
                    r = None
                if r is not None and r[0] == "MOD":
                    mod = r[1]
            if mod is not None:
                node["_mod"] = mod

    # ----- emit -----
    def new_tmp(self):
        self.tmp += 1
        return f"hsT{self.tmp}"

    def ref(self, res):
        kind = res[0]
        if kind == "L":
            return cname("hsL_", res[1])
        if kind == "G":
            return res[1] + cname("hsG_", res[2])
        if kind == "UL":
            return cname("hsU_", res[1])
        if kind == "UG":
            return res[1] + cname("hsUG_", res[2])
        raise HSErr(f"bad ref {res}")

    def vdcl(self, scope):
        """'volatile ' when the current function may longjmp (has try)."""
        return "volatile " if getattr(scope, "has_try", False) else ""

    # ----- static (unsafe) expression emitter: -> (type, code, const-or-None). -----
    def coerce_c(self, t, code, const, to_t, out, line):
        """static coerce with C code; const may be None. Emits checks into out."""
        from interp import is_ptr
        if t == to_t:
            return code
        if is_ptr(t) and is_ptr(to_t):
            return code  # addresses: plain and struct pointers mix freely
        if t == "LIT":
            v = const
            if to_t == "I64":
                if not (-(1 << 63) <= v < (1 << 63)):
                    raise HSErr(f"integer {v} too large for I64", line)
                return code
            if to_t == "U64":
                if not (0 <= v < (1 << 64)):
                    raise HSErr(f"integer {v} out of range for U64", line)
                return code
            if is_ptr(to_t):
                if v != 0:
                    raise HSErr("use as_ptr() for addresses (only 0/null allowed here)", line)
                return "((uint8_t *)0)"
        if t == "I64" and to_t == "U64":
            out.append(f"if (({code}) < 0) hs_err({line}, \"negative value as U64\");")
            return f"((uint64_t)({code}))"
        if t == "I64" and is_ptr(to_t):
            out.append(f"if (({code}) < 0) hs_err({line}, \"negative address\");")
            return f"((uint8_t *)(uintptr_t)(uint64_t)({code}))"
        if t == "U64" and to_t == "I64":
            return f"((int64_t)({code}))"
        if t == "U64" and is_ptr(to_t):
            return f"((uint8_t *)(uintptr_t)({code}))"
        raise HSErr(f"cannot convert {t} to {to_t} (use as_ptr/as_int)", line)

    def box_c(self, t, code, line):
        from interp import is_ptr
        if t == "I64" or t == "LIT":
            return f"(v_int({code}))"
        if t == "U64":
            return f"(hs_box_U64({code}, {line}))"
        if is_ptr(t):
            return f"(hs_box_U64((uint64_t)(uintptr_t)({code}), {line}))"
        raise HSErr(f"cannot box {t}", line)

    def unbox_c(self, to_t, code, line):
        from interp import is_ptr
        if to_t == "I64":
            return f"(hs_unbox_I64({code}, {line}))"
        if to_t == "U64":
            return f"(hs_unbox_U64({code}, {line}))"
        if is_ptr(to_t):
            return f"(hs_unbox_Ptr({code}, {line}))"
        raise HSErr(f"bad static type {to_t}", line)

    def s_tmp(self):
        self.tmp += 1
        return f"hsS{self.tmp}"

    def emit_sexpr(self, e, scope, out):
        """static expr -> (type, code, const-or-None)."""
        from interp import UNSAFE_BUILTINS
        t = e["t"]
        ln = e["line"]
        if t == "num":
            v = e["val"]
            if v is None:
                return ("Ptr", "((uint8_t *)0)", 0)
            if isinstance(v, bool):
                return ("I64", f"((int64_t){int(v)})", int(v))
            if isinstance(v, int):
                return ("LIT", f"({v}LL)", v)
            raise HSErr("float not allowed in unsafe", ln)
        if t == "str":
            raise HSErr("strings not allowed in unsafe (use alloc + store8)", ln)
        if t == "var":
            res = e["_res"]
            kind = res[0]
            if kind == "UL":
                return (res[2], self.ref(res), None)
            if kind == "UG":
                return (res[3], self.ref(res), None)
            if kind == "C":
                res = self.resolve(e["name"], scope, ln)
                c = f"(hs_unbox_I64(hs_cur_caps[{res[1]}], {ln}))"
                return ("I64", c, None)
            if kind in ("L", "G"):
                c = f"(hs_unbox_I64(v_chk({self.ref(res)}, \"{e['name']}\", {ln}), {ln}))"
                return ("I64", c, None)
            raise HSErr(f"cannot use builtin '{e['name']}' as value in unsafe", ln)
        if t == "deref":
            pt, pc, _ = self.emit_sexpr(e["val"], scope, out)
            from interp import is_ptr
            if not is_ptr(pt):
                raise HSErr(f"cannot dereference {pt} (need Ptr)", ln)
            return ("I64", f"(hs_ld64({pc}, {ln}))", None)
        if t == "neg":
            st, sc, sv = self.emit_sexpr(e["val"], scope, out)
            from interp import is_ptr
            if is_ptr(st):
                raise HSErr("cannot negate Ptr", ln)
            if st == "LIT":
                return ("LIT", f"(-{sc})", -sv)
            if st == "I64":
                return ("I64", f"(-({sc}))", None)
            return ("U64", f"(-({sc}))", None)
        if t == "not":
            st, sc, _ = self.emit_sexpr(e["val"], scope, out)
            return ("I64", f"((int64_t)(!({sc})))", None)
        if t == "sizeof":
            from interp import HS_STRUCTS
            st = e["stype"]
            if st in ("I64", "U64", "Ptr"):
                return ("I64", "(8LL)", 8)
            L = HS_STRUCTS.get(st)
            if L is None:
                raise HSErr(f"unknown struct '{st}'", ln)
            return ("I64", f"({L['size']}LL)", L["size"])
        if t == "field":
            return self.emit_sfield(e, scope, out)
        if t == "bin":
            return self.emit_sbin(e, scope, out)
        if t == "call":
            return self.emit_scall(e, scope, out)
        if t in ("index", "list", "dict"):
            raise HSErr("collections not allowed in unsafe (use alloc/load/store)", ln)
        if t in ("attr", "slice"):
            raise HSErr(f"{t} not allowed in unsafe", ln)
        raise HSErr(f"bad unsafe expr {t}", ln)

    def sctype(self, typ):
        from interp import is_ptr
        if is_ptr(typ):
            return "uint8_t *"
        return CTYPE[typ]

    def struct_cname(self, sname):
        return f"hsS_{sname}"

    def struct_layout(self, sname, line):
        from interp import HS_STRUCTS
        L = HS_STRUCTS.get(sname)
        if L is None:
            raise HSErr(f"unknown struct '{sname}'", line)
        return L

    def sctype(self, typ):
        from interp import is_ptr
        if is_ptr(typ):
            return "uint8_t *"
        return CTYPE[typ]

    def _field_lvalue(self, e, scope, out):
        """Shared by field reads and fstore. Returns (ftype, C lvalue)."""
        from interp import ptr_struct
        ln = e["line"]
        pt, pc, _ = self.emit_sexpr(e["obj"], scope, out)
        xs = ptr_struct(pt)
        if xs is None:
            raise HSErr(f"cannot access field of {pt} (need a struct pointer)", ln)
        L = self.struct_layout(xs, ln)
        f = L["fields"].get(e["name"])
        if f is None:
            raise HSErr(f"struct '{xs}' has no field '{e['name']}'", ln)
        ft, off, count = f
        if count > 1:
            if e["idx"] is None:
                raise HSErr(f"array field '{e['name']}' needs an index", ln)
            it, ic, iv = self.emit_sexpr(e["idx"], scope, out)
            ic = self.coerce_c(it, ic, iv, "I64", out, ln)
            out.append(f"if (({ic}) < 0 || ({ic}) >= {count}) "
                       f"hs_err({ln}, \"index out of range for '{e['name']}'\");")
            acc = f"(((volatile {self.struct_cname(xs)} *)({pc}))->" \
                  f"{e['name']}[(int64_t)({ic})])"
        else:
            if e["idx"] is not None:
                raise HSErr(f"field '{e['name']}' is not an array", ln)
            acc = f"(((volatile {self.struct_cname(xs)} *)({pc}))->" \
                  f"{e['name']})"
        return ft, acc

    def emit_sfield(self, e, scope, out):
        ft, acc = self._field_lvalue(e, scope, out)
        return (ft, acc, None)

    def emit_fstore_lvalue(self, s, scope, out):
        return self._field_lvalue(
            {"t": "field", "line": s["line"], "obj": s["obj"],
             "name": s["name"], "idx": s["idx"]}, scope, out)

    def emit_sbin(self, e, scope, out):
        op = e["op"]
        ln = e["line"]
        if op in ("and", "or"):
            lt, lc, _ = self.emit_sexpr(e["l"], scope, out)
            tmp = self.s_tmp()
            out.append(f"int64_t {tmp};")
            if op == "and":
                out.append(f"if (({lc}) != 0) {{")
            else:
                out.append(f"if (({lc}) == 0) {{")
            rt, rc, _ = self.emit_sexpr(e["r"], scope, out)
            out.append(f"{tmp} = (({rc}) != 0);")
            out.append("} else {")
            if op == "and":
                out.append(f"{tmp} = 0;")
            else:
                out.append(f"{tmp} = 1;")
            out.append("}")
            return ("I64", tmp, None)
        lt, lc, lcv = self.emit_sexpr(e["l"], scope, out)
        rt, rc, rcv = self.emit_sexpr(e["r"], scope, out)
        from interp import is_ptr, ptr_struct
        if op in ("==", "!="):
            if is_ptr(lt) or is_ptr(rt):
                if not (is_ptr(lt) and is_ptr(rt)):
                    raise HSErr(f"cannot compare {lt} and {rt}", ln)
            else:
                kinds = {lt, rt} - {"LIT"}
                if kinds == {"I64", "U64"}:
                    raise HSErr("cannot compare I64 and U64 (convert explicitly)", ln)
            cmp = "==" if op == "==" else "!="
            return ("I64", f"((int64_t)(({lc}) {cmp} ({rc})))", None)
        if op in ("<", ">", "<=", ">="):
            if is_ptr(lt) or is_ptr(rt):
                raise HSErr("cannot order pointers (use == / !=)", ln)
            if {"I64", "U64"} == ({lt, rt} - {"LIT"}):
                raise HSErr("cannot compare I64 and U64 (convert explicitly)", ln)
            return ("I64", f"((int64_t)(({lc}) {op} ({rc})))", None)
        # arithmetic
        if is_ptr(lt) or is_ptr(rt):
            lxs, rxs = ptr_struct(lt), ptr_struct(rt)
            if lxs:
                lsize = self.struct_layout(lxs, ln)["size"]
            if rxs:
                rsize = self.struct_layout(rxs, ln)["size"]
            if op == "+" and lxs and rt in ("I64", "U64", "LIT"):
                rc2 = self.coerce_c(rt, rc, rcv, "I64", out, ln)
                return (lt, f"(({lc}) + (({rc2}) * {lsize}))", None)
            if op == "+" and rxs and lt in ("I64", "U64", "LIT"):
                lc2 = self.coerce_c(lt, lc, lcv, "I64", out, ln)
                return (rt, f"(({lc2}) * {rsize} + ({rc}))", None)
            if op == "-" and lxs and rt in ("I64", "U64", "LIT"):
                rc2 = self.coerce_c(rt, rc, rcv, "I64", out, ln)
                return (lt, f"(({lc}) - (({rc2}) * {lsize}))", None)
            if op == "-" and lxs and rxs and lxs == rxs:
                return ("I64", f"((int64_t)(((intptr_t)({lc}) - (intptr_t)({rc})) / {lsize}))", None)
            if lt == "Ptr" or rt == "Ptr":
                if op == "+" and lt == "Ptr" and rt in ("I64", "U64", "LIT"):
                    rc2 = self.coerce_c(rt, rc, rcv, "I64", out, ln)
                    return ("Ptr", f"(({lc}) + ({rc2}))", None)
                if op == "+" and rt == "Ptr" and lt in ("I64", "U64", "LIT"):
                    lc2 = self.coerce_c(lt, lc, lcv, "I64", out, ln)
                    return ("Ptr", f"(({lc2}) + ({rc}))", None)
                if op == "-" and lt == "Ptr" and rt in ("I64", "U64", "LIT"):
                    rc2 = self.coerce_c(rt, rc, rcv, "I64", out, ln)
                    return ("Ptr", f"(({lc}) - ({rc2}))", None)
                if op == "-" and lt == "Ptr" and rt == "Ptr":
                    return ("I64", f"((int64_t)(({lc}) - ({rc})))", None)
            raise HSErr(f"cannot apply '{op}' to pointers", ln)
        if lt in ("I64", "U64") and rt in ("I64", "U64") and lt != rt:
            raise HSErr(f"cannot mix I64 and U64 with '{op}' (convert explicitly)", ln)
        tgt = lt if lt != "LIT" else (rt if rt != "LIT" else "I64")
        lc2 = self.coerce_c(lt, lc, lcv, tgt, out, ln)
        rc2 = self.coerce_c(rt, rc, rcv, tgt, out, ln)
        if op in ("/", "%"):
            if rt == "LIT" and rcv == 0:
                raise HSErr("division by zero", ln)
            if not (rt == "LIT"):
                out.append(f"if (({rc2}) == 0) hs_err({ln}, \"division by zero\");")
        return (tgt, f"(({lc2}) {op} ({rc2}))", None)

    def emit_scall(self, e, scope, out):
        from interp import UNSAFE_BUILTINS
        ln = e["line"]
        name = e["fn"]["name"]
        args = e["args"]

        def one(i, want_t=None):
            at, ac, av = self.emit_sexpr(args[i], scope, out)
            if want_t:
                ac = self.coerce_c(at, ac, av, want_t, out, ln)
                return ac
            return at, ac, av

        if name == "alloc":
            if len(args) != 1:
                raise HSErr("alloc wants alloc(n)", ln)
            at, ac, av = self.emit_sexpr(args[0], scope, out)
            ac = self.coerce_c(at, ac, av, "I64", out, ln)
            return ("Ptr", f"(hs_alloc({ac}, {ln}))", None)
        if name in ("load8", "load32"):
            if len(args) != 1:
                raise HSErr(f"{name} wants {name}(p)", ln)
            pt, pc, _ = self.emit_sexpr(args[0], scope, out)
            from interp import is_ptr
            if not is_ptr(pt):
                raise HSErr(f"{name} needs Ptr, got {pt}", ln)
            return ("I64", f"(hs_{name}({pc}, {ln}))", None)
        if name in ("store8", "store32"):
            if len(args) != 2:
                raise HSErr(f"{name} wants {name}(p, v)", ln)
            pt, pc, _ = self.emit_sexpr(args[0], scope, out)
            from interp import is_ptr
            if not is_ptr(pt):
                raise HSErr(f"{name} needs Ptr, got {pt}", ln)
            vt, vc, vv = self.emit_sexpr(args[1], scope, out)
            vc = self.coerce_c(vt, vc, vv, "I64", out, ln)
            return ("I64", f"(hs_{name}({pc}, {vc}, {ln}))", None)
        if name == "as_ptr":
            if len(args) != 1:
                raise HSErr("as_ptr wants as_ptr(int)", ln)
            at, ac, av = self.emit_sexpr(args[0], scope, out)
            from interp import is_ptr
            if at not in ("LIT", "I64", "U64") and not is_ptr(at):
                raise HSErr(f"as_ptr needs an integer, got {at}", ln)
            if at == "Ptr":
                return ("Ptr", ac, None)
            if at == "LIT":
                if not (0 <= av < (1 << 64)):
                    raise HSErr(f"address {av} out of range", ln)
                return ("Ptr", f"((uint8_t *)(uintptr_t)({ac}))", None)
            return ("Ptr", f"((uint8_t *)(uintptr_t)({ac}))", None)
        if name == "as_int":
            if len(args) != 1:
                raise HSErr("as_int wants as_int(p)", ln)
            pt, pc, _ = self.emit_sexpr(args[0], scope, out)
            from interp import is_ptr
            if not is_ptr(pt):
                raise HSErr(f"as_int needs Ptr, got {pt}", ln)
            return ("U64", f"((uint64_t)(uintptr_t)({pc}))", None)
        if name == "asm":
            raise HSErr('asm must be a statement: asm("...")', ln)
        raise HSErr(f"bad unsafe call {name}", ln)

    def ffi_sigdecl(self, sig):
        params = ", ".join(FCTYPE[ft] for _, ft in sig["ptypes"]) or "void"
        return f"{FCTYPE[sig['rtype']]} (*{sig['x']})({params})"

    def ffi_unbox(self, ft, code, ln):
        if ft == "I64":
            return f"(hs_ffi_I64({code}, {ln}))"
        if ft == "U64":
            return f"(hs_ffi_U64({code}, {ln}))"
        if ft == "F64":
            return f"(hs_ffi_F64({code}, {ln}))"
        if ft == "Str":
            return f"(hs_ffi_Str({code}, {ln}))"
        if ft == "Ptr":
            return f"((void *)(hs_unbox_Ptr({code}, {ln})))"
        raise HSErr(f"bad ffi type {ft}", ln)

    def ffi_box(self, rt, call, ln):
        if rt == "I64":
            return f"(v_int({call}))"
        if rt == "U64":
            return f"(hs_box_U64({call}, {ln}))"
        if rt == "F64":
            return f"(v_float({call}))"
        if rt == "Str":
            return f"(hs_box_Str({call}))"
        if rt == "Ptr":
            return f"(v_int((int64_t)(uintptr_t)({call})))"
        raise HSErr(f"bad ffi return type {rt}", ln)

    def emit_ffi_call(self, sig, args, scope, out, ln):
        if len(args) != len(sig["ptypes"]):
            raise HSErr(f"ffi '{sig['cname']}' wants {len(sig['ptypes'])} args, got {len(args)}", ln)
        cargs = []
        for (pn, ft), a in zip(sig["ptypes"], args):
            cargs.append(self.ffi_unbox(ft, self.emit_expr(a, scope, out), ln))
        call = f"{sig['x']}({', '.join(cargs)})"
        tmp = self.new_tmp()
        V = self.vdcl(scope)
        if sig["rtype"] == "U0":
            out.append(f"{call};")
            out.append(f"{V}Val {tmp} = v_null();")
        else:
            out.append(f"{V}Val {tmp} = {self.ffi_box(sig['rtype'], call, ln)};")
        return tmp

    def emit_expr(self, e, scope, out):
        """Append C statements to out; return C expr string for the value."""
        t = e["t"]
        ln = e["line"]
        V = self.vdcl(scope)
        if t == "num":
            v = e["val"]
            if v is True:
                return "v_bool(1)"
            if v is False:
                return "v_bool(0)"
            if v is None:
                return "v_null()"
            if isinstance(v, float):
                return f"v_float({repr(v)})"
            return f"v_int({v}LL)"
        if t == "str":
            return f'v_str("{c_esc(e["val"])}")'
        if t == "var":
            res = e["_res"]
            kind = res[0]
            name = e["name"]
            if kind == "B":
                return f'v_builtin("{name}")'
            if kind == "MOD":
                return f'(v_module("{res[1].name}"))'
            if kind == "E":
                raise HSErr(f"extern '{name}' is not a value (call it)", ln)
            if kind == "C":
                # re-resolve: scan stored a placeholder index, caplist is final now
                res = self.resolve(name, scope, ln)
                return f"(hs_cur_caps[{res[1]}])"
            if kind in ("UL", "UG"):
                utype = res[2] if kind == "UL" else res[3]
                return self.box_c(utype, self.ref(res), ln)
            return f'v_chk({self.ref(res)}, "{name}", {ln})'
        if t == "neg":
            a = self.emit_expr(e["val"], scope, out)
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_neg({a}, {ln});")
            return tmp
        if t == "not":
            a = self.emit_expr(e["val"], scope, out)
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_not({a});")
            return tmp
        if t == "deref":
            raise HSErr("deref only allowed in unsafe", ln)
        if t == "bin":
            op = e["op"]
            if op in ("and", "or"):
                l = self.emit_expr(e["l"], scope, out)
                tmp = self.new_tmp()
                out.append(f"{V}Val {tmp};")
                if op == "and":
                    out.append(f"if (v_truthy({l})) {{")
                else:
                    out.append(f"if (!v_truthy({l})) {{")
                r = self.emit_expr(e["r"], scope, out)
                out.append(f"{tmp} = {r};")
                out.append("} else {")
                out.append(f"{tmp} = {l};")
                out.append("}")
                return tmp
            l = self.emit_expr(e["l"], scope, out)
            r = self.emit_expr(e["r"], scope, out)
            tmp = self.new_tmp()
            if op in ("==", "!="):
                fn = "v_eq" if op == "==" else "v_ne"
                out.append(f"{V}Val {tmp} = {fn}({l}, {r});")
                return tmp
            fn = {"+": "v_add", "-": "v_sub", "*": "v_mul", "/": "v_div",
                  "%": "v_mod", "<": "v_lt",
                  ">": "v_gt", "<=": "v_le", ">=": "v_ge"}[op]
            out.append(f"{V}Val {tmp} = {fn}({l}, {r}, {ln});")
            return tmp
        if t == "call":
            fnexpr = e["fn"]
            if fnexpr["t"] == "var" and fnexpr.get("_res", (None,))[0] == "E":
                return self.emit_ffi_call(fnexpr["_res"][1], e["args"], scope, out, ln)
            if fnexpr["t"] == "attr" and "_mod" in fnexpr:
                mcode, mkind, mpayload = self.member_ref(
                    fnexpr["_mod"], fnexpr["name"], e["line"])
                if mkind == "E":
                    return self.emit_ffi_call(mpayload, e["args"], scope, out, ln)
            args = [self.emit_expr(a, scope, out) for a in e["args"]]
            arr = "(Val[]){%s}" % ", ".join(args) if args else "NULL"
            tmp = self.new_tmp()
            if fnexpr["t"] == "var" and fnexpr.get("_res", (None,))[0] == "B":
                out.append(f"{V}Val {tmp} = b_{fnexpr['name']}({arr}, {len(args)}, {ln});")
            else:
                f = self.emit_expr(fnexpr, scope, out)
                out.append(f"{V}Val {tmp} = v_call({f}, {arr}, {len(args)}, {ln});")
            return tmp
        if t == "index":
            o = self.emit_expr(e["obj"], scope, out)
            i = self.emit_expr(e["idx"], scope, out)
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_index({o}, {i}, {ln});")
            return tmp
        if t == "slice":
            o = self.emit_expr(e["obj"], scope, out)
            s = self.emit_expr(e["start"], scope, out) if e["start"] is not None else "v_null()"
            e2 = self.emit_expr(e["stop"], scope, out) if e["stop"] is not None else "v_null()"
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_slice({o}, {s}, {e2}, {ln});")
            return tmp
        if t == "list":
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_list();")
            for x in e["items"]:
                a = self.emit_expr(x, scope, out)
                out.append(f"v_push({tmp}, {a}, {ln});")
            return tmp
        if t == "attr":
            if "_mod" in e:
                code, kind, ut = self.member_ref(e["_mod"], e["name"], ln)
                if kind == "U":
                    return code
                if kind == "E":
                    raise HSErr(f"extern '{e['name']}' is not a value (call it)", ln)
                return f"v_chk({code}, \"{e['name']}\", {ln})"
            o = self.emit_expr(e["obj"], scope, out)
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_getattr({o}, \"{e['name']}\", {ln});")
            return tmp
        if t == "dict":
            tmp = self.new_tmp()
            out.append(f"{V}Val {tmp} = v_dict();")
            for k, v in e["pairs"]:
                a = self.emit_expr(k, scope, out)
                b = self.emit_expr(v, scope, out)
                out.append(f"v_setindex({tmp}, {a}, {b}, {ln});")
            return tmp
        raise HSErr(f"bad expr {t}", ln)

    def emit_stmt(self, s, scope, out, depth, ux=False):
        t = s["t"]
        ln = s["line"]
        if t == "pass":
            out.append("(void)0;")
            return
        if t == "extern":
            return  # prototypes + init emitted file-scope; nothing per site
        elif t == "unsafe":
            self.emit_body(s["body"], scope, out, depth, True)
        elif t == "struct":
            return  # typedefs emitted file-scope in build()
        elif t == "udecl":
            if s["init"] is not None:
                st, sc, sv = self.emit_sexpr(s["init"], scope, out)
                sc = self.coerce_c(st, sc, sv, s["utype"], out, ln)
                out.append(f"{self.uref(s['name'], scope)} = {sc};")
        elif t == "store":
            pt, pc, _ = self.emit_sexpr(s["ptr"], scope, out)
            from interp import is_ptr
            if not is_ptr(pt):
                raise HSErr(f"cannot store through {pt} (need Ptr)", ln)
            vt, vc, vv = self.emit_sexpr(s["val"], scope, out)
            vc = self.coerce_c(vt, vc, vv, "I64", out, ln)
            out.append(f"hs_st64({pc}, {vc}, {ln});")
        elif t == "fstore":
            ft, acc = self.emit_fstore_lvalue(s, scope, out)
            if s["val"] is None:
                raise HSErr("fstore without value", ln)
            vt, vc, vv = self.emit_sexpr(s["val"], scope, out)
            vc = self.coerce_c(vt, vc, vv, ft, out, ln)
            out.append(f"{acc} = {vc};")
        elif t == "expr":
            if ux:
                v = s["val"]
                if v["t"] == "call" and v["fn"]["t"] == "var" and v["fn"]["name"] == "asm":
                    lit = v["args"][0]["val"]
                    out.append(f'__asm__ volatile("{c_esc(lit)}");')
                else:
                    st, sc, _ = self.emit_sexpr(v, scope, out)
                    out.append(f"(void)({sc});")
            else:
                self.emit_expr(s["val"], scope, out)
        elif t == "print":
            if ux:
                parts = []
                for a in s["args"]:
                    if a["t"] == "str":
                        parts.append(f'(v_str("{c_esc(a["val"])}"))')
                    else:
                        st, sc, _ = self.emit_sexpr(a, scope, out)
                        parts.append(self.box_c(st, sc, ln))
                arr = "(Val[]){%s}" % ", ".join(parts) if parts else "NULL"
                out.append(f"b_print({arr}, {len(parts)}, {ln});")
            else:
                args = [self.emit_expr(a, scope, out) for a in s["args"]]
                arr = "(Val[]){%s}" % ", ".join(args) if args else "NULL"
                out.append(f"b_print({arr}, {len(args)}, {ln});")
        elif t == "set":
            res = self.resolve(s["name"], scope, ln)
            if res[0] in ("UL", "UG"):
                ref = self.ref(res)
                typ = res[2] if res[0] == "UL" else res[3]
                if ux:
                    st, sc, sv = self.emit_sexpr(s["val"], scope, out)
                    sc = self.coerce_c(st, sc, sv, typ, out, ln)
                    out.append(f"{ref} = {sc};")
                else:
                    a = self.emit_expr(s["val"], scope, out)
                    out.append(f"{ref} = {self.unbox_c(typ, a, ln)};")
            elif ux:
                st, sc, _ = self.emit_sexpr(s["val"], scope, out)
                out.append(f"{self.ref(res)} = {self.box_c(st, sc, ln)};")
            else:
                a = self.emit_expr(s["val"], scope, out)
                out.append(f"{self.ref(res)} = {a};")
        elif t == "setindex":
            o = self.emit_expr(s["obj"], scope, out)
            i = self.emit_expr(s["idx"], scope, out)
            v = self.emit_expr(s["val"], scope, out)
            out.append(f"v_setindex({o}, {i}, {v}, {ln});")
        elif t == "setattr":
            if "_mod" in s:
                code, kind, ut = self.member_ref(s["_mod"], s["name"], ln)
                if kind == "E":
                    raise HSErr(f"cannot assign to extern '{s['name']}'", ln)
                if kind == "U":
                    if ux:
                        st, sc, sv = self.emit_sexpr(s["val"], scope, out)
                        sc = self.coerce_c(st, sc, sv, ut, out, ln)
                        out.append(f"{code} = {sc};")
                    else:
                        a = self.emit_expr(s["val"], scope, out)
                        out.append(f"{code} = {self.unbox_c(ut, a, ln)};")
                else:
                    a = self.emit_expr(s["val"], scope, out) if not ux else None
                    if ux:
                        st, sc, _ = self.emit_sexpr(s["val"], scope, out)
                        a = self.box_c(st, sc, ln)
                    out.append(f"{code} = {a};")
            else:
                o = self.emit_expr(s["obj"], scope, out)
                v = self.emit_expr(s["val"], scope, out) if not ux else None
                if ux:
                    st, sc, _ = self.emit_sexpr(s["val"], scope, out)
                    v = self.box_c(st, sc, ln)
                out.append(f"v_setattr({o}, \"{s['name']}\", {v}, {ln});")
        elif t == "import":
            top = s["name"].split(".")[0]
            for m in s.get("_chain", []):
                if m is None:
                    out.append(f"hs_err({ln}, \"circular import '{s['name']}\");")
                    break
                out.append(f"{m.initfn}({ln});")
            out.append(f"{self.ref(self.resolve(top, scope, ln))} = v_module(\"{top}\");")
        elif t == "global":
            pass
        elif t == "return":
            if depth == 0:
                raise HSErr("return outside function", ln)
            self._emit_finallies(out, scope, depth)
            for _ in range(self.try_depth):
                out.append("hs_try_pop();")
            if s["val"] is None:
                out.append("return v_null();")
            elif ux:
                st, sc, _ = self.emit_sexpr(s["val"], scope, out)
                out.append(f"return {self.box_c(st, sc, ln)};")
            else:
                a = self.emit_expr(s["val"], scope, out)
                out.append(f"return {a};")
        elif t == "raise":
            if s["val"] is None:
                if not self._except_stack:
                    raise HSErr("raise without active exception", ln)
                fr = self._except_stack[-1]
                out.append(f"hs_err({fr}.line, \"%s\", {fr}.msg);")
            elif ux:
                v = s["val"]
                if v["t"] != "str":
                    # evaluate dynamically; must be Str (matches interp)
                    a = self.emit_expr(v, scope, out)
                    out.append(f"hs_raise_val({ln}, {a});")
                else:
                    out.append(f"hs_err({ln}, \"%s\", \"{c_esc(v['val'])}\");")
            else:
                a = self.emit_expr(s["val"], scope, out)
                out.append(f"hs_raise_val({ln}, {a});")
        elif t == "break":
            if depth == 0:
                raise HSErr("break outside loop", ln)
            self._emit_finallies(out, scope, depth, for_break=True)
            for _ in range(self.try_depth - self.loop_trys[-1]):
                out.append("hs_try_pop();")
            out.append("break;")
        elif t == "continue":
            if depth == 0:
                raise HSErr("continue outside loop", ln)
            self._emit_finallies(out, scope, depth, for_break=True)
            for _ in range(self.try_depth - self.loop_trys[-1]):
                out.append("hs_try_pop();")
            out.append("continue;")
        elif t == "def":
            if ux:
                raise HSErr("def not allowed in unsafe", ln)
            slot = self.ref(self.resolve(s["name"], scope, ln))
            out.append(f'{slot} = v_func({s["_cf"]}, "{s["name"]}", {len(s["params"])});')
            caps = getattr(s["_scope"], "caplist", [])
            if caps:
                parts = []
                for nm in caps:
                    fake = {"t": "var", "name": nm, "line": ln,
                            "_res": self.resolve(nm, scope, ln)}
                    parts.append(self.emit_expr(fake, scope, out))
                arr = "(Val[]){%s}" % ", ".join(parts)
                out.append(f"v_func_setcaps({slot}, {arr}, {len(caps)});")
        elif t == "if":
            if ux:
                ct, cc, _ = self.emit_sexpr(s["cond"], scope, out)
                out.append(f"if (({cc}) != 0) {{")
                self.emit_body(s["then"], scope, out, depth, ux)
                for ec, eb in s["elifs"]:
                    out.append("} else {")
                    du, dc, _ = self.emit_sexpr(ec, scope, out)
                    out.append(f"if (({dc}) != 0) {{")
                    self.emit_body(eb, scope, out, depth, ux)
                if s["els"]:
                    out.append("} else {")
                    self.emit_body(s["els"], scope, out, depth, ux)
                out.append("}" * (1 + len(s["elifs"])))
                return
            c = self.emit_expr(s["cond"], scope, out)
            out.append(f"if (v_truthy({c})) {{")
            self.emit_body(s["then"], scope, out, depth)
            for ec, eb in s["elifs"]:
                out.append("} else {")
                c2 = self.emit_expr(ec, scope, out)
                out.append(f"if (v_truthy({c2})) {{")
                self.emit_body(eb, scope, out, depth)
            if s["els"]:
                out.append("} else {")
                self.emit_body(s["els"], scope, out, depth)
            out.append("}" * (1 + len(s["elifs"])))
        elif t == "while":
            self.loop_trys.append(self.try_depth)
            if ux:
                out.append("while (1) {")
                ct, cc, _ = self.emit_sexpr(s["cond"], scope, out)
                out.append(f"if (({cc}) == 0) break;")
                self.emit_body(s["body"], scope, out, depth + 1, ux)
                out.append("}")
                self.loop_trys.pop()
                return
            out.append("while (1) {")
            c = self.emit_expr(s["cond"], scope, out)
            out.append(f"if (!v_truthy({c})) break;")
            self.emit_body(s["body"], scope, out, depth + 1)
            out.append("}")
            self.loop_trys.pop()
        elif t == "try":
            if ux:
                raise HSErr("try not allowed in unsafe (wrap the unsafe block instead)", ln)
            self.try_tmp += 1
            tn = self.try_tmp
            has_except = s.get("ebody") is not None
            has_finally = s.get("fbody") is not None
            if has_finally:
                self._fin_stack.append((len(self.loop_trys), s["fbody"]))
            out.append(f"HSTry hsTry{tn};")
            out.append(f"Val * volatile hsSavedCaps{tn} = hs_cur_caps;")
            out.append(f"volatile int hsSavedN{tn} = hs_cur_ncaps;")
            out.append(f"hs_try_push(&hsTry{tn});")
            out.append(f"if (setjmp(hsTry{tn}.buf) == 0) {{")
            self.try_depth += 1
            self.emit_body(s["body"], scope, out, depth)
            self.try_depth -= 1
            out.append("hs_try_pop();")
            if has_finally:
                self._emit_fbody(out, scope, depth, s["fbody"])
            out.append("} else {")
            out.append(f"hs_cur_caps = hsSavedCaps{tn};")
            out.append(f"hs_cur_ncaps = hsSavedN{tn};")
            if has_except:
                self._except_stack.append(f"hsTry{tn}")
                out.append("{")
                out.append(f"char hsEm{tn}[1152];")
                out.append(f"snprintf(hsEm{tn}, sizeof(hsEm{tn}), \"%s at line %d\", "
                           f"hsTry{tn}.msg, hsTry{tn}.line);")
                if s["ename"] is not None:
                    out.append(f"{self.ref(self.resolve(s['ename'], scope, ln))} = v_str(hsEm{tn});")
                if has_finally:
                    # an error raised inside the handler must still run this
                    # try's finally before unwinding further: guard the handler
                    # with its own frame, run finally, then rethrow
                    out.append(f"HSTry hsHandler{tn};")
                    out.append(f"hs_try_push(&hsHandler{tn});")
                    out.append(f"if (setjmp(hsHandler{tn}.buf) == 0) {{")
                self.emit_body(s["ebody"], scope, out, depth)
                if has_finally:
                    out.append("hs_try_pop();")
                    out.append("} else {")
                    # hs_err already popped this frame before longjmp
                    self._emit_fbody(out, scope, depth, s["fbody"])
                    out.append(f"hs_err(hsHandler{tn}.line, \"%s\", hsHandler{tn}.msg);")
                    out.append("}")
                out.append("}")
                self._except_stack.pop()
                if has_finally:
                    self._emit_fbody(out, scope, depth, s["fbody"])
            else:
                if has_finally:
                    self._emit_fbody(out, scope, depth, s["fbody"])
                out.append(f"hs_err(hsTry{tn}.line, \"%s\", hsTry{tn}.msg);")
            out.append("}")
            if has_finally:
                self._fin_stack.pop()
        elif t == "for":
            if ux:
                raise HSErr("for not allowed in unsafe (use while)", ln)
            self.loop_trys.append(self.try_depth)
            it = self.emit_expr(s["iter"], scope, out)
            self.loop_tmp += 1
            li = self.loop_tmp
            out.append(f"{self.vdcl(scope)}Val hsS{li} = v_seq({it}, {ln});")
            out.append(f"for ({self.vdcl(scope)}int64_t hsI{li} = 0; hsI{li} < AS_LIST(hsS{li})->len; hsI{li}++) {{")
            vres = self.resolve(s["var"], scope, ln)
            if vres[0] in ("UL", "UG"):
                utype = vres[2] if vres[0] == "UL" else vres[3]
                out.append(f"{self.ref(vres)} = {self.unbox_c(utype, f'AS_LIST(hsS{li})->items[hsI{li}]', ln)};")
            else:
                out.append(f"{self.ref(vres)} = AS_LIST(hsS{li})->items[hsI{li}];")
            self.emit_body(s["body"], scope, out, depth + 1, ux)
            out.append("}")
            self.loop_trys.pop()
        else:
            raise HSErr(f"bad stmt {t}", ln)

    def uref(self, name, scope):
        mod = self.mod_of(scope)
        if scope is mod.scope:
            return mod.cprefix + cname("hsUG_", name)
        return cname("hsU_", name)

    def lref(self, name, scope):
        if name in scope.globals or scope is self.mod:
            return cname("hsG_", name)
        return cname("hsL_", name)

    def emit_body(self, body, scope, out, depth, ux=False):
        for s in body:
            self.emit_stmt(s, scope, out, depth, ux)

    def _emit_finallies(self, out, scope, depth, for_break=False):
        # emit pending finally bodies, innermost first. return exits every
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
                self.emit_body(fb, scope, out, depth)
            finally:
                self._fin_active.discard(id(fb))

    def _emit_fbody(self, out, scope, depth, fbody):
        # emit a finally body; it never re-runs itself, outer finallys apply.
        self._fin_active.add(id(fbody))
        try:
            self.emit_body(fbody, scope, out, depth)
        finally:
            self._fin_active.discard(id(fbody))

    def emit_func(self, cf, node, scope):
        out = []
        out.append(f"static Val {cf}(Val *hsA, int hsN, int hsCallLine) {{")
        out.append("(void)hsN; (void)hsCallLine;")
        for i, p in enumerate(node["params"]):
            out.append(f"Val {cname('hsL_', p)} = hsA[{i}];")
        for n in sorted(scope.assigned - set(node["params"])):
            out.append(f"{self.vdcl(scope)}Val {cname('hsL_', n)} = v_unbound();")
        for n, typ in sorted(scope.utypes.items()):
            out.append(f"{self.vdcl(scope)}{self.sctype(typ)} {cname('hsU_', n)} = {UZERO.get(typ, '0')};")
        self.emit_body(node["body"], scope, out, 1)
        out.append("return v_null();")
        out.append("}")
        return "\n".join(out)

    def build(self):
        self.scan()
        parts = ['#include "rt.h"', "#include <stddef.h>", "#include <stdint.h>",
                 "#include <stdio.h>", ""]
        from interp import HS_STRUCTS
        for sname in sorted(HS_STRUCTS):
            L = HS_STRUCTS[sname]
            fdecls = []
            for fname in sorted(L["fields"], key=lambda k: L["fields"][k][1]):
                ft, _off, count = L["fields"][fname]
                base = {"I64": "int64_t", "U64": "uint64_t"}.get(ft, "uint8_t *")
                fdecls.append(f"{base} {fname}" + (f"[{count}]" if count > 1 else ""))
            parts.append(f"typedef struct {{ {'; '.join(fdecls)}; }} {self.struct_cname(sname)};")
        if HS_STRUCTS:
            parts.append("")
        vol = "volatile " if self.try_used else ""
        for cp, n in sorted(self.gnames):
            parts.append(f"static {vol}Val {cp + cname('hsG_', n)} = {{T_UNBOUND}};")
        for mod in self.modules:
            for n, typ in sorted(mod.scope.utypes.items()):
                parts.append(f"static {self.sctype(typ)} {mod.cprefix + cname('hsUG_', n)} = {UZERO.get(typ, '0')};")
        for mod in self.modules:
            if mod.initfn is not None:
                parts.append(f"static int {mod.statevar} = 0;")
        # ffi: distinct libs get handles; each decl gets a fn pointer
        ffi_libs = []
        for _, sig in self.ffi_all:
            if sig["lib"] not in ffi_libs:
                ffi_libs.append(sig["lib"])
        for i, lib in enumerate(ffi_libs):
            parts.append(f"static void *hsXlib_{i} = NULL;")
        for _, sig in self.ffi_all:
            parts.append(f"static {self.ffi_sigdecl(sig)};")
        if ffi_libs:
            parts.append("")
        for cf, node, scope in self.funcs:
            parts.append(self.emit_func(cf, node, scope))
            parts.append("")
        for mod in self.modules:
            if mod.initfn is not None:
                parts.append(f"static void {mod.initfn}(int hsLine);")
        if any(m.initfn is not None for m in self.modules):
            parts.append("")
        for mod in self.modules:
            if mod.initfn is None:
                continue
            outm = []
            self.emit_body(mod.prog, mod.scope, outm, 0)
            parts.append(f"static void {mod.initfn}(int hsLine) {{")
            parts.append(f"if ({mod.statevar} == 2) return;")
            parts.append(f"if ({mod.statevar} == 1) hs_err(hsLine, \"circular import '{mod.name}'\");")
            parts.append(f"{mod.statevar} = 1;")
            for n in sorted(mod.scope.assigned):
                parts.append(f"hs_reg_attr(\"{mod.name}\", \"{n}\", "
                             f"&{mod.cprefix + cname('hsG_', n)});")
            parts.extend(outm)
            parts.append(f"{mod.statevar} = 2;")
            parts.append("}")
            parts.append("")
        out = []
        # hosted userland (freestanding kernel goes through x64gen)
        parts.append("int main(int hsAC, char **hsAV) {")
        parts.append("hs_argc = hsAC - 1; hs_argv = hsAV + 1;")
        out.append("/* ffi init */")
        for i, lib in enumerate(ffi_libs):
            kind, val = lib
            if kind in ("default", "src"):
                out.append(f"hsXlib_{i} = hs_ffi_lib(NULL, 0);")
            else:
                out.append(f"hsXlib_{i} = hs_ffi_lib(\"{c_esc(val)}\", 0);")
        for _, sig in self.ffi_all:
            li = ffi_libs.index(sig["lib"])
            params = ", ".join(FCTYPE[ft] for _, ft in sig["ptypes"]) or "void"
            out.append(f"{sig['x']} = ({FCTYPE[sig['rtype']]}(*)({params}))"
                       f"hs_ffi_sym(hsXlib_{li}, \"{sig['cname']}\", 0);")
        self.emit_body(self.prog, self.mod, out, 0)
        parts.extend(out)
        parts.append("return 0;")
        parts.append("}")
        return "\n".join(parts) + "\n"


def gen_c(src, main_path="<main>"):
    prog = interp.parse_program(src)
    return Gen(prog, main_path).build()


def build(prog_path, out_path, as_json=False):
    interp.reset_parse_state()
    def fail(msg, line):
        if as_json:
            _jerr(prog_path, msg, line)
        else:
            print(f"error: {msg}" + (f" at line {line}" if line else ""), file=sys.stderr)
        return 1

    try:
        with open(prog_path, encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        return fail(f"cannot read {prog_path}: {e.strerror or e}", None)
    try:
        gen = Gen(interp.parse_program(src), prog_path)
        code = gen.build()
    except HSErr as e:
        return fail(e.msg, e.line)
    c_path = out_path + ".hs.c"
    with open(c_path, "w", encoding="utf-8") as f:
        f.write(code)
    # collect ffi link inputs from all extern decls
    dep_objs = []
    dep_flags = []
    dep_srcs = []
    for _, sig in gen.ffi_all:
        kind, val = sig["lib"]
        if kind == "src" and val not in dep_srcs:
            dep_srcs.append(val)
        elif kind == "file" and val not in dep_objs:
            dep_objs.append(val)
        elif kind == "lib" and ("-l" + val) not in dep_flags:
            dep_flags.append("-l" + val)
    cleanup = [c_path]
    try:
        for i, s in enumerate(dep_srcs):
            o = f"{out_path}.ffidep{i}.o"
            r = subprocess.run(["gcc", "-O2", "-c", s, "-o", o],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stderr, file=sys.stderr)
                return 1
            dep_objs.append(o)
            cleanup.append(o)
        r = subprocess.run(
            ["gcc", "-O2", "-I", RT_DIR, os.path.join(RT_DIR, "rt.c"),
             c_path] + dep_objs +
            ["-lgc", "-lm", "-ldl", "-rdynamic", "-o", out_path] + dep_flags,
            capture_output=True, text=True)
        if r.returncode != 0:
            if as_json:
                _jerr(prog_path, f"c compile failed: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'gcc error'}", None)
            else:
                print(r.stderr, file=sys.stderr)
            return 1
    finally:
        for p in cleanup:
            if os.path.exists(p):
                os.remove(p)
    return 0


def main(argv):
    if "--version" in argv or "-V" in argv:
        print(f"hs {_version()}")
        return 0
    as_json = False
    if "--json" in argv:
        as_json = True
        argv = [a for a in argv if a != "--json"]
    if len(argv) >= 2 and argv[1] == "lsp":
        import lsp as _lsp
        _lsp.main()
        return 0
    if len(argv) < 3 or argv[1] not in ("build", "run", "check", "fmt",
                                     "xbuild", "xrun", "xkernel"):
        print("usage: hs.py [--json] build prog.hs [-o prog] | hs.py run prog.hs [args...] "
              "| hs.py check prog.hs | hs.py fmt prog.hs [-w|--check] "
              "| hs.py xbuild prog.hs [-o prog] | hs.py xrun prog.hs "
              "| hs.py xkernel prog.hs -o kernel.elf | hs.py lsp",
              file=sys.stderr)
        return 2
    if argv[1] == "fmt":
        import fmt as _fmt
        write = "-w" in argv
        check = "--check" in argv
        files = [a for a in argv[2:] if not a.startswith("-")]
        if not files:
            print("usage: hs.py fmt prog.hs [-w|--check]", file=sys.stderr)
            return 2
        rc = 0
        for path in files:
            try:
                with open(path, encoding="utf-8") as f:
                    src = f.read()
                interp.reset_parse_state()
                out = _fmt.fmt_program(interp.parse_program(src))
            except HSErr as e:
                print(f"{path}: {e}", file=sys.stderr)
                rc = 1
                continue
            except OSError as e:
                print(f"{path}: cannot read: {e.strerror or e}", file=sys.stderr)
                rc = 1
                continue
            if check:
                # comments and blank lines are not reproduced by the printer,
                # so only structure/spacing is compared
                if not _fmt.is_canonical(src, out):
                    print(f"unformatted: {path}", file=sys.stderr)
                    rc = 1
                continue
            if write:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(out)
            else:
                sys.stdout.write(out)
        return rc
    if argv[1] == "check":
        try:
            with open(argv[2], encoding="utf-8") as f:
                src = f.read()
        except OSError as e:
            msg = f"cannot read {argv[2]}: {e.strerror or e}"
            if as_json:
                _jerr(argv[2], msg, None)
            else:
                print(f"error: {msg}", file=sys.stderr)
            return 1
        try:
            interp.reset_parse_state()
            Gen(interp.parse_program(src), argv[2]).scan()
        except HSErr as e:
            if as_json:
                _jerr(argv[2], e.msg, e.line)
            else:
                print(str(e), file=sys.stderr)
            return 1
        if not as_json:
            print(f"ok: {argv[2]}")
        return 0
    if argv[1] == "xbuild":
        import x64gen as _x64
        prog = argv[2]
        out = prog.rsplit(".", 1)[0] + ".x64"
        if "-o" in argv:
            out = argv[argv.index("-o") + 1]
        return _x64.build_x64(prog, out)
    if argv[1] == "xkernel":
        import x64gen as _x64
        prog = argv[2]
        out = "kernel.elf"
        if "-o" in argv:
            out = argv[argv.index("-o") + 1]
        return _x64.build_xkernel(prog, out)
    if argv[1] == "xrun":
        import tempfile as _tf
        import x64gen as _x64
        prog = argv[2]
        with _tf.TemporaryDirectory() as d:
            out = os.path.join(d, "hsxbin")
            rc = _x64.build_x64(prog, out)
            if rc != 0:
                return rc
            r = subprocess.run([out])
            return r.returncode
    if argv[1] == "build":
        prog = argv[2]
        out = prog.rsplit(".", 1)[0]
        if "-o" in argv:
            out = argv[argv.index("-o") + 1]
        return build(prog, out, as_json)
    prog = argv[2]
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "hsbin")
        rc = build(prog, out)
        if rc != 0:
            return rc
        r = subprocess.run([out] + argv[3:])
        return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
