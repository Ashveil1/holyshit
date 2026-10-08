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
INLINE_DIRECT = {"float", "len", "str", "int", "range", "append"}


class GenIR(Gen):
    def __init__(self, irmod):
        Gen.__init__(self, [], freestanding=False)
        self.irmod = irmod
        self.flabel = {}  # ir func key -> code label
        self.frames = {}  # ir func key -> frame descriptor
        self.glabels = {}  # module global name -> data label

    # ----- planning (no code): slots, caps, globals -----

    def _glabel(self, name):
        lab = self.glabels.get(name)
        if lab is None:
            lab = f"hsG_ir_{len(self.glabels)}"
            self.glabels[name] = lab
            self.a.data_label(lab)
            self.a.data_qword(Gen.HS_UNBOUND)
        return lab

    def _plan(self):
        irm = self.irmod
        main = irm["funcs"]["<main>"]
        mglob = set()
        for b in main["blocks"]:
            for ins in b["instrs"]:
                if ins["op"] in ("stvar", "stglobal"):
                    mglob.add(ins["name"])
        self.mglob = mglob
        for i, key in enumerate(irm["order"]):
            self.flabel[key] = f"hsIR_{i}"
            self.frames[key] = self._plan_func(key, irm["funcs"][key],
                                              key == "<main>")
        # definer links for closure chains (child -> func with the mkfunc)
        parents = {}
        for key in irm["order"]:
            for b in irm["funcs"][key]["blocks"]:
                for ins in b["instrs"]:
                    if ins["op"] == "mkfunc":
                        parents[ins["func"]] = key
        self.parents = parents
        for key in irm["order"]:
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
            if name in pf["pmap"] or name in pf["locals"]:
                return "cap"
            p = self.parents.get(p)
        if name in self.mglob:
            return "global"
        if name in Gen.BI_VALUES:
            return "builtin"
        if name in NOT_A_VALUE:
            return "novalue"
        return "auto"

    def _plan_res(self, key):
        fdef = self.irmod["funcs"][key]
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
        # inline-only builtins (float: no value form in x64) and direct
        # calls of inlinable builtins (exact error lines): a loaded temp
        # that is unshadowed and feeds call-fn positions exclusively gets
        # a dummy value at the load; any other use raises "not a value".
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                if ins["op"] == "load" and ins["name"] in INLINE_ONLY | \
                        INLINE_DIRECT and res.get(ins["name"]) in \
                        ("novalue", "builtin"):
                    ds = ins["dest"]
                    if fr["uses"].get(ds, []) and \
                            all(u == "call" for u in fr["uses"][ds]):
                        fr["floattemps"].add(ds)

    def _plan_func(self, key, fdef, is_main):
        params = list(fdef["params"])
        pmap = {p: 24 + 8 * i for i, p in enumerate(params)}
        stored = set()
        temps = []
        prov = {}
        uses = {}
        for b in fdef["blocks"]:
            for ins in b["instrs"]:
                d = ins.get("dest")
                if d is not None and d not in temps:
                    temps.append(d)
                if ins["op"] == "load":
                    prov[d] = ins["name"]
                if ins["op"] == "stvar" and not is_main:
                    stored.add(ins["name"])
                for k in ("l", "r", "v", "fn", "obj", "idx", "src"):
                    if k in ins and isinstance(ins[k], str):
                        uses.setdefault(ins[k], []).append(ins["op"])
                for k in ("args", "items"):
                    if k in ins:
                        for x in ins[k]:
                            uses.setdefault(x, []).append(ins["op"])
                for k, v in ins.get("pairs", []):
                    uses.setdefault(k, []).append(ins["op"])
                    uses.setdefault(v, []).append(ins["op"])
                for _al, at in ins.get("arms", []):
                    uses.setdefault(at, []).append(ins["op"])
        slots = {}
        n = [0]

        def take():
            n[0] += 1
            return -8 * n[0]

        for t in temps:
            slots[t] = take()
        for nm in sorted(stored):
            slots[nm] = take()
        return {"key": key, "params": params, "pmap": pmap,
                "locals": stored, "slots": slots, "nloc": n[0],
                "caps": [], "res": {}, "prov": prov, "uses": uses,
                "floattemps": set(), "is_main": is_main}

    # ----- operands -----

    def _load(self, fr, ref, ln):
        """rax = temp or name. Returns the resolution kind for names
        (temps report "temp") so callers can special-case builtins."""
        a = self.a
        if ref.startswith("%"):
            a.mov_rm("rax", "rbp", fr["slots"][ref])
            return "temp"
        if ref in fr["pmap"]:
            a.mov_rm("rax", "rbp", fr["pmap"][ref])
            return "bound"
        if ref in fr["locals"]:
            a.mov_rm("rax", "rbp", fr["slots"][ref])
            self.check_bound(ref, ln)
            return "bound"
        kind = fr["res"].get(ref, "auto")
        if kind == "cap":
            a.mov_rm("rax", "r15", 8 * fr["caps"].index(ref))
            return "bound"
        if kind == "builtin" or ref in Gen.BI_VALUES:
            self.ev_builtin_value(ref)
            return "builtin:" + ref
        if kind == "novalue" or ref in NOT_A_VALUE:
            raise HSErr(f"builtin '{ref}' is not a value (call it)", ln)
        lab = self._glabel(ref)
        a.lea_rip("rax", lab)
        a.mov_rm("rax", "rax", 0)
        self.check_bound(ref, ln)
        return "bound"

    def _store(self, fr, name, ln):
        """rax -> variable slot (params/locals) or module global."""
        a = self.a
        if not fr["is_main"]:
            if name in fr["pmap"]:
                a.mov_mr("rbp", "rax", fr["pmap"][name])
                return
            a.mov_mr("rbp", "rax", fr["slots"][name])
            return
        lab = self._glabel(name)
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

    def _print(self, fr, args, ln):
        a = self.a
        for i, t in enumerate(args):
            if i > 0:
                a.lea_rip("rdi", "sp_")
                a.mov_ri32("rsi", 1)
                self.rt_out()
            self._load(fr, t, ln)
            a.mov_rr("rdi", "rax")
            a.call("print_val")
        a.lea_rip("rdi", "nl_")
        a.mov_ri32("rsi", 1)
        self.rt_out()

    def _print(self, fr, args, ln):
        a = self.a
        for i, t in enumerate(args):
            if i > 0:
                a.lea_rip("rdi", "sp_")
                a.mov_ri32("rsi", 1)
                self.rt_out()
            self._load(fr, t, ln)
            a.mov_rr("rdi", "rax")
            a.call("print_val")
        a.lea_rip("rdi", "nl_")
        a.mov_ri32("rsi", 1)
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
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_dkey)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_dget)
        a.label(lab_dkey)
        self.raise_static("dict key must be Str", ln)
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
        a.test_rr("r11", "r11")
        a.jcc("ne", lab_sdkey)
        a.mov_rm("r11", "rcx", 0)
        a.cmp_ri32("r11", Gen.K_STR)
        a.jcc("e", lab_sdset)
        a.label(lab_sdkey)
        self.raise_static("dict key must be Str", ln)
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
        if fn in fr["floattemps"]:
            name = fr["prov"][fn]
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

    def _mkfunc(self, fr, dest, qname, ln):
        # transliterated Gen ex-def: captures evaluated in the defining
        # frame, Func = [kind][code][nparams][name][caps...].
        a = self.a
        child = self.irmod["funcs"][qname]
        cfr = self.frames[qname]
        for nm in cfr["caps"]:
            self._load(fr, nm, ln)
            a.push_r("rax")
        n = len(cfr["caps"])
        a.mov_ri32("rdi", 8 * (4 + n))
        a.call("x_malloc")
        for i in reversed(range(n)):
            a.pop_r("rcx")
            a.mov_mr("rax", "rcx", 8 * (i + 4))
        a.mov_ri32("rcx", Gen.K_FUNC)
        a.mov_mr("rax", "rcx", 0)
        a.lea_rip("rcx", self.flabel[qname])
        a.mov_mr("rax", "rcx", 8)
        a.mov_ri32("rcx", len(child["params"]))
        a.mov_mr("rax", "rcx", 16)
        a.push_r("rax")
        a.lea_rip("rdi", self.rstr(child["dispname"]))
        a.mov_ri32("rsi", len(child["dispname"].encode()))
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

    def _emit_block(self, fr, key, blk, by):
        a = self.a
        a.label(self._blabel(key, blk["label"]))
        for ins in blk["instrs"]:
            op = ins["op"]
            ln = ins["line"]
            if op == "const":
                self._const(ins["val"], ln)
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "load":
                if ins["dest"] in fr["floattemps"]:
                    a.mov_ri32("rax", 0)  # dummy: inline call ignores it
                else:
                    self._load(fr, ins["name"], ln)
                a.mov_mr("rbp", "rax", fr["slots"][ins["dest"]])
            elif op == "stvar":
                self._load(fr, ins["src"], ln)
                self._store(fr, ins["name"], ln)
            elif op == "stglobal":
                self._load(fr, ins["src"], ln)
                lab = self._glabel(ins["name"])
                a.lea_rip("rcx", lab)
                a.mov_mr("rcx", "rax", 0)
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
            self.truthy_br(lab_e)
            self._phi_moves(fr, blk["label"], by[tm["then"]])
            a.jmp(self._blabel(key, tm["then"]))
            a.label(lab_e)
            self._phi_moves(fr, blk["label"], by[tm["els"]])
            a.jmp(self._blabel(key, tm["els"]))
        elif tm["term"] == "ret":
            if tm["val"] is not None:
                self._load(fr, tm["val"], ln)
            elif fr["is_main"]:
                a.mov_ri32("rax", 0)  # hosted exit code, like emit_main
            else:
                a.mov_ri64("rax", Gen.HS_NULL)
            a.mov_rr("rsp", "rbp")
            a.pop_r("rbp")
            a.ret()
        else:
            raise HSErr("IR: bad terminator", ln)

    def _emit_ifunc(self, key):
        fdef = self.irmod["funcs"][key]
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
        self.frame_init_unbound(fr["nloc"])
        by = {b["label"]: b for b in fdef["blocks"]}
        for blk in fdef["blocks"]:
            self._emit_block(fr, key, blk, by)

    # ----- image -----

    def build_ir_image(self):
        self._plan()
        for nm in sorted(self.mglob):
            self._glabel(nm)
        for key in self.irmod["order"]:
            self._emit_ifunc(key)
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
        a.call("hs_main")
        a.mov_rr("rdi", "rax")
        a.mov_ri32("rax", 60)
        a.syscall()
        self.emit_runtime()
        self.emit_fatal_line()
        self.emit_err_builders()
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
        a.label("sp_")
        a.code += b" "
        a.label("nl_")
        a.code += b"\n"
        a.label("wspace_")
        ws = bytearray(256)
        for c in b" \t\n\v\f\r\x1c\x1d\x1e\x1f":
            ws[c] = 1
        a.code += bytes(ws)
        from x64 import layout, pack
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
    g = GenIR(irm)
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
