#!/usr/bin/env python3
"""holyshit IR -> x86-64 machine code (no gcc). Task 4, part 1.

    python3 irx64.py prog.hs -o prog   # build through the IR (hosted only)

GenIR subclasses x64gen.Gen and reuses its entire runtime (value model,
heap, builtins, error machinery) plus its leaf emitters. Only the
driving layer is new: IR blocks/temps instead of AST scopes. Semantics
equal x64gen-today by construction (same emitters); the IR path will be
where divergences get fixed, one at a time, after the switchover.

Subset: const/bin/un/br/jmp/ret/phi/load/stvar/stglobal/print/call/
mkfunc plus containers (build_list/dict/index/slice/setindex/iterseq).
try/import/unsafe/extern/attr stay out (later work).
"""
import struct as _st
import sys

import interp
from interp import HSErr
import ir as IR
from x64gen import Gen

NOT_A_VALUE = {
    # var_get's "is not a value (call it)" list minus BI_VALUES (which take
    # the builtin-value path first, exactly like x64gen-today)
    "float", "ticks", "readkey", "pmm_alloc", "meminfo",
    "tcp_connect", "tcp_send", "tcp_recv", "tcp_close", "tcp_listen",
    "tcp_accept", "http_get", "json_parse", "json_str", "read_text",
    "write_text", "append_text", "exists", "ls", "mkdir", "json_load",
    "json_save", "alloc", "load8", "load32", "load64", "store8",
    "store32", "store64", "as_ptr", "as_int", "asm",
}

# builtins with an inline call emitter but no value form in x64gen-today.
# A `load` of one whose temp feeds call-fn positions exclusively gets a
# dummy value (the inline path ignores it); any other use raises.
INLINE_ONLY = {"float"}

# builtins where a DIRECT call must use the inline emitter (exact error
# lines) while first-class uses go through the value/stub protocol
# (whose type errors carry the stub's line 0, like x64gen-today).
INLINE_DIRECT = {"float", "len", "str", "int", "range", "append",
                 "read_text", "write_text", "append_text", "exists", "ls",
                 "mkdir", "read_mem", "has", "contains"}
# NOTE: split/find/join also have inline arms in ev_call but are not in
# INLINE_DIRECT yet: no corpus program triggers their error paths, and
# their success paths work through the stubs. Same for the other
# BI_VALUES builtins (argv/input/env/...). Add on demand with a failing
# differential case in hand.


class GenIR(Gen):
    def emit_malloc(self):
        import gcrt
        gcrt.emit_gc_malloc(self)

    def __init__(self, irmod, prog_dir):
        Gen.__init__(self, [], freestanding=False)
        self.irmod = irmod
        self.prog_dir = prog_dir
        self.flabel = {}  # ir func key -> code label
        self.frames = {}  # ir func key -> frame descriptor
        self.glabels = {}  # (modpfx, name) -> data label
        self.modtab = {}  # dotted name -> module record
        self.funcmod = {}  # ir func key -> module dotted name (""/"a.b")
        self.mod_globals = {}  # modpfx -> set(stored names)
        self.allfuncs = {}
        self.allorder = []
        self.ffi_syms = []   # extern C symbols (GOT slot order)
        self.ffi_libs = []   # DT_NEEDED sonames beyond libc

    # ----- planning (no code): slots, caps, globals -----

    def _glabel(self, name, modpfx=""):
        key = (modpfx, name)
        lab = self.glabels.get(key)
        if lab is None:
            lab = f"hsG_ir_{len(self.glabels)}"
            self.glabels[key] = lab
            self.a.data_label(lab)
            self.a.data_qword(Gen.HS_UNBOUND)
        return lab

    def _find_module(self, name, from_dir, ln):
        import os as _os
        import re as _re
        if not _re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_]"
                         r"[A-Za-z0-9_]*)*$", name):
            raise HSErr(f"bad module name '{name}'", ln)
        hspath = [d for d in _os.environ.get("HSPATH", "").split(":") if d]
        rel = name.replace(".", "/") + ".hs"
        for d in [from_dir] + hspath + [_os.getcwd()]:
            if not d:
                continue
            p = _os.path.abspath(_os.path.join(d, rel))
            if _os.path.isfile(p):
                return p
        raise HSErr(f"cannot find module '{name}'", ln)

    def _load_all(self):
        # depth-first over import instrs (top module first): resolve
        # files parent-first like ensure_prefixes, build each module's IR
        # with a dotted prefix, merge funcs. A module on the active
        # chain re-entered -> circular import (compile error, x64gen).
        import os as _os
        self.pending = []
        self._moddir = {"": self.prog_dir}
        self._seen = {""}
        self.mod_entries = {"": self.irmod["entry"]}
        self.allfuncs.update(self.irmod["funcs"])
        self.allorder.extend(self.irmod["order"])
        for key in self.irmod["order"]:
            self.funcmod[key] = ""
        self._load_mod_body("", self.irmod, [])

    def _json_used(self):
        # textual scan like x64gen uses_json: any call whose callee temp
        # comes from a `load json_*` (shadowing ignored, also like x64gen
        # — the helper merely gets compiled in unused).
        for key in self.allorder:
            fdef = self.allfuncs[key]
            loads = {}
            for b in fdef["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] == "load" and ins.get("dest"):
                        loads[ins["dest"]] = ins["name"]
            for b in fdef["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] == "call" and \
                            loads.get(ins["fn"]) in GenIR.JSON_CALLS:
                        return True
        return False

    def _load_json_if_needed(self):
        # compile runtime/json.hs through the IR like an implicit import
        # (x64gen does the same from AST). Entries become normal merged
        # funcs; calls route through the wrapper below.
        import os as _os
        if not self._json_used():
            self.js_entries = {}
            return
        path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                             "runtime", "json.hs")
        try:
            with open(path, encoding="utf-8") as f:
                src = f.read()
        except OSError as e:
            raise HSErr(f"cannot read {path}: {e.strerror or e}", 1)
        import ir as _IR
        interp.reset_parse_state()
        sub = _IR.build_module(interp.parse_program(src), "<json>.")
        _IR.verify_module(sub)
        self.allfuncs.update(sub["funcs"])
        self.allorder.extend(sub["order"])
        for k in sub["order"]:
            self.funcmod[k] = "<json>"
        self.mod_entries["<json>"] = sub["entry"]
        self.modtab["<json>"] = {"name": "<json>", "shell": False,
                                 "submods": {}, "imports": {},
                                 "irmod": sub,
                                 "dir": _os.path.dirname(path),
                                 "pfx": "<json>."}
        self._moddir["<json>"] = _os.path.dirname(path)
        self.js_entries = {}
        for k in sub["order"]:
            d = sub["funcs"][k]["dispname"]
            if d in ("js_decode", "js_encode"):
                self.js_entries[d] = k

    def _load_mod_body(self, mpref, m, active):
        for key in m["order"]:
            for b in m["funcs"][key]["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] != "import":
                        continue
                    _top, chain = self._resolve_import(
                        ins["name"], self._moddir[mpref], ins["line"],
                        active, mpref, key)
                    ins["_chain"] = chain

    def _resolve_import(self, name, from_dir, ln, active, mpref, funckey):
        parts = name.split(".")
        chain = []
        parent = None
        for i, part in enumerate(parts):
            dotted = ".".join(parts[:i + 1])
            last = (i == len(parts) - 1)
            try:
                path = self._find_module(dotted, from_dir, ln)
                is_shell = False
            except HSErr as e:
                if last or f"cannot find module '{dotted}'" not in str(e):
                    raise
                path = None
                is_shell = True
            if dotted in active:
                raise HSErr(f"circular import '{dotted}'", ln)
            if dotted not in self.modtab:
                rec = {"name": dotted, "shell": is_shell, "submods": {},
                       "imports": {}, "irmod": None, "dir": None, "pfx": ""}
                self.modtab[dotted] = rec
            else:
                rec = self.modtab[dotted]
            if parent is not None:
                parent.setdefault("submods", {})[part] = rec
            parent = rec
            if not is_shell:
                chain.append(rec)
                if rec["irmod"] is None:
                    import os as _os
                    with open(path, encoding="utf-8") as f:
                        src = f.read()
                    try:
                        interp.reset_parse_state()
                        prog = interp.parse_program(src)
                    except HSErr as e:
                        raise HSErr(f"in module '{dotted}': {e.msg}",
                                    e.line)
                    import ir as _IR
                    sub = _IR.build_module(prog, dotted + ".")
                    _IR.verify_module(sub)
                    rec["irmod"] = sub
                    rec["dir"] = _os.path.dirname(path)
                    rec["pfx"] = dotted + "."
                    self._moddir[dotted] = _os.path.dirname(path)
                    self.mod_entries[dotted] = sub["entry"]
                    self.allfuncs.update(sub["funcs"])
                    self.allorder.extend(sub["order"])
                    for k in sub["order"]:
                        self.funcmod[k] = dotted
                    self._load_mod_body(dotted, sub, active + [dotted])
        topmod = self.modtab.get(parts[0])
        if topmod is None:
            topmod = next(m for m in chain if m["name"] == parts[0])
        top = parts[0]
        self.pending.append((funckey, top, name, chain, ln, mpref,
                             self.modtab[parts[0]]))
        return topmod, chain

    def _note_imports(self):
        # "already defined" check + alias/import maps (x64gen collect).
        # Runs after frames exist (needs locals/params).
        for funckey, top, name, chain, ln, mpref, topmod in self.pending:
            fr = self.frames.get(funckey)
            if fr is not None:
                if top in fr.get("params", []) or \
                        top in fr.get("locals", set()):
                    raise HSErr(f"cannot import '{name}': '{top}' is "
                                "already defined", ln)
                fr.setdefault("imports", []).append((name, chain))
                fr.setdefault("aliases", {})[top] = topmod
            if mpref:
                self.modtab[mpref].setdefault("imports", {})[top] = topmod

    JSON_CALLS = {"json_parse", "json_str", "json_load", "json_save"}

    def _plan(self):
        self._load_all()
        self._load_json_if_needed()
        # exception runtime is needed when any function uses try/raise
        self.exc_used = False
        for key in self.allorder:
            for b in self.allfuncs[key]["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] in ("try_push", "reraise"):
                        self.exc_used = True
                tm = b["term"]
                if tm["term"] == "raise":
                    self.exc_used = True
        # per-module globals: stored names in each module's entry func.
        self.mod_globals = {}
        self.global_raw = set()
        self.global_utypes = {}
        for mpref, ekey in self.mod_entries.items():
            names = set()
            for b in self.allfuncs[ekey]["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] in ("stvar", "stglobal"):
                        names.add(ins["name"])
                    if ins["op"] == "sdecl":
                        self.global_raw.add((mpref, ins["name"]))
                        self.global_utypes[(mpref, ins["name"])] = \
                            ins["utype"]
            self.mod_globals[mpref] = names
        self.mglob = self.mod_globals.get("", set())
        for i, key in enumerate(self.allorder):
            self.flabel[key] = f"hsIR_{i}"
            mpref = self.funcmod.get(key, "")
            is_entry = (key == self.mod_entries.get(mpref))
            self.frames[key] = self._plan_func(
                key, self.allfuncs[key], mpref, is_entry)
        # definer links for closure chains (child -> func with the mkfunc)
        parents = {}
        for key in self.allorder:
            for b in self.allfuncs[key]["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] == "mkfunc":
                        parents[ins["func"]] = key
        self.parents = parents
        self._note_imports()
        for key in self.allorder:
            self._plan_res(key)

    def _classify(self, key, name):
        # where does `load name` inside func key resolve? mirrors the
        # x64gen var_get precedence (locals/params/caps first, builtins
        # only when nothing binds, auto-global last) so user shadowing
        # (even of a builtin like `float = 5`) keeps working.
        fr = self.frames[key]
        if name in fr["pmap"] or name in fr["locals"]:
            return "bound"
        seen = set()
        p = self.parents.get(key)
        while p is not None and p not in seen:
            seen.add(p)
            pf = self.frames[p]
            if name in pf["pmap"] or name in pf["locals"] or \
                    name in pf.get("rawnames", ()):
                return "cap"
            p = self.parents.get(p)
        if name in self.mod_globals.get(fr["mod"], set()):
            return "global"
        if name in Gen.BI_VALUES:
            return "builtin"
        if name in NOT_A_VALUE:
            return "novalue"
        return "auto"

    def _plan_res(self, key):
        fdef = self.allfuncs[key]
        fr = self.frames[key]
        loads = set()
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                if ins["op"] == "load":
                    loads.add(ins["name"])
        res = {}
        caps = set()
        for nm in loads:
            k = self._classify(key, nm)
            res[nm] = k
            if k == "cap":
                caps.add(nm)
        fr["res"] = res
        fr["caps"] = sorted(caps)
        # inline-only builtins (float: no value form in x64), direct
        # calls of inlinable builtins (exact error lines), json_* calls
        # (routed to the helper entries), and the json-only type_name
        # hook: a loaded temp that is unshadowed and feeds call-fn
        # positions exclusively gets a dummy value at the load; any other
        # use raises "not a value".
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                if ins["op"] == "load" and (ins["name"] in INLINE_ONLY | \
                        INLINE_DIRECT | GenIR.JSON_CALLS or
                        (ins["name"] == "type_name" and
                         fr.get("mod") == "<json>")) and \
                        res.get(ins["name"]) in ("novalue", "builtin",
                                                 "auto"):
                    ds = ins["dest"]
                    if fr["uses"].get(ds, []) and \
                            all(u == ("call", "fn") for u in fr["uses"][ds]):
                        fr["floattemps"].add(ds)
        # import-alias loads feeding chain positions exclusively (attr
        # obj / print arg resolving to a module / setattr obj / alias-copy
        # stores) are dead: every consumer resolves statically, so emit
        # nothing. Any other use raises first-class via _load.
        chain_roles = {("attr", "obj"), ("print", "arg"),
                       ("setattr", "obj"), ("stvar", "src"),
                       ("stglobal", "src")}
        dead = set()
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                if ins["op"] == "load" and \
                        self._alias_visible(fr, ins["name"]) is not None and \
                        fr["uses"].get(ins["dest"], []) and \
                        all(u in chain_roles for u in
                            fr["uses"][ins["dest"]]):
                    dead.add(ins["dest"])
        fr["deadloads"] = dead

    def _plan_func(self, key, fdef, modpfx, is_entry):
        params = list(fdef["params"])
        pmap = {p: 24 + 8 * i for i, p in enumerate(params)}
        stored = set()
        rawnames = set()
        utypes = {}
        temps = []
        prov = {}
        uses = {}
        def _use(t, role):
            uses.setdefault(t, []).append(role)
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                d = ins.get("dest")
                if d is not None and d not in temps:
                    temps.append(d)
                if ins["op"] == "load":
                    prov[d] = ("load", ins["name"])
                elif ins["op"] == "attr":
                    prov[d] = ("attr", ins["obj"], ins["name"])
                    _use(ins["obj"], ("attr", "obj"))
                elif ins["op"] == "setattr":
                    _use(ins["obj"], ("setattr", "obj"))
                    _use(ins["val"], ("setattr", "val"))
                elif ins["op"] == "call":
                    _use(ins["fn"], ("call", "fn"))
                    for x in ins["args"]:
                        _use(x, ("call", "arg"))
                elif ins["op"] == "print":
                    for x in ins["args"]:
                        _use(x, ("print", "arg"))
                elif ins["op"] == "bin":
                    _use(ins["l"], ("bin", "l"))
                    _use(ins["r"], ("bin", "r"))
                elif ins["op"] == "un":
                    _use(ins["v"], ("un", "v"))
                elif ins["op"] == "index":
                    _use(ins["obj"], ("index", "obj"))
                    _use(ins["idx"], ("index", "idx"))
                elif ins["op"] == "slice":
                    _use(ins["obj"], ("slice", "obj"))
                    for k in ("start", "stop"):
                        if ins[k] is not None:
                            _use(ins[k], ("slice", k))
                elif ins["op"] == "setindex":
                    for k in ("obj", "idx", "val"):
                        _use(ins[k], ("setindex", k))
                elif ins["op"] == "iterseq":
                    _use(ins["src"], ("iterseq", "src"))
                elif ins["op"] in ("stvar", "stglobal"):
                    _use(ins["src"], (ins["op"], "src"))
                elif ins["op"] == "build_list":
                    for x in ins["items"]:
                        _use(x, ("build_list", "items"))
                elif ins["op"] == "build_dict":
                    for k, v in ins["pairs"]:
                        _use(k, ("build_dict", "key"))
                        _use(v, ("build_dict", "val"))
                elif ins["op"] == "phi":
                    for _al, at in ins["arms"]:
                        _use(at, ("phi", "arm"))
                if ins["op"] == "stvar" and not is_entry:
                    stored.add(ins["name"])
                if ins["op"] == "sdecl" and not is_entry:
                    rawnames.add(ins["name"])
                    utypes[ins["name"]] = ins["utype"]
        slots = {}
        n = [0]

        def take():
            n[0] += 1
            return -8 * n[0]

        definstr = {}
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                if ins.get("dest") is not None:
                    definstr[ins["dest"]] = ins
        # duplicate static declarations fail at build, like x64gen's
        # collect (order-sensitive: a later sdecl of a bound name
        # errors; sdecl-then-set is fine).
        bound = set(params)
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                if ins["op"] == "stvar":
                    bound.add(ins["name"])
                elif ins["op"] == "import":
                    bound.add(ins["name"].split(".")[0])
                elif ins["op"] == "sdecl":
                    if ins["name"] in bound:
                        raise HSErr(f"'{ins['name']}' already defined in "
                                    "this scope", ins["line"])
                    bound.add(ins["name"])
        for t in temps:
            slots[t] = take()
        for nm in sorted(stored):
            slots[nm] = take()
        for nm in sorted(rawnames):
            if nm not in slots:
                slots[nm] = take()
        if fdef.get("xname"):
            slots["%cline"] = take()   # ffi: the caller's line (rsi at entry)
        return {"key": key, "params": params, "pmap": pmap,
                "locals": stored, "slots": slots, "nloc": n[0],
                "rawnames": rawnames, "utypes": utypes,
                "caps": [], "res": {}, "prov": prov, "uses": uses,
                "definstr": definstr,
                "floattemps": set(), "mod": modpfx, "is_entry": is_entry}

    # ----- operands -----

    def _load(self, fr, ref, ln):
        """rax = temp or name. Returns the resolution kind for names
        (temps report "temp") so callers can special-case builtins."""
        a = self.a
        if ref.startswith("%"):
            if ref in fr.get("phantoms", {}):
                raise HSErr(f"module '{fr['phantoms'][ref]}' is not a "
                            "first-class value in x64 subset (use "
                            "mod.attr)", ln)
            a.mov_rm("rax", "rbp", fr["slots"][ref])
            return "temp"
        m = self._alias_visible(fr, ref)
        if m is not None:
            raise HSErr(f"module '{m['name']}' is not a first-class "
                        "value in x64 subset (use mod.attr)", ln)
        kind = fr["res"].get(ref)
        if kind is None:
            # names only ever read through sload/captures (never a
            # plain load) miss the plan-time map; classify lazily.
            kind = self._classify(fr["key"], ref)
            fr["res"][ref] = kind
        if kind == "bound":
            if ref in fr["pmap"]:
                a.mov_rm("rax", "rbp", fr["pmap"][ref])
                return "bound"
            a.mov_rm("rax", "rbp", fr["slots"][ref])
            if ref in fr.get("rawnames", ()):
                self.tag_box()
            else:
                self.check_bound(ref, ln)
            return "bound"
        if kind == "cap":
            a.mov_rm("rax", "r15", 8 * fr["caps"].index(ref))
            return "bound"
        if kind == "builtin":
            self.ev_builtin_value(ref)
            return "builtin:" + ref
        if kind == "novalue":
            raise HSErr(f"builtin '{ref}' is not a value (call it)", ln)
        lab = self._glabel(ref, fr["mod"])
        a.lea_rip("rax", lab)
        a.mov_rm("rax", "rax", 0)
        if (fr["mod"], ref) in self.global_raw:
            self.tag_box()
        else:
            self.check_bound(ref, ln)
        return "bound"

    def _store(self, fr, name, ln):
        """rax -> variable slot (params/locals/caps) or module global."""
        a = self.a
        if not fr["is_entry"]:
            if name in fr["pmap"]:
                a.mov_mr("rbp", "rax", fr["pmap"][name])
                return
            if name in fr["locals"] or name in fr["rawnames"]:
                a.mov_mr("rbp", "rax", fr["slots"][name])
                return
            if name in fr["caps"]:
                a.mov_mr("r15", "rax", 8 * fr["caps"].index(name))
                return
        lab = self._glabel(name, fr["mod"])
        a.lea_rip("rcx", lab)
        a.mov_mr("rcx", "rax", 0)

    # ----- instructions (result convention: rax) -----

    def _const(self, v, ln):
        a = self.a
        if v is True:
            a.mov_ri64("rax", Gen.HS_TRUE)
        elif v is False:
            a.mov_ri64("rax", Gen.HS_FALSE)
        elif v is None:
            a.mov_ri64("rax", Gen.HS_NULL)
        elif isinstance(v, float):
            a.mov_ri64("rdi", _st.unpack("<Q", _st.pack("<d", v))[0])
            a.call("x_float_new")
        elif isinstance(v, int):
            a.mov_ri64("rax", self.tag_int(v))
        elif isinstance(v, str):
            b = v.encode()
            lab = self.rstr(v)
            a.lea_rip("rdi", lab)
            a.mov_ri32("rsi", len(b))
            a.call("x_str_at")
        else:
            raise HSErr("IR: bad const value", ln)

    def _bin(self, fr, op, l, r, ln):
        a = self.a
        self._load(fr, l, ln)
        a.push_r("rax")
        self._load(fr, r, ln)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")  # rax = l, rcx = r (both tagged)
        if op == "+":
            self.emit_add(ln)
            return
        if op in ("==", "!="):
            a.mov_rr("rdi", "rax")
            a.mov_rr("rsi", "rcx")
            a.call("x_eq")
            self.box_bool_al()
            if op == "!=":
                a.code += bytes([0x48, 0x83, 0xF0, 0x08])  # xor rax, 8
            return
        if op in ("<", ">", "<=", ">="):
            lab_cmpno, lab_cmperr, lab_cmpok = (self.new_tmp("co"),
                                               self.new_tmp("co"),
                                               self.new_tmp("co"))
            lab_cflt, lab_cnoflt = self.new_tmp("co"), self.new_tmp("co")
            lab_cerr = self.new_tmp("co")
            self.emit_float_check(lab_cflt, lab_cnoflt)
            self.emit_f64_bits("rax", lab_cerr)
            self.emit_f64_bits("rcx", lab_cerr)
            a.movq_xr(0, "rdi")
            a.movq_xr(1, "rsi")
            a.ucomisd(0, 1)
            a.setcc_al({"<": "b", ">": "a", "<=": "be", ">=": "ae"}[op])
            lab_cnan = self.new_tmp("co")
            a.jcc("np", lab_cnan)
            a.xor_rr("rax", "rax")
            a.label(lab_cnan)
            self.box_bool_al()
            lab_cdone = self.new_tmp("co")
            a.jmp(lab_cdone)
            a.label(lab_cerr)
            self.raise_binop(5, ln)
            a.label(lab_cnoflt)
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
            a.label(lab_cdone)
            return
        if op in ("<<", ">>", "&", "|", "^"):
            self._bitop(op, ln)
            return
        if op in ("-", "*", "/", "%"):
            opcodes = {"-": 1, "*": 2, "/": 3, "%": 4}
            lab_aerr = self.new_tmp("ae")
            lab_aflt, lab_noflt = self.new_tmp("ae"), self.new_tmp("ae")
            lab_bok, lab_fdone = self.new_tmp("ae"), self.new_tmp("ae")
            self.emit_float_check(lab_aflt, lab_noflt)
            self.emit_f64_bits("rax", lab_aerr)
            self.emit_f64_bits("rcx", lab_aerr)
            if op in ("/", "%"):
                a.mov_rr("r11", "rsi")
                a.shl_ri8("r11", 1)
                a.test_rr("r11", "r11")
                a.jcc("ne", lab_bok)
                self.raise_static("division by zero", ln)
                a.label(lab_bok)
            if op == "%":
                a.call("x_fmod")
            else:
                a.mov_ri32("rdx", {"-": 1, "*": 2, "/": 3}[op])
                a.call("x_fop")
            a.mov_rr("rdi", "rax")
            a.call("x_float_new")
            a.jmp(lab_fdone)
            a.label(lab_noflt)
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
            elif op == "/":
                # Int / Int is true division: the result is a Float
                # (AGENTS.md: "7 / 2 is 3.5").
                self._int_div_float(ln)
                a.jmp(lab_fdone)
            elif op == "%":
                a.push_r("rdx")
                a.test_rr("rcx", "rcx")
                lab_dz = self.new_tmp("dz")
                a.jcc("ne", lab_dz)
                self.raise_static("division by zero", ln)
                a.label(lab_dz)
                a.cqo()
                a.idiv_r("rcx")
                # idiv remainder takes the dividend's sign; hs follows
                # Python, where it takes the divisor's (-7 % 3 == 2).
                a.mov_rr("rax", "rdx")
                a.test_rr("rax", "rax")
                lab_rmok = self.new_tmp("rm")
                a.jcc("e", lab_rmok)
                a.mov_rr("r10", "rax")
                a.xor_rr("r10", "rcx")
                a.sar_ri8("r10", 63)
                a.test_rr("r10", "r10")
                a.jcc("e", lab_rmok)
                a.add_rr("rax", "rcx")
                a.label(lab_rmok)
                a.pop_r("rdx")
            self.tag_box()
            a.label(lab_fdone)
            return
        raise HSErr(f"IR: '{op}' not in irx64 subset yet", ln)

    def _bitop(self, op, ln):
        # dynamic (tagged) half of Gen.emit_bitop; operands already in
        # rax/rcx. Type/shift errors use interp's wording.
        a = self.a
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
        a.label(lab_err)
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
            a.cmp_ri32("rcx", 63)
            a.jcc("le", lab_sh)
            a.jmp(lab_bad)
            a.label(lab_sh)
            a.test_rr("rcx", "rcx")
            a.jcc("s", lab_bad)
            lab_end = self.new_tmp("be")
            if op == "<<":
                a.shl_cl("rax")
                self.trunc62()
            else:
                a.sar_cl("rax")
            a.jmp(lab_end)
            a.label(lab_bad)
            a.mov_rr("rdi", "rcx")
            a.mov_ri32("rsi", ln)
            a.jmp("hs_shift_err")
            a.label(lab_end)
        elif op == "&":
            a.and_rr("rax", "rcx")
        elif op == "|":
            a.or_rr("rax", "rcx")
        else:
            a.xor_rr("rax", "rcx")
        self.tag_box()

    def _un(self, fr, op, v, ln):
        a = self.a
        self._load(fr, v, ln)
        if op == "neg":
            lab_nfl, lab_nno, lab_ndone = (self.new_tmp("ng"),
                                           self.new_tmp("ng"),
                                           self.new_tmp("ng"))
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.test_rr("r11", "r11")
            a.jcc("ne", lab_nno)
            a.mov_rm("r11", "rax", 0)
            a.cmp_ri32("r11", Gen.K_FLOAT)
            a.jcc("ne", lab_nno)
            a.label(lab_nfl)
            a.mov_rm("rdi", "rax", 8)
            a.mov_ri64("r11", 0x8000000000000000)
            a.xor_rr("rdi", "r11")
            a.call("x_float_new")
            a.jmp(lab_ndone)
            a.label(lab_nno)
            self.check_int(lambda: self.raise_unop(6, ln))
            a.sar_ri8("rax", 2)
            a.neg_r("rax")
            self.tag_box()
            a.label(lab_ndone)
            return
        if op == "not":
            self.truthy()
            a.setcc_al("e")
            self.box_bool_al()
            return
        if op == "unot":
            lab_bad, lab_done = self.new_tmp("un"), self.new_tmp("un")
            self.check_int(lambda: a.jmp(lab_bad))
            a.sar_ri8("rax", 2)
            a.not_rr("rax")
            self.trunc62()
            self.tag_box()
            a.jmp(lab_done)
            a.label(lab_bad)
            self.raise_unop(9, ln)
            a.label(lab_done)
            return
        raise HSErr(f"IR: '{op}' not in irx64 subset yet", ln)

    def _alias_visible(self, fr, name):
        # innermost module binding for `name` that no value slot
        # shadows (mirrors Gen.mod_alias_visible): value slots in the
        # current function win outright (a tie with a same-scope binding
        # goes to the binding); otherwise walk outward.
        if name in fr["pmap"] or name in fr["locals"] or \
                name in fr.get("rawnames", ()):
            return fr.get("aliases", {}).get(name)
        m = fr.get("aliases", {}).get(name)
        if m is not None:
            return m
        seen = set()
        p = self.parents.get(fr["key"])
        while p is not None and p not in seen:
            seen.add(p)
            pf = self.frames[p]
            if name in pf["pmap"] or name in pf["locals"] or \
                    name in pf.get("rawnames", ()):
                return pf.get("aliases", {}).get(name)
            m = pf.get("aliases", {}).get(name)
            if m is not None:
                return m
            p = self.parents.get(p)
        return None

    def _modref(self, fr, ref):
        # temp -> ("mod", rec) | ("mval", rec, attr) | None, following the
        # static prov chain (import aliases and attr results only; module
        # objects never exist at runtime on this path, like x64gen).
        p = fr["prov"].get(ref)
        if p is None:
            return None
        if p[0] == "load":
            m = self._alias_visible(fr, p[1])
            return ("mod", m) if m is not None else None
        if p[0] == "attr":
            base = self._modref(fr, p[1])
            if base is None or base[0] != "mod":
                return None
            return ("mval", base[1], p[2])
        return None

    def _mod_attr(self, modrec, attr, ln):
        # mirrors Gen.mod_global: submodules and re-exported imports are
        # ("sub", ...), real globals are ("lab", ...).
        sub = modrec.get("submods", {}).get(attr)
        if sub is not None:
            return ("sub", sub)
        sub = modrec.get("imports", {}).get(attr)
        if sub is not None:
            return ("sub", sub)
        if attr in self.mod_globals.get(modrec["name"], set()):
            return ("lab", self._glabel(attr, modrec["name"]))
        raise HSErr(f"module '{modrec['name']}' has no attribute '{attr}'",
                    ln)

    def _init_label(self, modrec):
        return "hsM_init_" + modrec["name"].replace(".", "_")

    def _init_done_label(self, modrec):
        return "hsM_done_" + modrec["name"].replace(".", "_")

    SRAW_OPS = {"sconst", "sbin", "sun", "scall", "sderef", "sfield",
                "sload", "sraw"}

    def _is_raw_temp(self, fr, t, seen=None):
        # True when temp t holds an untagged machine word (static world).
        # phi joins sraw/sbin chains only in practice; consensus keeps it
        # exact, anything else falls back to tagged (dispatch path).
        if not t.startswith("%"):
            return False
        ins = fr["definstr"].get(t)
        if ins is None:
            return False
        op = ins["op"]
        if op in GenIR.SRAW_OPS:
            return True
        if op == "phi":
            if seen is None:
                seen = set()
            if t in seen:
                return True
            seen.add(t)
            arms = [self._is_raw_temp(fr, at, seen) for _al, at in
                    ins["arms"]]
            return bool(arms) and all(arms)
        return False

    def _struct_of(self, fr, t, seen=None):
        # struct name behind temp t, for sfield/sfstore layout. Sources:
        # sloads of Ptr:X declarations, +/- propagation, nested fields,
        # phi consensus. Anything else -> None -> build error, exactly
        # like x64gen's "struct type unknown".
        if not t.startswith("%"):
            return None
        if seen is None:
            seen = set()
        if t in seen:
            return None
        seen.add(t)
        ins = fr["definstr"].get(t)
        if ins is None:
            return None
        op = ins["op"]
        if op == "sload":
            ut = fr["utypes"].get(ins["name"])
            if ut is None:
                ut = self.global_utypes.get((fr["mod"], ins["name"]))
            if ut is not None and ut.startswith("Ptr:"):
                return ut[4:]
            return None
        if op == "sbin" and ins["binop"] in ("+", "-"):
            xl = self._struct_of(fr, ins["l"], seen)
            xr = self._struct_of(fr, ins["r"], seen)
            if xl is not None and xr is None:
                return xl
            if xr is not None and xl is None:
                return xr
            return None
        if op == "sfield":
            xs = self._struct_of(fr, ins["obj"], seen)
            if xs is None:
                return None
            from interp import HS_STRUCTS
            L = HS_STRUCTS.get(xs)
            if L is None:
                return None
            f = L["fields"].get(ins["name"])
            if f is None:
                return None
            ft = f[0]
            return ft[4:] if ft.startswith("Ptr:") else None
        if op == "phi":
            xs = {self._struct_of(fr, at, seen) for _al, at in ins["arms"]}
            xs.discard(None)
            return xs.pop() if len(xs) == 1 else None
        return None

    def _sconst(self, fr, dest, stype, val, ln):
        # mirror x64gen sev(num): ints materialize masked-or-raw.
        a = self.a
        if isinstance(val, bool):
            val = int(val)
        a.mov_ri64("rax", val & ((1 << 64) - 1) if val >= 0 else val)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sload(self, fr, dest, name, ln):
        # raw names (locals and module globals) move directly;
        # dynamic-held names unbox (mirror x64gen sev(var)).
        a = self.a
        if name in fr.get("rawnames", ()):
            a.mov_rm("rax", "rbp", fr["slots"][name])
        elif (fr["mod"], name) in self.global_raw:
            a.lea_rip("rax", self._glabel(name, fr["mod"]))
            a.mov_rm("rax", "rax", 0)
        else:
            self._load(fr, name, ln)
            self.unbox_int_here(ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sdecl(self, fr, name, src, ln):
        a = self.a
        if name in fr["pmap"]:
            raise HSErr(f"'{name}' already defined in this scope", ln)
        self._load(fr, src, ln)
        if fr["is_entry"]:
            lab = self._glabel(name, fr["mod"])
            a.lea_rip("rcx", lab)
            a.mov_mr("rcx", "rax", 0)
        else:
            a.mov_mr("rbp", "rax", fr["slots"][name])

    def _sset(self, fr, name, src, ln):
        # mirror _sset_exec resolution, machine-word edition: raw
        # holders (locals, raws, module-raw globals) take the word;
        # dynamic holders take it boxed (blind tag_box). x64gen-today
        # stores raw unconditionally (crashing on mixed flows); the IR
        # path matches interp instead (documented improvement).
        a = self.a
        if name in fr.get("rawnames", ()):
            self._load(fr, src, ln)
            a.mov_mr("rbp", "rax", fr["slots"][name])
            return
        if name in fr["pmap"] or name in fr["locals"]:
            self._load(fr, src, ln)
            self.tag_box()
            if name in fr["pmap"]:
                a.mov_mr("rbp", "rax", fr["pmap"][name])
            else:
                a.mov_mr("rbp", "rax", fr["slots"][name])
            return
        if name in fr.get("caps", ()):
            self._load(fr, src, ln)
            self.tag_box()
            a.mov_mr("r15", "rax", 8 * fr["caps"].index(name))
            return
        self._load(fr, src, ln)
        if (fr["mod"], name) in self.global_raw:
            lab = self._glabel(name, fr["mod"])
            a.lea_rip("rcx", lab)
            a.mov_mr("rcx", "rax", 0)
        else:
            self.tag_box()
            lab = self._glabel(name, fr["mod"])
            a.lea_rip("rcx", lab)
            a.mov_mr("rcx", "rax", 0)

    def _sstore(self, fr, ptr, val, ln):
        # mirror ex_unsafe store: no null check (hardware faults).
        a = self.a
        self._load(fr, ptr, ln)
        a.push_r("rax")
        self._load(fr, val, ln)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")
        a.mov_mr("rax", "rcx", 0)

    def _sfstore(self, fr, obj, name, idx, val, ln):
        # transliterated ex_unsafe fstore (null + bounds checked hosted).
        from interp import HS_STRUCTS
        a = self.a
        xs = self._struct_of(fr, obj)
        if xs is None or xs not in HS_STRUCTS:
            raise HSErr("struct type unknown (x64)", ln)
        f = HS_STRUCTS[xs]["fields"].get(name)
        if f is None:
            raise HSErr(f"struct '{xs}' has no field '{name}'", ln)
        ft, off, count = f
        self._load(fr, obj, ln)
        a.push_r("rax")
        lab_nn = self.new_tmp("nn")
        a.test_rr("rax", "rax")
        a.jcc("ne", lab_nn)
        self.raise_static("null pointer dereference", ln)
        a.label(lab_nn)
        a.pop_r("rax")
        if count > 1:
            if idx is None:
                raise HSErr(f"array field '{name}' needs an index", ln)
            a.push_r("rax")
            self._load(fr, idx, ln)
            a.mov_rr("rcx", "rax")
            a.pop_r("rax")
            a.cmp_ri32("rcx", count)
            lab_ok = self.new_tmp("bd")
            a.jcc("b", lab_ok)
            self.raise_struct_oob(name, count, ln)
            a.label(lab_ok)
            a.lea_m("rax", "rax", off, "rcx", 8)
        else:
            if idx is not None:
                raise HSErr(f"field '{name}' is not an array", ln)
            a.lea_m("rax", "rax", off)
        a.push_r("rax")
        self._load(fr, val, ln)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")
        a.mov_mr("rax", "rcx", 0)

    def _sbin(self, fr, dest, op, l, r, ln):
        # type-blind raw words, exactly like x64gen sev_bin (signed ops,
        # truncating division, no mix checks). interp-strictness lives in
        # the IR interpreter; the machine matches x64gen-today bit for bit.
        a = self.a
        self._load(fr, l, ln)
        a.push_r("rax")
        self._load(fr, r, ln)
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
        elif op in ("<<", ">>", "&", "|", "^"):
            self._sbitop(op, ln)
        else:
            raise HSErr(f"IR: '{op}' not in irx64 subset yet", ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sbitop(self, op, ln):
        # rax/rcx raw words in, rax raw out. Mirrors the shared body of
        # Gen.emit_bitop with dynamic=False (no tag checks, count checks
        # and 62-bit << truncation kept).
        a = self.a
        if op in ("<<", ">>"):
            lab_sh, lab_bad = self.new_tmp("be"), self.new_tmp("be")
            a.cmp_ri32("rcx", 63)
            a.jcc("le", lab_sh)
            a.jmp(lab_bad)
            a.label(lab_sh)
            a.test_rr("rcx", "rcx")
            a.jcc("s", lab_bad)
            lab_end = self.new_tmp("be")
            if op == "<<":
                a.shl_cl("rax")
                self.trunc62()
            else:
                a.sar_cl("rax")
            a.jmp(lab_end)
            a.label(lab_bad)
            a.mov_rr("rdi", "rcx")
            a.mov_ri32("rsi", ln)
            a.jmp("hs_shift_err")
            a.label(lab_end)
        elif op == "&":
            a.and_rr("rax", "rcx")
        elif op == "|":
            a.or_rr("rax", "rcx")
        else:
            a.xor_rr("rax", "rcx")

    def _sun(self, fr, dest, op, v, ln):
        a = self.a
        self._load(fr, v, ln)
        if op == "neg":
            a.neg_r("rax")
        elif op == "not":
            a.test_rr("rax", "rax")
            a.setcc_al("e")
            a.movzx_eax_al()
        elif op == "unot":
            a.not_rr("rax")
        else:
            raise HSErr(f"IR: '{op}' not in irx64 subset yet", ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _scall(self, fr, dest, name, args, ln):
        # transliterated x64gen sev_call (raw words, machine checks only).
        a = self.a
        if name == "alloc":
            if len(args) != 1:
                raise HSErr("alloc wants alloc(n)", ln)
            self._load(fr, args[0], ln)
            a.push_r("rax")
            a.call("x_alloc")
            a.add_ri32("rsp", 8)
        elif name in ("load8", "load32", "load64"):
            if len(args) != 1:
                raise HSErr(f"{name} wants {name}(p)", ln)
            self._load(fr, args[0], ln)
            if name == "load8":
                a.code += bytes([0x48, 0x0F, 0xB6, 0x00])
            elif name == "load32":
                a.code += bytes([0x8B, 0x00])
            else:
                a.code += bytes([0x48, 0x8B, 0x00])
        elif name in ("store8", "store32", "store64"):
            if len(args) != 2:
                raise HSErr(f"{name} wants {name}(p, v)", ln)
            self._load(fr, args[1], ln)
            a.push_r("rax")
            self._load(fr, args[0], ln)
            a.pop_r("rcx")
            if name == "store8":
                a.code += bytes([0x88, 0x08])
            elif name == "store32":
                a.code += bytes([0x89, 0x08])
            else:
                a.code += bytes([0x48, 0x89, 0x08])
            a.mov_rr("rax", "rcx")
        elif name in ("as_ptr", "as_int"):
            if len(args) != 1:
                raise HSErr(f"{name} wants 1 arg", ln)
            # non-var args always evaluate to raw words (every _sexpr
            # result is raw), so they pass through untouched.
            self._load(fr, args[0], ln)
        else:
            raise HSErr("only alloc/load/store/as_* calls allowed in "
                        "unsafe (x64)", ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _svarptr(self, fr, dest, conv, name, ln):
        # `conv` (as_ptr/as_int) only differs in the IR interpreter; x64gen
        # emits the same dispatch for both (it never type-checks here).
        # as_ptr/as_int of a direct variable: raw names pass through;
        # dynamic-held names dispatch on the tagged word (Int unboxes,
        # heap passes as the address); anything else is unknown at
        # build, like x64gen's resolve failure.
        a = self.a
        if name in fr.get("rawnames", ()):
            a.mov_rm("rax", "rbp", fr["slots"][name])
        elif (fr["mod"], name) in self.global_raw:
            a.lea_rip("rax", self._glabel(name, fr["mod"]))
            a.mov_rm("rax", "rax", 0)
        elif name in fr["pmap"] or name in fr["locals"] or \
                name in fr.get("caps", ()) or \
                name in self.mod_globals.get(fr["mod"], set()):
            if name in fr["pmap"]:
                a.mov_rm("rax", "rbp", fr["pmap"][name])
            elif name in fr["locals"]:
                a.mov_rm("rax", "rbp", fr["slots"][name])
            elif name in fr.get("caps", ()):
                a.mov_rm("rax", "r15", 8 * fr["caps"].index(name))
            else:
                lab = self._glabel(name, fr["mod"])
                a.lea_rip("rax", lab)
                a.mov_rm("rax", "rax", 0)
            lab_heap, lab_bad, lab_done = (self.new_tmp("az"),
                                           self.new_tmp("az"),
                                           self.new_tmp("az"))
            a.mov_rr("r11", "rax")
            a.and_ri32("r11", 3)
            a.cmp_ri32("r11", Gen.TAG_INT)
            a.jcc("ne", lab_heap)
            a.sar_ri8("rax", 2)
            a.jmp(lab_done)
            a.label(lab_heap)
            a.test_rr("r11", "r11")
            a.jcc("ne", lab_bad)
            a.jmp(lab_done)
            a.label(lab_bad)
            self.type_err()
            a.label(lab_done)
        else:
            raise HSErr(f"unknown variable '{name}'", ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sderef(self, fr, dest, v, ln):
        a = self.a
        self._load(fr, v, ln)
        a.mov_rm("rax", "rax", 0)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sfield(self, fr, dest, obj, name, idx, ln):
        # mirror sev_field emission (null + bounds checked hosted).
        from interp import HS_STRUCTS
        a = self.a
        xs = self._struct_of(fr, obj)
        if xs is None or xs not in HS_STRUCTS:
            raise HSErr("struct type unknown (x64)", ln)
        f = HS_STRUCTS[xs]["fields"].get(name)
        if f is None:
            raise HSErr(f"struct '{xs}' has no field '{name}'", ln)
        ft, off, count = f
        self._load(fr, obj, ln)
        lab_nn = self.new_tmp("nn")
        a.test_rr("rax", "rax")
        a.jcc("ne", lab_nn)
        self.raise_static("null pointer dereference", ln)
        a.label(lab_nn)
        if count > 1:
            if idx is None:
                raise HSErr(f"array field '{name}' needs an index", ln)
            a.push_r("rax")
            self._load(fr, idx, ln)
            a.mov_rr("rcx", "rax")
            a.pop_r("rax")
            a.cmp_ri32("rcx", count)
            lab_ok = self.new_tmp("bd")
            a.jcc("b", lab_ok)
            self.raise_struct_oob(name, count, ln)
            a.label(lab_ok)
            a.mov_rmx("rax", "rax", "rcx", 8, off)
        else:
            if idx is not None:
                raise HSErr(f"field '{name}' is not an array", ln)
            a.mov_rm("rax", "rax", off)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sbox(self, fr, dest, src, ln):
        # static word -> dynamic Int, blind tag (print_unsafe philosophy;
        # out-of-range U64/Ptr box is an accepted micro-divergence).
        a = self.a
        self._load(fr, src, ln)
        self.tag_box()
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _sraw(self, fr, dest, src, ln):
        a = self.a
        self._load(fr, src, ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _print(self, fr, args, ln):
        a = self.a
        for i, t in enumerate(args):
            if i > 0:
                a.lea_rip("rdi", "sp_")
                a.mov_ri32("rsi", 1)
                self.rt_out()
            r = self._modref(fr, t)
            if r is not None and r[0] == "mod":
                self._print_str(f"<module {r[1]['name']}>")
                continue
            if r is not None:
                _m, mattr = r[1], r[2]
                rr = self._mod_attr(_m, mattr, ln)
                if rr[0] == "lab":
                    a.lea_rip("rax", rr[1])
                    a.mov_rm("rax", "rax", 0)
                    a.mov_rr("rdi", "rax")
                    a.call("print_val")
                    continue
                self._print_str(f"<module {rr[1]['name']}>")
                continue
            d = fr["definstr"].get(t)
            if d is not None and d["op"] == "sstr":
                # unsafe str literal: printed directly (ex_unsafe parity)
                b = d["val"].encode()
                lab = self.rstr(d["val"])
                a.lea_rip("rdi", lab)
                a.mov_ri32("rsi", len(b))
                self.rt_out()
                continue
            if d is not None and d["op"] == "box":
                # unsafe static: raw word via print_int (ex_unsafe parity)
                self._load(fr, d["src"], ln)
                a.push_r("rax")
                a.call("print_int")
                a.add_ri32("rsp", 8)
                continue
            self._load(fr, t, ln)
            a.mov_rr("rdi", "rax")
            a.call("print_val")
        a.lea_rip("rdi", "nl_")
        a.mov_ri32("rsi", 1)
        self.rt_out()

    def _print_str(self, s):
        b = s.encode()
        lab = self.rstr(s)
        self.a.lea_rip("rdi", lab)
        self.a.mov_ri32("rsi", len(b))
        self.rt_out()

    def _build_list(self, fr, dest, items, ln):
        a = self.a
        for it in items:
            self._load(fr, it, ln)
            a.push_r("rax")
        a.mov_ri32("rdi", len(items))
        a.call("x_list_new")
        if items:
            a.mov_rm("rdx", "rax", 24)  # buf
            for i in reversed(range(len(items))):
                a.pop_r("rcx")
                a.mov_mr("rdx", "rcx", 8 * i)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _build_dict(self, fr, dest, pairs, ln):
        a = self.a
        n = len(pairs)
        for k, v in pairs:  # source order: key, value, ...
            self._load(fr, k, ln)
            a.push_r("rax")
            self._load(fr, v, ln)
            a.push_r("rax")
        a.mov_ri32("rdi", n)
        a.call("x_dict_new")
        a.push_r("rax")
        for i in range(n):
            a.mov_rm("rdx", "rsp", 16 * (n - i) - 8)  # value
            a.mov_rm("rsi", "rsp", 16 * (n - i))  # key
            a.mov_rm("rdi", "rsp", 0)
            a.call("x_dict_set")
        a.mov_rm("rax", "rsp", 0)
        a.add_ri32("rsp", 8 * (2 * n + 1))
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _index(self, fr, dest, obj, idx, ln):
        # transliterated Gen.ev_index: obj in rax, idx (tagged) in rcx
        a = self.a
        self._load(fr, obj, ln)
        a.push_r("rax")
        self._load(fr, idx, ln)
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")
        lab_notdict = self.new_tmp("ix")
        lab_dkey, lab_dget = self.new_tmp("ix"), self.new_tmp("ix")
        lab_ix_done = self.new_tmp("ix")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_notdict)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_DICT)
        a.jcc("ne", lab_notdict)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)   # Int keys are fine
        a.jcc("e", lab_dget)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_dkey)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_dget)
        a.label(lab_dkey)
        self.raise_static("dict key must be Str or Int", ln)
        a.label(lab_dget)
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rcx")
        a.mov_ri32("rdx", ln)
        a.call("x_dict_get")
        a.jmp(lab_ix_done)
        a.label(lab_notdict)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        lab_ok = self.new_tmp("ix")
        a.jcc("e", lab_ok)
        self.raise_static("index must be Int", ln)
        a.label(lab_ok)
        a.sar_ri8("rcx", 2)
        lab_heap, lab_bad = self.new_tmp("ix"), self.new_tmp("ix")
        lab_str, lab_list = self.new_tmp("ix"), self.new_tmp("ix")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_str)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_list)
        a.label(lab_bad)
        self.raise_unop(1, ln)
        a.label(lab_str)
        a.mov_rm("r11", "rax", 8)
        a.cmp_ri32("rcx", 0)
        lab_pos = self.new_tmp("ix")
        a.jcc("ge", lab_pos)
        a.add_rr("rcx", "r11")
        a.label(lab_pos)
        a.cmp_ri32("rcx", 0)
        a.jcc("l", lab_heap)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_heap)
        a.lea_m("rdi", "rax", 16, "rcx", 1)
        a.mov_ri32("rsi", 1)
        a.call("x_str_at")
        lab_done = self.new_tmp("ix")
        a.jmp(lab_done)
        a.label(lab_list)
        a.mov_rm("r11", "rax", 8)
        a.cmp_ri32("rcx", 0)
        lab_pos2 = self.new_tmp("ix")
        a.jcc("ge", lab_pos2)
        a.add_rr("rcx", "r11")
        a.label(lab_pos2)
        a.cmp_ri32("rcx", 0)
        a.jcc("l", lab_heap)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_heap)
        a.mov_rm("rdx", "rax", 24)
        a.mov_rmx("rax", "rdx", "rcx", 8, 0)
        a.jmp(lab_done)
        a.label(lab_heap)
        self.raise_static("index out of range", ln)
        a.label(lab_done)
        a.label(lab_ix_done)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _slice(self, fr, dest, obj, start, stop, ln):
        # transliterated Gen.ev_slice: raw bounds -> x_slice
        a = self.a
        self._load(fr, obj, ln)
        a.push_r("rax")
        mask = 0
        if start is not None:
            self._load(fr, start, ln)
            self.check_int(lambda: self.raise_static(
                "slice index must be Int", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            mask |= 1
        else:
            a.mov_ri32("rax", 0)
            a.push_r("rax")
        if stop is not None:
            self._load(fr, stop, ln)
            self.check_int(lambda: self.raise_static(
                "slice index must be Int", ln))
            a.sar_ri8("rax", 2)
            a.push_r("rax")
            mask |= 2
        else:
            a.mov_ri32("rax", 0)
            a.push_r("rax")
        a.pop_r("rdx")
        a.pop_r("rsi")
        a.pop_r("rdi")
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
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _setindex(self, fr, obj, idx, val, ln):
        # transliterated Gen.ex_setindex
        a = self.a
        self._load(fr, obj, ln)
        a.push_r("rax")
        self._load(fr, idx, ln)
        a.push_r("rax")
        self._load(fr, val, ln)
        a.mov_rr("rdx", "rax")
        a.pop_r("rcx")
        a.pop_r("rax")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        lab_snotdict = self.new_tmp("sx")
        lab_sdkey, lab_sdset = self.new_tmp("sx"), self.new_tmp("sx")
        lab_sx_done = self.new_tmp("sx")
        a.jcc("ne", lab_snotdict)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_DICT)
        a.jcc("ne", lab_snotdict)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)   # Int keys are fine
        a.jcc("e", lab_sdset)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_sdkey)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_sdset)
        a.label(lab_sdkey)
        self.raise_static("dict key must be Str or Int", ln)
        a.label(lab_sdset)
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rcx")
        a.call("x_dict_set")
        a.jmp(lab_sx_done)
        a.label(lab_snotdict)
        a.mov_rr("r11", "rcx")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        lab_ok = self.new_tmp("sx")
        a.jcc("e", lab_ok)
        self.raise_static("index must be Int", ln)
        a.label(lab_ok)
        a.sar_ri8("rcx", 2)
        lab_bad, lab_list = self.new_tmp("sx"), self.new_tmp("sx")
        lab_pos, lab_oob, lab_done = (self.new_tmp("sx"), self.new_tmp("sx"),
                                      self.new_tmp("sx"))
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_list)
        a.label(lab_bad)
        self.raise_unop(2, ln)
        a.label(lab_list)
        a.mov_rm("r11", "rax", 8)
        a.cmp_ri32("rcx", 0)
        a.jcc("ge", lab_pos)
        a.add_rr("rcx", "r11")
        a.label(lab_pos)
        a.cmp_ri32("rcx", 0)
        a.jcc("l", lab_oob)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_oob)
        a.mov_rm("r11", "rax", 24)
        a.mov_mrx("r11", "rcx", 8, 0, "rdx")
        a.jmp(lab_done)
        a.label(lab_oob)
        self.raise_static("index out of range", ln)
        a.label(lab_done)
        a.label(lab_sx_done)

    def _iterseq(self, fr, dest, src, ln):
        # like the IR interpreter: dict -> fresh key list, List/Str pass
        # through (shared, like interp's `seq = it`), else "not iterable".
        a = self.a
        self._load(fr, src, ln)
        lab_list, lab_str, lab_dict, lab_done = (self.new_tmp("iq"),
                                                 self.new_tmp("iq"),
                                                 self.new_tmp("iq"),
                                                 self.new_tmp("iq"))
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        lab_bad = self.new_tmp("iq")
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_LIST)
        a.jcc("e", lab_list)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_str)
        a.cmp_ri32("r11", Gen.K_DICT)
        a.jcc("e", lab_dict)
        a.label(lab_bad)
        self.raise_unop(5, ln)
        a.label(lab_list)
        a.label(lab_str)
        a.jmp(lab_done)
        a.label(lab_dict)
        # dict buf holds [k0, v0, k1, v1, ...]: copy the even words into
        # a fresh list. No calls inside the loop, so caller-saved regs
        # survive across iterations.
        a.push_r("rax")  # dict
        a.mov_rm("rdi", "rax", 8)  # pair count
        a.call("x_list_new")  # rax = keys list
        a.mov_rr("rsi", "rax")  # rsi = keys list
        a.pop_r("rax")  # rax = dict
        a.mov_rm("r11", "rax", 8)  # r11 = pair count
        a.mov_rm("rdi", "rax", 24)  # rdi = dict buf
        a.mov_rm("rdx", "rsi", 24)  # rdx = list buf
        a.test_rr("r11", "r11")
        lab_kdone = self.new_tmp("iq")
        a.jcc("e", lab_kdone)
        a.mov_ri32("rcx", 0)  # i
        lab_kloop = self.new_tmp("iq")
        a.label(lab_kloop)
        a.mov_rr("r8", "rcx")
        a.shl_ri8("r8", 1)  # 2i
        a.mov_rmx("r8", "rdi", "r8", 8, 0)  # dictbuf[2i]
        a.mov_mrx("rdx", "rcx", 8, 0, "r8")  # listbuf[i]
        a.add_ri32("rcx", 1)
        a.cmp_rr("rcx", "r11")
        a.jcc("l", lab_kloop)
        a.label(lab_kdone)
        a.mov_rr("rax", "rsi")
        a.label(lab_done)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _call(self, fr, dest, fn, args, ln):
        # Direct calls of inline builtins use the inline emitter (exact
        # error lines, like ev_call); first-class uses go through the
        # value/stub protocol (whose type errors carry line 0, also like
        # x64gen-today). `float` has no value form at all.
        p = fr["prov"].get(fn)
        pname = p[1] if p is not None and p[0] == "load" else None
        if pname in GenIR.JSON_CALLS and fr["res"].get(pname) == "novalue":
            self._json_call(fr, dest, pname, args, ln)
            return
        if pname == "type_name" and fr.get("mod") == "<json>" and \
                fr["res"].get(pname) in ("novalue", "auto"):
            # private hook for runtime/json.hs only: x_tname. User
            # code never sees it (resolves unknown at runtime).
            if len(args) != 1:
                raise HSErr("type_name wants type_name(x)", ln)
            self._load(fr, args[0], ln)
            a = self.a
            a.mov_rr("rdi", "rax")
            a.call("x_tname")
            a.mov_mr("rbp", "rax", fr["slots"][dest])
            return
        if fn in fr["floattemps"]:
            name = pname
            if name == "float":
                self._inline_float(fr, dest, args, ln)
            elif name in ("len", "str"):
                self._inline_len_str(fr, dest, name, args, ln)
            elif name == "int":
                self._inline_int(fr, dest, args, ln)
            elif name == "range":
                self._inline_range(fr, dest, args, ln)
            elif name == "append":
                self._inline_append(fr, dest, args, ln)
            elif name in ("read_text", "write_text", "append_text",
                          "exists", "ls", "mkdir"):
                self._inline_file(fr, dest, name, args, ln)
            elif name == "read_mem":
                self._inline_read_mem(fr, dest, args, ln)
            elif name == "has":
                self._inline_has(fr, dest, args, ln)
            elif name == "contains":
                if len(args) != 2:
                    raise HSErr("contains wants contains(container, x)", ln)
                self._load(fr, args[0], ln)
                self.a.push_r("rax")
                self._load(fr, args[1], ln)
                self.a.mov_rr("rsi", "rax")
                self.a.pop_r("rdi")
                self.a.mov_ri32("rdx", ln)
                self.a.call("x_contains")
                self.a.mov_mr("rbp", "rax", fr["slots"][dest])
            else:
                raise HSErr(f"IR: '{name}' not in irx64 subset yet", ln)
            return
        # otherwise one path for user funcs and builtin values
        # (transliterated Gen.ev_user_call; nparams == -1 lets bi_call
        # check arity itself).
        a = self.a
        self._load(fr, fn, ln)  # rax = func struct ptr
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
        nargs = len(args)
        a.mov_rm("r11", "rax", 16)
        a.cmp_ri32("r11", -1)
        lab_aok = self.new_tmp("ar")
        a.jcc("e", lab_aok)
        a.cmp_ri32("r11", nargs)
        lab_aok2 = self.new_tmp("ar")
        a.jcc("e", lab_aok2)
        a.mov_ri32("r11", nargs)
        a.mov_ri32("rsi", ln)
        a.jmp("arity_fail")
        a.label(lab_aok2)
        a.label(lab_aok)
        a.push_r("rax")
        for ar in reversed(args):
            self._load(fr, ar, ln)
            a.push_r("rax")
        a.mov_rm("rax", "rsp", 8 * nargs)
        a.push_r("r15")
        a.mov_rr("r15", "rax")
        a.add_ri32("r15", 32)
        a.mov_rm("rax", "rax", 8)
        a.mov_ri32("rdi", nargs)
        a.mov_ri32("rsi", ln)
        a.call_rax()
        a.pop_r("r15")
        a.add_ri32("rsp", 8 * (nargs + 1))
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_float(self, fr, dest, args, ln):
        # transliterated ev_call float arm (inline-only builtin: Int/Bool
        # -> bits; Float passes; Str parses; else tname error).
        a = self.a
        if len(args) != 1:
            raise HSErr("float wants 1 arg", ln)
        self._load(fr, args[0], ln)
        lab_fok, lab_fnum = self.new_tmp("fl"), self.new_tmp("fl")
        lab_fflt, lab_fstr = self.new_tmp("fl"), self.new_tmp("fl")
        lab_fbool, lab_fquote = self.new_tmp("fl"), self.new_tmp("fl")
        lab_fint = self.new_tmp("fl")
        a.push_r("rax")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("e", lab_fint)
        a.cmp_ri32("r11", Gen.TAG_BOOL)
        a.jcc("e", lab_fbool)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_fnum)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_FLOAT)
        a.jcc("e", lab_fflt)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_fstr)
        a.label(lab_fnum)
        a.add_ri32("rsp", 8)
        a.mov_rr("rdi", "rax")
        a.call("x_tname")
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr("cannot convert "))
        a.mov_ri32("rsi", 15)
        a.call("x_str_at")
        a.mov_rr("rdi", "rax")
        a.pop_r("rsi")
        a.call("x_str_cat")
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr("cannot convert '"))
        a.mov_ri32("rsi", 16)
        a.call("x_str_at")
        a.mov_rr("rdi", "rax")
        a.pop_r("rsi")
        a.call("x_str_cat")
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr("' to Float"))
        a.mov_ri32("rsi", 10)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rsi", ln)
        a.jmp("hs_raise_msg")
        a.label(lab_fint)
        a.sar_ri8("rax", 2)
        a.cvtsi2sd(0, "rax")
        a.movq_rx("rdi", 0)
        a.call("x_float_new")
        a.add_ri32("rsp", 8)
        a.jmp(lab_fok)
        a.label(lab_fbool)
        a.cmp_ri32("rax", Gen.HS_TRUE)
        a.setcc_al("e")
        a.movzx_eax_al()
        a.cvtsi2sd(0, "rax")
        a.movq_rx("rdi", 0)
        a.call("x_float_new")
        a.add_ri32("rsp", 8)
        a.jmp(lab_fok)
        a.label(lab_fflt)
        a.add_ri32("rsp", 8)
        a.jmp(lab_fok)
        a.label(lab_fstr)
        a.mov_rr("rdi", "rax")
        a.call("x_trim")
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rdx")
        a.call("x_parse_f64")
        a.test_rr("rdx", "rdx")
        a.jcc("e", lab_fquote)
        a.mov_rr("rdi", "rax")
        a.call("x_float_new")
        a.add_ri32("rsp", 8)
        a.jmp(lab_fok)
        a.label(lab_fquote)
        a.mov_rm("rdi", "rsp", 0)
        a.push_r("rdi")
        a.lea_rip("rdi", self.rstr("cannot convert '"))
        a.mov_ri32("rsi", 16)
        a.call("x_str_at")
        a.mov_rr("rdi", "rax")
        a.pop_r("rsi")
        a.call("x_str_cat")
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr("' to Float"))
        a.mov_ri32("rsi", 10)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rsi", ln)
        a.jmp("hs_raise_msg")
        a.label(lab_fok)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_len_str(self, fr, dest, name, args, ln):
        a = self.a
        if len(args) != 1:
            raise HSErr(f"{name} wants 1 arg", ln)
        self._load(fr, args[0], ln)
        if name == "len":
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
            a.cmp_ri32("r11", Gen.K_DICT)
            a.jcc("e", lab_lok)
            a.label(lab_lck)
            self.raise_unop(0, ln)
            a.label(lab_lok)
        a.mov_rr("rdi", "rax")
        a.call("x_str" if name == "str" else "x_len")
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_int(self, fr, dest, args, ln):
        a = self.a
        if len(args) != 1:
            raise HSErr("int wants 1 arg", ln)
        self._load(fr, args[0], ln)
        lab_iok, lab_inum = self.new_tmp("in"), self.new_tmp("in")
        lab_iflt, lab_istr = self.new_tmp("in"), self.new_tmp("in")
        lab_ibool, lab_iquote = self.new_tmp("in"), self.new_tmp("in")
        lab_iint = self.new_tmp("in")
        a.push_r("rax")
        a.mov_rr("r11", "rax")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("e", lab_iint)
        a.cmp_ri32("r11", Gen.TAG_BOOL)
        a.jcc("e", lab_ibool)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_inum)
        a.mov_rm("r11", "rax", 0)
        a.cmp_ri32("r11", Gen.K_FLOAT)
        a.jcc("e", lab_iflt)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_istr)
        a.label(lab_inum)
        a.add_ri32("rsp", 8)
        self.raise_unop(4, ln)
        a.label(lab_ibool)
        a.cmp_ri32("rax", Gen.HS_TRUE)
        a.setcc_al("e")
        a.movzx_eax_al()
        a.shl_ri8("rax", 2)
        a.or_ri8("rax", 1)
        a.add_ri32("rsp", 8)
        a.jmp(lab_iok)
        a.label(lab_iflt)
        a.movq_xm(0, "rax", 8)
        a.cvttsd2si("rax", 0)
        a.mov_rr("rcx", "rax")
        a.mov_ri64("r11", 0x2000000000000000)
        a.add_rr("rcx", "r11")
        a.mov_ri64("r11", 0x4000000000000000)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_inum)
        self.tag_box()
        a.add_ri32("rsp", 8)
        a.jmp(lab_iok)
        a.label(lab_istr)
        a.mov_rr("rdi", "rax")
        a.call("x_trim")
        a.mov_rr("rdi", "rax")
        a.mov_rr("rsi", "rdx")
        a.call("x_int_parse")
        a.test_rr("rdx", "rdx")
        a.jcc("e", lab_iquote)
        a.mov_rr("rcx", "rax")
        a.mov_ri64("r11", 0x2000000000000000)
        a.add_rr("rcx", "r11")
        a.mov_ri64("r11", 0x4000000000000000)
        a.cmp_rr("rcx", "r11")
        a.jcc("ae", lab_iquote)
        self.tag_box()
        a.add_ri32("rsp", 8)
        a.jmp(lab_iok)
        a.label(lab_iquote)
        a.lea_rip("rdi", self.rstr("cannot convert '"))
        a.mov_ri32("rsi", 16)
        a.call("x_str_at")
        a.mov_rr("rdi", "rax")
        a.mov_rm("rsi", "rsp", 0)
        a.call("x_str_cat")
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr("' to Int"))
        a.mov_ri32("rsi", 8)
        a.call("x_str_at")
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_str_cat")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rsi", ln)
        a.jmp("hs_raise_msg")
        a.label(lab_iint)
        a.add_ri32("rsp", 8)
        a.jmp(lab_iok)
        a.label(lab_iok)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_range(self, fr, dest, args, ln):
        a = self.a
        if len(args) == 1:
            self._load(fr, args[0], ln)
            self.check_int(lambda: self.raise_static(
                "range wants range(n) or range(a, b) with Ints", ln))
            a.mov_rr("rdi", "rax")
            a.call("x_range1")
        elif len(args) == 2:
            self._load(fr, args[0], ln)
            self.check_int(lambda: self.raise_static(
                "range wants range(n) or range(a, b) with Ints", ln))
            a.push_r("rax")
            self._load(fr, args[1], ln)
            self.check_int(lambda: self.raise_static(
                "range wants range(n) or range(a, b) with Ints", ln))
            a.mov_rr("rsi", "rax")
            a.pop_r("rdi")
            a.call("x_range2")
        else:
            raise HSErr("range wants range(n) or range(a, b)", ln)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_append(self, fr, dest, args, ln):
        a = self.a
        if len(args) != 2:
            raise HSErr("append wants append(list, x)", ln)
        self._load(fr, args[0], ln)
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
        self._load(fr, args[1], ln)
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        a.call("x_append")
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_has(self, fr, dest, args, ln):
        a = self.a
        if len(args) != 2:
            raise HSErr("has wants has(dict, key)", ln)
        self._load(fr, args[0], ln)
        a.push_r("rax")
        self._load(fr, args[1], ln)
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        lab_bad, lab_k, lab_ok = (self.new_tmp("hs"), self.new_tmp("hs"),
                                  self.new_tmp("hs"))
        a.mov_rr("r11", "rdi")
        a.and_ri32("r11", 3)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_bad)
        a.mov_rm("r11", "rdi", 0)
        a.cmp_ri32("r11", Gen.K_DICT)
        a.jcc("ne", lab_bad)
        a.mov_rr("r11", "rsi")
        a.and_ri32("r11", 3)
        a.cmp_ri32("r11", Gen.TAG_INT)
        a.jcc("e", lab_ok)
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_k)
        a.mov_rm("r11", "rsi", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_ok)
        a.label(lab_k)
        self.raise_static("dict key must be Str or Int", ln)
        a.label(lab_bad)
        self.raise_static("has wants has(dict, key)", ln)
        a.label(lab_ok)
        a.call("x_dict_find")
        lab_f, lab_d = self.new_tmp("hs"), self.new_tmp("hs")
        a.test_rr("rax", "rax")
        a.jcc("s", lab_f)
        a.mov_ri64("rax", Gen.HS_TRUE)
        a.jmp(lab_d)
        a.label(lab_f)
        a.mov_ri64("rax", Gen.HS_FALSE)
        a.label(lab_d)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_file(self, fr, dest, name, args, ln):
        # transliterated ev_call whole-file-helper arm (hosted only;
        # irx64 never builds freestanding, so no subset gate needed).
        a = self.a
        want = {"read_text": (1, "read_text wants read_text(path)"),
                "write_text": (2, "write_text wants write_text(path, str)"),
                "append_text": (2,
                                "append_text wants append_text(path, str)"),
                "exists": (1, "exists wants exists(path)"),
                "ls": (1, "ls wants ls(dir)"),
                "mkdir": (1, "mkdir wants mkdir(path)")}[name]
        n_want, msg = want
        lab_fsbad, lab_fsret = self.new_tmp("fs"), self.new_tmp("fs")
        if len(args) != n_want:
            raise HSErr(msg, ln)
        for ar in args:
            self._load(fr, ar, ln)
            a.push_r("rax")
        for _ in range(len(args)):
            a.pop_r("rcx")
            a.test_rr("rcx", "rcx")
            a.jcc("e", lab_fsbad)
            a.mov_rm("rax", "rcx", 0)
            a.cmp_ri32("rax", Gen.K_STR)
            a.jcc("ne", lab_fsbad)
            a.push_r("rcx")
        if name == "read_text":
            a.pop_r("rdi")
            a.mov_ri32("rsi", 0)
            a.mov_ri32("rdx", ln)
            a.call("file_open")
            a.push_r("rax")
            a.mov_rr("rdi", "rax")
            a.mov_ri32("rdx", ln)
            a.call("file_read_all")
            a.push_r("rax")
            a.mov_rm("rdi", "rsp", 8)
            a.call("file_close")
            a.pop_r("rax")
            a.add_ri32("rsp", 8)
            a.jmp(lab_fsret)
        if name in ("write_text", "append_text"):
            a.pop_r("rsi")
            a.pop_r("rdi")
            a.push_r("rdi")
            a.push_r("rsi")
            a.mov_ri32("rsi", 1 if name == "write_text" else 2)
            a.mov_ri32("rdx", ln)
            a.call("file_open")
            a.push_r("rax")
            a.mov_ri32("rdx", ln)
            a.mov_rm("rsi", "rsp", 8)
            a.mov_rm("rdi", "rsp", 0)
            a.call("file_write_all")
            a.mov_rm("rdi", "rsp", 0)
            a.add_ri32("rsp", 24)
            a.call("file_close")
            a.jmp(lab_fsret)
        a.pop_r("rdi")
        a.mov_ri32("rsi", ln)
        if name == "exists":
            a.call("fs_exists")
            a.jmp(lab_fsret)
        if name == "mkdir":
            a.call("fs_mkdirs")
            a.jmp(lab_fsret)
        a.call("fs_ls")
        a.jmp(lab_fsret)
        a.label(lab_fsbad)
        self.raise_static(msg, ln)
        a.label(lab_fsret)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _inline_read_mem(self, fr, dest, args, ln):
        a = self.a
        if len(args) != 2:
            raise HSErr("read_mem wants read_mem(ptr, nbytes)", ln)
        self._load(fr, args[0], ln)
        self.check_int(lambda: self.raise_static(
            "read_mem wants read_mem(ptr, nbytes)", ln))
        a.sar_ri8("rax", 2)
        a.push_r("rax")
        self._load(fr, args[1], ln)
        self.check_int(lambda: self.raise_static(
            "read_mem wants read_mem(ptr, nbytes)", ln))
        a.sar_ri8("rax", 2)
        a.mov_rr("rsi", "rax")
        a.pop_r("rdi")
        lab_rmok = self.new_tmp("rm")
        a.test_rr("rsi", "rsi")
        a.jcc("ns", lab_rmok)
        self.raise_static("read_mem length must be >= 0", ln)
        a.label(lab_rmok)
        a.call("x_str_at")
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _js_entry(self, name, ln):
        key = self.js_entries.get(name)
        if key is None:
            raise HSErr("IR: json entry missing", ln)
        return self.flabel[key]

    def _js_finish(self, dest, ln, fr, parse=False):
        # rax = [err_or_null, payload]: payload to dest, else raise at ln
        # (transliterated Gen.js_finish verbatim).
        a = self.a
        lab_ok = self.new_tmp("js")
        a.mov_rm("r11", "rax", 24)
        a.mov_rm("r10", "r11", 0)
        a.cmp_ri32("r10", Gen.HS_NULL)
        a.jcc("e", lab_ok)
        a.mov_rr("rcx", "r10")
        if parse:
            pre = "json_parse failed: "
            a.push_r("rcx")
            a.lea_rip("rdi", self.rstr(pre))
            a.mov_ri32("rsi", len(pre))
            a.call("x_str_at")
            a.pop_r("rsi")
            a.mov_rr("rdi", "rax")
            a.call("x_str_cat")
            a.mov_rr("rdi", "rax")
        else:
            a.mov_rr("rdi", "rcx")
        a.mov_ri32("rsi", ln)
        a.jmp("hs_raise_msg")
        a.label(lab_ok)
        a.mov_rm("rax", "r11", 8)
        a.mov_mr("rbp", "rax", fr["slots"][dest])

    def _json_call(self, fr, dest, name, args, ln):
        # transliterated Gen.ev_json over temps (same checks, messages,
        # lines; entries are normal merged IR funcs reached through the
        # shared call_js_entry convention).
        a = self.a
        want = {"json_parse": (1, "json_parse wants json_parse(str)"),
                "json_str": (1, "json_str wants json_str(x)"),
                "json_load": (1, "json_load wants json_load(path)"),
                "json_save": (2, "json_save wants json_save(path, x)")}[name]
        if len(args) != want[0]:
            raise HSErr(want[1], ln)
        a.call(self._init_label(self.modtab["<json>"]))
        lab_ok = self.new_tmp("js")
        lab_bad = self.new_tmp("js")
        lab_go = self.new_tmp("js")
        for ar in args:
            self._load(fr, ar, ln)
            a.push_r("rax")
        if name in ("json_parse", "json_load", "json_save"):
            for i in range(len(args)):
                if name == "json_save" and i == 1:
                    continue
                off = 8 * (len(args) - 1 - i)
                a.mov_rm("r11", "rsp", off)
                a.and_ri32("r11", 3)
                a.jcc("ne", lab_bad)
                a.mov_rm("r11", "rsp", off)
                a.mov_rm("r11", "r11", 0)
                a.cmp_ri32("r11", Gen.K_STR)
                a.jcc("ne", lab_bad)
            a.jmp(lab_go)
            a.label(lab_bad)
            self.raise_static(want[1], ln)
            a.label(lab_go)
        if name == "json_save":
            a.pop_r("rax")
            self.call_js_entry(self._js_entry("js_encode", ln))
            self._js_finish(dest, ln, fr)
            a.push_r("rax")
            a.mov_rm("rdi", "rsp", 8)
            a.mov_ri32("rsi", 1)
            a.mov_ri32("rdx", ln)
            a.call("file_open")
            a.push_r("rax")
            a.mov_ri32("rdx", ln)
            a.mov_rm("rsi", "rsp", 8)
            a.mov_rm("rdi", "rsp", 0)
            a.call("file_write_all")
            a.mov_rm("rdi", "rsp", 0)
            a.add_ri32("rsp", 24)
            a.call("file_close")
            a.mov_ri64("rax", Gen.HS_NULL)
            a.mov_mr("rbp", "rax", fr["slots"][dest])
            return
        if name == "json_load":
            a.mov_rm("rdi", "rsp", 0)
            a.mov_ri32("rsi", 0)
            a.mov_ri32("rdx", ln)
            a.call("file_open")
            a.push_r("rax")
            a.mov_rr("rdi", "rax")
            a.mov_ri32("rdx", ln)
            a.call("file_read_all")
            a.push_r("rax")
            a.mov_rm("rdi", "rsp", 8)      # the File (one slot up)
            a.call("file_close")
            # stack: content, File, path. Pop the content FIRST; popping
            # after dropping a slot handed js_decode the closed File.
            a.pop_r("rax")
            a.add_ri32("rsp", 16)
            self.call_js_entry(self._js_entry("js_decode", ln))
            self._js_finish(dest, ln, fr, parse=True)
            return
        a.pop_r("rax")
        if name == "json_parse":
            self.call_js_entry(self._js_entry("js_decode", ln))
            self._js_finish(dest, ln, fr, parse=True)
            return
        self.call_js_entry(self._js_entry("js_encode", ln))
        self._js_finish(dest, ln, fr)
        return

    def _ffi_sym(self, name):
        if name not in self.ffi_syms:
            self.ffi_syms.append(name)
        return self.ffi_syms.index(name)

    def _ffi_lib(self, lib, ln):
        import ctypes.util as _cu
        if lib is None:
            so = "libc.so.6"
        elif lib.endswith(".c"):
            raise HSErr(f"extern from '{lib}': a C source needs a C compiler; "
                        "xbuild calls none (pass a prebuilt .so)", ln)
        elif "/" in lib or lib.endswith(".so") or ".so." in lib:
            so = lib
        else:
            so = _cu.find_library(lib)
            if so is None:
                raise HSErr(f"cannot find ffi library '{lib}'", ln)
        if so not in self.ffi_libs:
            self.ffi_libs.append(so)

    def _ffi(self, fr, ins, ln):
        """extern call: tagged hs values -> C ABI (rdi rsi rdx rcx r8 r9),
        call through the GOT slot ld.so fills, convert rax back, then
        fflush(NULL) so C stdio and hs output stay in program order."""
        a = self.a
        name, pt, rt = ins["sym"], ins["ptypes"], ins["rtype"]
        nf = pt.count("F64")
        if nf > 8:
            raise HSErr(f"ffi '{name}': xbuild passes at most 8 F64 args", ln)
        if len(pt) > 6:
            raise HSErr(f"ffi '{name}': xbuild passes at most 6 args", ln)
        self._ffi_lib(ins["lib"], ln)
        gi = self._ffi_sym(name)
        fl = self._ffi_sym("fflush")
        for i, (pn, ft) in enumerate(zip(ins["pnames"], pt)):
            self._load(fr, pn, ln)
            msg = f"ffi '{name}' arg {i + 1} wants {ft}, got "
            lab_bad = self.new_tmp("ff")
            lab_after = self.new_tmp("ff")
            if ft == "F64":
                lab_fi, lab_fok = self.new_tmp("ff"), self.new_tmp("ff")
                a.mov_rr("r11", "rax")
                a.and_ri32("r11", 3)
                a.cmp_ri32("r11", Gen.TAG_INT)
                a.jcc("e", lab_fi)
                a.test_rr("r11", "r11")
                a.jcc("ne", lab_bad)
                a.mov_rm("r11", "rax", 0)
                a.cmp_ri32("r11", Gen.K_FLOAT)
                a.jcc("ne", lab_bad)
                a.mov_rm("rax", "rax", 8)
                a.jmp(lab_fok)
                a.label(lab_fi)
                a.sar_ri8("rax", 2)
                a.cvtsi2sd(0, "rax")
                a.movq_rx("rax", 0)
                a.label(lab_fok)
                a.push_r("rax")
            elif ft == "Str":
                lab_ok = self.new_tmp("ff")
                a.mov_rr("r11", "rax")
                a.and_ri32("r11", 3)
                a.test_rr("r11", "r11")
                a.jcc("ne", lab_bad)
                a.mov_rm("r11", "rax", 0)
                a.cmp_ri32("r11", Gen.K_STR)
                a.jcc("e", lab_ok)
                a.jmp(lab_bad)
                a.label(lab_ok)
                a.push_r("rax")
                a.mov_rm("rdi", "rax", 8)
                a.add_ri32("rdi", 24)
                a.call("x_malloc")           # zeroed: NUL terminator for free
                a.pop_r("rsi")
                a.mov_rm("rcx", "rsi", 8)
                a.add_ri32("rsi", 16)
                a.mov_rr("rdi", "rax")
                a.push_r("rax")
                self.copy_bytes()
            else:
                self.check_int(lambda lb=lab_bad: a.jmp(lb))
                a.sar_ri8("rax", 2)
                a.push_r("rax")
            a.jmp(lab_after)
            # bad argument (rax = the value): "... wants T, got <type>"
            a.label(lab_bad)
            a.mov_rr("rdi", "rax")
            a.call("x_tname")
            a.push_r("rax")
            a.lea_rip("rdi", self.rstr(msg))
            a.mov_ri32("rsi", len(msg.encode()))
            a.call("x_str_at")
            a.mov_rr("rdi", "rax")
            a.pop_r("rsi")
            a.call("x_str_cat")
            a.mov_rr("rdi", "rax")
            a.mov_rm("rsi", "rbp", fr["slots"]["%cline"])
            a.jmp("hs_raise_msg")
            a.label(lab_after)
        iregs = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        ni = len(pt) - nf
        fi, ii = nf, ni
        for ft in reversed(pt):
            if ft == "F64":
                fi -= 1
                a.pop_r("rax")
                a.movq_xr(fi, "rax")
            else:
                ii -= 1
                a.pop_r(iregs[ii])

        def ccall(idx, nfl=nf):
            a.mov_rr("r10", "rsp")
            a.and_ri32("rsp", -16)
            a.sub_ri32("rsp", 16)
            a.mov_mr("rsp", "r10", 0)
            a.lea_rip("r11", "ffi_got_")
            a.mov_rm("r11", "r11", 8 * idx)
            a.mov_ri32("rax", nfl)       # varargs: number of vector regs
            a.call_r11()
            a.mov_rm("rsp", "rsp", 0)
        ccall(gi)
        if rt == "F64":
            a.movq_rx("rax", 0)
        a.push_r("rax")
        a.mov_ri32("rdi", 0)
        ccall(fl, 0)
        a.pop_r("rax")
        if rt == "F64":
            a.mov_rr("rdi", "rax")
            a.call("x_float_new")
        elif rt == "U0":
            a.mov_ri64("rax", Gen.HS_NULL)
        elif rt == "Str":
            lab_nn, lab_done = self.new_tmp("ff"), self.new_tmp("ff")
            lab_lt, lab_le = self.new_tmp("ff"), self.new_tmp("ff")
            a.test_rr("rax", "rax")
            a.jcc("ne", lab_nn)
            a.mov_ri64("rax", Gen.HS_NULL)
            a.jmp(lab_done)
            a.label(lab_nn)
            a.mov_rr("rdi", "rax")
            a.mov_ri32("rcx", 0)
            a.label(lab_lt)
            a.movzx_eax_mx("rdi", "rcx", 1, 0)
            a.test_rr("rax", "rax")
            a.jcc("e", lab_le)
            a.add_ri32("rcx", 1)
            a.jmp(lab_lt)
            a.label(lab_le)
            a.mov_rr("rsi", "rcx")
            a.call("x_str_at")
            a.label(lab_done)
        else:
            self.tag_box()
        a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])

    def _mkfunc(self, fr, dest, qname, ln):
        # transliterated Gen ex-def: captures evaluated in the defining
        # frame, Func = [kind][code][nparams][name][caps...].
        a = self.a
        child = self.allfuncs[qname]
        cfr = self.frames[qname]
        # A nested def that calls itself captures its own name. That slot
        # is still UNBOUND here (the stvar that binds the name comes after
        # this instruction), so the capture takes the object being built
        # instead of the frame -- the same value the name will hold.
        selfcap = cfr["caps"].index(child["dispname"]) \
            if child["dispname"] in cfr["caps"] else None
        for i, nm in enumerate(cfr["caps"]):
            if i == selfcap:
                continue
            self._load(fr, nm, ln)
            a.push_r("rax")
        n = len(cfr["caps"])
        a.mov_ri32("rdi", 8 * (4 + n))
        a.call("x_malloc")
        for i in reversed(range(n)):
            if i == selfcap:
                a.mov_mr("rax", "rax", 8 * (i + 4))
                continue
            a.pop_r("rcx")
            a.mov_mr("rax", "rcx", 8 * (i + 4))
        a.mov_ri32("rcx", Gen.K_FUNC)
        a.mov_mr("rax", "rcx", 0)
        a.lea_rip("rcx", self.flabel[qname])
        a.mov_mr("rax", "rcx", 8)
        a.mov_ri32("rcx", len(child["params"]))
        a.mov_mr("rax", "rcx", 16)
        a.push_r("rax")
        fname = child.get("xname", child["dispname"])
        a.lea_rip("rdi", self.rstr(fname))
        a.mov_ri32("rsi", len(fname.encode()))
        a.call("x_str_at")
        a.mov_rr("rcx", "rax")
        a.pop_r("rax")
        a.mov_mr("rax", "rcx", 24)
        a.mov_mr("rbp", "rax", fr["slots"][dest])
        # the name binding itself is a normal store done by the caller

    # ----- blocks and functions -----

    def _blabel(self, key, blab):
        return f"{self.flabel[key]}_{blab}"

    def _phi_moves(self, fr, from_lab, to_blk):
        for ins in to_blk["instrs"]:
            if ins["op"] != "phi":
                continue
            for al, at in ins["arms"]:
                if al == from_lab:
                    self._load(fr, at, ins["line"])
                    self.a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
                    break

    def _gc_point(self):
        # safe point: collect when the allocator asked for it. rax is
        # saved around the flag test (x_gc itself saves every register).
        a = self.a
        skip = self.new_tmp("gcp")
        a.push_r("rax")
        a.mov_rm_rip("rax", "gc_pend_")
        a.test_rr("rax", "rax")
        a.pop_r("rax")
        a.jcc("e", skip)
        a.call("x_gc")
        a.label(skip)

    def _gc_heads(self, by):
        # labels targeted by a backward (or self) jump: loop headers
        c = getattr(self, "_gc_head_cache", None)
        if c is None:
            c = self._gc_head_cache = {}
        k = id(by)
        if k not in c:
            order = {lab: i for i, lab in enumerate(by)}
            heads = set()
            for lab, b in by.items():
                tm = b["term"]
                outs = []
                if tm["term"] == "jmp":
                    outs = [tm["to"]]
                elif tm["term"] == "br":
                    outs = [tm["then"], tm["els"]]
                for t in outs:
                    if order[t] <= order[lab]:
                        heads.add(t)
            c[k] = (by, heads)  # keep `by` alive so id() stays unique
        return c[k][1]

    def _emit_block(self, fr, key, blk, by):
        a = self.a
        a.label(self._blabel(key, blk["label"]))
        if self._gc_heads(by).__contains__(blk["label"]):
            self._gc_point()
        for ins in blk["instrs"]:
            op = ins["op"]
            ln = ins["line"]
            if op == "const":
                self._const(ins["val"], ln)
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "load":
                if ins["dest"] in fr["floattemps"]:
                    a.mov_ri32("rax", 0)  # dummy: inline call ignores it
                    a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
                elif ins["dest"] in fr.get("deadloads", ()):
                    pass  # chain-only alias use: nothing to materialize
                elif self._alias_visible(fr, ins["name"]) is not None and \
                        fr["uses"].get(ins["dest"], []) and all(
                            u in {("attr", "obj"), ("print", "arg"),
                                  ("setattr", "obj"), ("stvar", "src"),
                                  ("stglobal", "src")} for u in
                            fr["uses"][ins["dest"]]):
                    pass  # copy-alias use: static only (aliases can be
                    # recorded mid-emission by an earlier copy)
                else:
                    self._load(fr, ins["name"], ln)
                    a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "stvar":
                r = self._modref(fr, ins["src"])
                sub = None
                if r is not None and r[0] == "mod":
                    sub = r[1]
                elif r is not None:
                    rr = self._mod_attr(r[1], r[2], ln)
                    if rr[0] == "sub":
                        sub = rr[1]
                if sub is not None:
                    # module alias copy: rebind, no code (x64gen parity);
                    # a later plain write drops it again below.
                    fr.setdefault("aliases", {})[ins["name"]] = sub
                    continue
                self._load(fr, ins["src"], ln)
                fr.get("aliases", {}).pop(ins["name"], None)
                self._store(fr, ins["name"], ln)
            elif op == "stglobal":
                self._load(fr, ins["src"], ln)
                fr.get("aliases", {}).pop(ins["name"], None)
                lab = self._glabel(ins["name"], fr["mod"])
                a.lea_rip("rcx", lab)
                a.mov_mr("rcx", "rax", 0)
            elif op == "ffi":
                self._ffi(fr, ins, ln)
            elif op == "mkfunc":
                self._mkfunc(fr, ins["dest"], ins["func"], ln)
            elif op == "bin":
                self._bin(fr, ins["binop"], ins["l"], ins["r"], ln)
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "un":
                self._un(fr, ins["unop"], ins["v"], ln)
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "call":
                self._call(fr, ins["dest"], ins["fn"], ins["args"], ln)
            elif op == "print":
                self._print(fr, ins["args"], ln)
            elif op == "try_push":
                a.call("hs_try_push0")
                a.test_rr("rax", "rax")
                a.jcc("ne", self._blabel(key, ins["handler"]))
            elif op == "try_pop":
                a.call("hs_try_pop")
            elif op == "exc_str":
                a.call("hs_exc_str")
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "exc_pop":
                a.call("hs_exc_pop")
            elif op == "unbind":
                # bound via stvar in the same function, so a slot exists;
                # at module level the binding lives in a data global.
                if ins["name"] in fr["slots"]:
                    a.mov_ri64("rax", Gen.HS_UNBOUND)
                    a.mov_mr("rbp", "rax", fr["slots"][ins["name"]])
                else:
                    lab = self._glabel(ins["name"], fr["mod"])
                    a.mov_ri64("rax", Gen.HS_UNBOUND)
                    a.lea_rip("rcx", lab)
                    a.mov_mr("rcx", "rax", 0)
            elif op == "reraise":
                a.call("hs_reraise")
            elif op == "import":
                for m in ins.get("_chain", []):
                    a.call(self._init_label(m))
            elif op == "attr":
                r = self._modref(fr, ins["obj"])
                basemod = None
                if r is not None and r[0] == "mod":
                    basemod = r[1]
                elif r is not None:
                    rr = self._mod_attr(r[1], r[2], ln)
                    if rr[0] != "sub":
                        raise HSErr("IR: attribute needs a direct m.attr "
                                    "chain", ln)
                    basemod = rr[1]
                if basemod is None:
                    raise HSErr("IR: attribute needs a direct m.attr "
                                "chain", ln)
                rr = self._mod_attr(basemod, ins["name"], ln)
                if rr[0] == "lab":
                    a.lea_rip("rax", rr[1])
                    a.mov_rm("rax", "rax", 0)
                    a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
                else:
                    # submodule: no runtime value (x64gen parity); the
                    # temp is a phantom — any value-use fails at build.
                    fr.setdefault("phantoms", {})[ins["dest"]] = \
                        rr[1]["name"]
            elif op == "setattr":
                r = self._modref(fr, ins["obj"])
                target = None
                if r is not None and r[0] == "mod":
                    target = r[1]
                elif r is not None:
                    rr = self._mod_attr(r[1], r[2], ln)
                    if rr[0] != "sub":
                        raise HSErr("IR: attribute assignment only "
                                    "supported on modules (x64)", ln)
                    target = rr[1]
                else:
                    raise HSErr("IR: attribute assignment only supported "
                                "on modules (x64)", ln)
                rr = self._mod_attr(target, ins["name"], ln)
                if rr[0] is None or rr[0] != "lab":
                    raise HSErr(f"module '{target['name']}' is not a "
                                "first-class value in x64 subset (use "
                                "mod.attr)", ln)
                self._load(fr, ins["val"], ln)
                a.push_r("rax")
                a.lea_rip("rcx", rr[1])
                a.pop_r("rax")
                a.mov_mr("rcx", "rax", 0)
            elif op == "build_list":
                self._build_list(fr, ins["dest"], ins["items"], ln)
            elif op == "build_dict":
                self._build_dict(fr, ins["dest"], ins["pairs"], ln)
            elif op == "index":
                self._index(fr, ins["dest"], ins["obj"], ins["idx"], ln)
            elif op == "slice":
                self._slice(fr, ins["dest"], ins["obj"], ins["start"],
                            ins["stop"], ln)
            elif op == "setindex":
                self._setindex(fr, ins["obj"], ins["idx"], ins["val"], ln)
            elif op == "iterseq":
                self._iterseq(fr, ins["dest"], ins["src"], ln)
            elif op == "phi":
                pass  # lowered as moves on incoming edges, not here
            elif op == "sconst":
                self._sconst(fr, ins["dest"], ins["stype"], ins["val"], ln)
            elif op == "sload":
                self._sload(fr, ins["dest"], ins["name"], ln)
            elif op == "sdecl":
                self._sdecl(fr, ins["name"], ins["src"], ln)
            elif op == "sset":
                self._sset(fr, ins["name"], ins["src"], ln)
            elif op == "sstore":
                self._sstore(fr, ins["ptr"], ins["val"], ln)
            elif op == "sfstore":
                self._sfstore(fr, ins["obj"], ins["name"], ins["idx"],
                              ins["val"], ln)
            elif op == "sbin":
                self._sbin(fr, ins["dest"], ins["binop"], ins["l"],
                           ins["r"], ln)
            elif op == "sun":
                self._sun(fr, ins["dest"], ins["unop"], ins["v"], ln)
            elif op == "scall":
                self._scall(fr, ins["dest"], ins["name"], ins["args"], ln)
            elif op == "svarptr":
                self._svarptr(fr, ins["dest"], ins["conv"], ins["var"], ln)
            elif op == "sderef":
                self._sderef(fr, ins["dest"], ins["v"], ln)
            elif op == "sfield":
                self._sfield(fr, ins["dest"], ins["obj"], ins["name"],
                             ins["idx"], ln)
            elif op == "box":
                self._sbox(fr, ins["dest"], ins["src"], ln)
            elif op == "sraw":
                self._sraw(fr, ins["dest"], ins["src"], ln)
            elif op == "sstr":
                raise HSErr("strings not allowed in unsafe (use unsafe: "
                            "outside)", ln)
            elif op == "serr":
                raise HSErr(ins["xmsg"], ln)
            elif op == "ssizeof":
                from interp import HS_STRUCTS
                st = ins["stype"]
                if st not in ("I64", "U64", "Ptr") and st not in HS_STRUCTS:
                    raise HSErr(f"unknown struct '{st}'", ln)
                a.mov_ri32("rax", 8 if st in ("I64", "U64", "Ptr")
                           else HS_STRUCTS[st]["size"])
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            else:
                raise HSErr(f"IR: '{op}' not in irx64 subset yet", ln)
        tm = blk["term"]
        ln = tm["line"]
        if tm["term"] == "jmp":
            self._phi_moves(fr, blk["label"], by[tm["to"]])
            a.jmp(self._blabel(key, tm["to"]))
        elif tm["term"] == "br":
            self._load(fr, tm["cond"], ln)
            lab_e = self.new_tmp("bre")
            if self._is_raw_temp(fr, tm["cond"]):
                # unsafe conditions are raw words (sev `!= 0`): plain
                # test, not the tagged truthiness path (raw 0 must be
                # falsy; the tag check would misread it).
                a.test_rr("rax", "rax")
                a.jcc("e", lab_e)
            else:
                self.truthy_br(lab_e)
            self._phi_moves(fr, blk["label"], by[tm["then"]])
            a.jmp(self._blabel(key, tm["then"]))
            a.label(lab_e)
            self._phi_moves(fr, blk["label"], by[tm["els"]])
            a.jmp(self._blabel(key, tm["els"]))
        elif tm["term"] == "ret":
            if tm["val"] is not None:
                self._load(fr, tm["val"], ln)
            elif key == "<main>":
                a.mov_ri32("rax", 0)  # hosted exit code, like emit_main
            else:
                a.mov_ri64("rax", Gen.HS_NULL)
            a.mov_rr("rsp", "rbp")
            a.pop_r("rbp")
            a.ret()
        elif tm["term"] == "raise":
            if tm["src"] is not None:
                self._load(fr, tm["src"], ln)
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
            else:
                a.call("hs_reraise")
        else:
            raise HSErr("IR: bad terminator", ln)

    def _emit_initfunc(self, modrec):
        # guarded one-time module body (shape mirrors emit_mod_init):
        # flag check, frame setup, entry blocks, done label.
        ekey = self.mod_entries[modrec["name"]]
        fdef = self.allfuncs[ekey]
        fr = self.frames[ekey]
        a = self.a
        done = self._init_done_label(modrec)
        a.data_label(done)
        a.data_qword(0)
        a.label(self._init_label(modrec))
        a.lea_rip("rax", done)
        a.mov_rm("rcx", "rax", 0)
        a.test_rr("rcx", "rcx")
        lab_done = self.new_tmp("mi")
        a.jcc("ne", lab_done)
        a.mov_ri32("rcx", 1)
        a.mov_mr("rax", "rcx", 0)
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        if fr["nloc"]:
            a.sub_ri32("rsp", 8 * fr["nloc"])
        self.frame_init_unbound(fr["nloc"])
        by = {b["label"]: b for b in fdef["blocks"]}
        for blk in fdef["blocks"]:
            self._emit_block(fr, ekey, blk, by)
        a.label(lab_done)
        a.ret()

    def _emit_ifunc(self, key):
        fdef = self.allfuncs[key]
        fr = self.frames[key]
        a = self.a
        if key == "<main>":
            a.label("hs_main")
        else:
            a.label(self.flabel[key])
        a.push_r("rbp")
        a.mov_rr("rbp", "rsp")
        if fr["nloc"]:
            a.sub_ri32("rsp", 8 * fr["nloc"])
        a.mov_rr("r10", "rsi")           # caller line (ffi errors report it)
        self.frame_init_unbound(fr["nloc"])
        if "%cline" in fr["slots"]:
            a.mov_mr("rbp", "r10", fr["slots"]["%cline"])
        self._gc_point()
        by = {b["label"]: b for b in fdef["blocks"]}
        for blk in fdef["blocks"]:
            self._emit_block(fr, key, blk, by)

    # ----- image -----

    def build_ir_image(self):
        self.a.data_label("gc_data_lo")
        self._plan()
        for nm in sorted(self.mglob):
            self._glabel(nm, "")
        inits = {ek for mp, ek in self.mod_entries.items() if mp != ""}
        for key in self.allorder:
            if key in inits:
                continue  # module bodies emit guarded, on import
            self._emit_ifunc(key)
        for _dotted, rec in self.modtab.items():
            if not rec.get("shell"):
                self._emit_initfunc(rec)
        a = self.a
        # _start: same contract as Gen.emit_main's tail
        a.label("_start")
        a.mov_rm("rdi", "rsp", 0)
        a.lea_rip("rax", "cmd_argc_")
        a.mov_mr("rax", "rdi", 0)
        a.lea_m("rax", "rsp", 8)
        a.lea_rip("rcx", "cmd_argv_")
        a.mov_mr("rcx", "rax", 0)
        a.and_ri32("rsp", -16)
        a.mov_mr_rip("gc_stk_", "rsp")
        a.call("hs_main")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rax", 60)
        a.syscall()
        self.emit_runtime()
        self.emit_fatal_line()
        self.emit_err_builders()
        if self.exc_used:
            self.emit_exc_runtime()
        # builtin-value stubs evaluate synthetic AST and need a real Scope
        # chain + module dict (only for name resolution, never emitted)
        _stubmod = {"name": "<main>", "pfx": "ir", "scope": Gen.Scope()}
        self.emit_builtin_runtime(_stubmod)
        self.emit_str_table()
        # print buffer + bump allocator state in data (hosted values,
        # copied from Gen.build_image)
        a.data_label("pbuf_")
        a.data_bytes(b"\0" * 32)
        a.data_label("pbuf_e")
        a.data_label("nbuf_")
        a.data_bytes(b"\0" * 32)
        a.data_label("nbuf_e")
        a.data_label("bump_ptr_")
        a.data_qword(0)
        a.data_label("bump_end_")
        a.data_qword(0)
        if self.exc_used:
            # exception handler stack + active-error value stack
            a.data_label("exc_depth")
            a.data_qword(0)
            a.data_label("exc_frames")
            a.data_bytes(b"\0" * (Gen.EXC_FRSZ * Gen.EXC_MAX))
            a.data_label("exc_vlen")
            a.data_qword(0)
            a.data_label("exc_vals")
            a.data_bytes(b"\0" * (Gen.EXC_VSZ * Gen.EXC_VMAX))
        a.data_label("gc_data_hi")
        import gcrt
        gcrt.gc_data(a)
        a.label("sp_")
        a.code += b" "
        a.label("nl_")
        a.code += b"\n"
        a.label("wspace_")
        ws = bytearray(256)
        for c in b" \t\n\v\f\r\x1c\x1d\x1e\x1f":
            ws[c] = 1
        a.code += bytes(ws)
        from x64 import layout, pack, layout_dyn, pack_dyn
        if self.ffi_syms:
            # dynamically linked image: ld.so + libc fill the GOT slots
            a.data_label("ffi_got_")
            a.data_bytes(b"\0" * (8 * len(self.ffi_syms)))
            lo = layout_dyn(len(self.a.code), len(self.a.data))
            code = self.a.resolve(lo["text_vaddr"], lo["data_vaddr"])
            libs = ["libc.so.6"] + [l for l in self.ffi_libs if l != "libc.so.6"]
            return pack_dyn(code, bytes(self.a.data),
                            self.a.labels["_start"], lo, libs,
                            self.ffi_syms, self.a.data_labels["ffi_got_"])
        lo = layout(len(self.a.code), len(self.a.data))
        code = self.a.resolve(lo["text_vaddr"], lo["data_vaddr"])
        start_off = self.a.labels["_start"]
        return pack(code, bytes(self.a.data), start_off, lo)


def build_irx64(prog_path, out_path):
    import os as _os
    interp.reset_parse_state()
    try:
        with open(prog_path, encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"error: cannot read {prog_path}: {e.strerror or e}",
              file=sys.stderr)
        return 1
    try:
        prog = interp.parse_program(src)
        irm = IR.build_module(prog)
        IR.verify_module(irm)
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    g = GenIR(irm, _os.path.dirname(_os.path.abspath(prog_path)))
    try:
        img = g.build_ir_image()
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    with open(out_path, "wb") as f:
        f.write(img)
    _os.chmod(out_path, 0o755)
    print(f"ok: irx64 -> {out_path} ({len(img)} bytes, via IR, no gcc)")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print("usage: irx64.py prog.hs [-o out]", file=_sys.stderr)
        _sys.exit(2)
    prog = _sys.argv[1]
    out = prog.rsplit(".", 1)[0] + ".irx64"
    if "-o" in _sys.argv:
        out = _sys.argv[_sys.argv.index("-o") + 1]
    _sys.exit(build_irx64(prog, out))
