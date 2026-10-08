#!/usr/bin/env python3
"""holyshit IR: architecture-neutral flat CFG built from the interp AST.

    python3 ir.py prog.hs [args...]   # execute via the IR (reference check)

Every backend (x86-64 now, ARM64 later, JIT later) will consume this IR
instead of reading AST. `interp.py` stays the parser + reference
semantics; this module must be byte-identical to it on stdout/stderr/rc.

Design: expression temporaries are pure SSA (`%1`, `%2`, ...); source
variables live in frames (`stvar`/`load`, like memory). Control flow is
explicit blocks. That split is deliberate: no mem2reg yet (Task 3), so
closures, forward refs and path-dependent definedness all behave exactly
like interp by construction.

Subset (Tasks 1-2): num/str/var, list/dict literals, index/slice,
setindex, bin (arith/cmp/bitwise/and/or), not/neg/unot, call, print, set,
def/return, global, if/elif/else, while/for/break/continue, pass. Anything
else fails fast with `IR: unsupported '<t>'` so gaps are loud, never silent.

Deliberate divergences from interp (both rc=1, different stderr):
`break`/`continue` outside a loop and top-level `return` are clean
`error:` lines here; interp lets BreakExc/ContinueExc/ReturnExc escape
as a Python traceback. Matching a traceback byte-for-byte would couple
the IR to interp.py's file layout, so the IR defines the sane behavior.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import interp
from interp import HSErr

# Builtins the IR runtime reuses verbatim (same function objects as interp,
# so messages match by construction). Anything else fails at call time.
IR_BUILTINS = {"len", "str", "int", "float", "range", "append"}


def _n(kind, line, **kw):
    d = {"op": kind, "line": line}
    d.update(kw)
    return d


def _t(term, line, **kw):
    d = {"term": term, "line": line}
    d.update(kw)
    return d


# ---------- builder: AST -> flat CFG ----------

class _FuncBuild:
    def __init__(self, b, name, params, dispname):
        self.b = b
        self.name = name
        self.dispname = dispname
        self.params = list(params)
        self.blocks = []
        self.tmp = 0
        self.cur = None
        self.loops = []  # {header_exit...}: {"header": blk, "exit": blk}
        self.gnames = set()

    def block(self, hint):
        lab = f"b_{hint}_{len(self.blocks)}"
        blk = {"label": lab, "instrs": [], "term": None}
        self.blocks.append(blk)
        return blk

    def start(self, blk):
        self.cur = blk

    def temp(self):
        self.tmp += 1
        return f"%{self.tmp}"

    def emit(self, ins):
        assert self.cur is not None and self.cur["term"] is None
        self.cur["instrs"].append(ins)

    def end(self, term):
        assert self.cur is not None and self.cur["term"] is None
        self.cur["term"] = term
        self.cur = None

    def alive(self):
        if self.cur is None:
            self.start(self.block("dead"))


class Builder:
    def __init__(self, pfx=""):
        self.funcs = {}
        self.order = []
        self.pfx = pfx

    def build(self, prog, pfx=""):
        pfx = pfx or self.pfx
        fb = _FuncBuild(self, f"{pfx}<main>", [], "<main>")
        entry = fb.block("entry")
        fb.start(entry)
        self._body(fb, prog)
        if fb.cur is not None:
            fb.end(_t("ret", prog[-1]["line"] if prog else 0, val=None))
        fn = {"name": f"{pfx}<main>", "dispname": "<main>", "params": [],
              "blocks": fb.blocks, "entry": entry["label"],
              "globals": sorted(fb.gnames)}
        self.funcs[f"{pfx}<main>"] = fn
        self.order.append(f"{pfx}<main>")
        return {"funcs": self.funcs, "order": self.order,
                "entry": f"{pfx}<main>"}

    # ----- statements -----

    def _body(self, fb, stmts):
        for s in stmts:
            fb.alive()
            self._stmt(fb, s)

    def _stmt(self, fb, s):
        t = s["t"]
        ln = s["line"]
        if t == "pass":
            return
        if t == "global":
            fb.gnames.update(s["names"])
            return
        if t == "set":
            v = self._expr(fb, s["val"])
            if s["name"] in fb.gnames:
                fb.emit(_n("stglobal", ln, name=s["name"], src=v))
            else:
                fb.emit(_n("stvar", ln, name=s["name"], src=v))
            return
        if t == "expr":
            self._expr(fb, s["val"])
            return
        if t == "print":
            args = [self._expr(fb, a) for a in s["args"]]
            fb.emit(_n("print", ln, args=args))
            return
        if t == "return":
            v = self._expr(fb, s["val"]) if s["val"] is not None else None
            fb.end(_t("ret", ln, val=v))
            return
        if t == "break":
            if not fb.loops:
                raise HSErr("break outside loop", ln)
            fb.end(_t("jmp", ln, to=fb.loops[-1]["exit"]["label"]))
            return
        if t == "continue":
            if not fb.loops:
                raise HSErr("continue outside loop", ln)
            lp = fb.loops[-1]
            to = lp["incr"]["label"] if lp["incr"] is not None else \
                lp["header"]["label"]
            fb.end(_t("jmp", ln, to=to))
            return
        if t == "def":
            self._def(fb, s)
            return
        if t == "if":
            self._if(fb, s)
            return
        if t == "while":
            self._while(fb, s)
            return
        if t == "for":
            self._for(fb, s)
            return
        if t == "import":
            import re as _re
            if not _re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_]"
                             r"[A-Za-z0-9_]*)*$", s["name"]):
                raise HSErr(f"bad module name '{s['name']}'", ln)
            fb.emit(_n("import", ln, name=s["name"]))
            return
        if t == "setindex":
            obj = self._expr(fb, s["obj"])
            idx = self._expr(fb, s["idx"])
            val = self._expr(fb, s["val"])
            fb.emit(_n("setindex", ln, obj=obj, idx=idx, val=val))
            return
        if t == "setattr":
            obj = self._expr(fb, s["obj"])
            val = self._expr(fb, s["val"])
            fb.emit(_n("setattr", ln, obj=obj, name=s["name"], val=val))
            return
        raise HSErr(f"IR: unsupported '{t}'", ln)

    def _def(self, fb, s):
        ln = s["line"]
        qname = f"{self.pfx}{s['name']}$L{ln}"
        child = _FuncBuild(self, qname, s["params"], s["name"])
        entry = child.block("entry")
        child.start(entry)
        self._body(child, s["body"])
        if child.cur is not None:
            last = s["body"][-1]["line"] if s["body"] else ln
            child.end(_t("ret", last, val=None))
        self.funcs[qname] = {"name": qname, "dispname": s["name"],
                             "params": list(s["params"]),
                             "blocks": child.blocks,
                             "entry": entry["label"],
                             "globals": sorted(child.gnames)}
        self.order.append(qname)
        d = fb.temp()
        fb.emit(_n("mkfunc", ln, dest=d, func=qname))
        if s["name"] in fb.gnames:
            fb.emit(_n("stglobal", ln, name=s["name"], src=d))
        else:
            fb.emit(_n("stvar", ln, name=s["name"], src=d))

    def _if(self, fb, s):
        ln = s["line"]
        join = fb.block("join")
        branches = [(s["cond"], s["then"])]
        branches += s["elifs"]
        for cond, body in branches:
            c = self._expr(fb, cond)
            tb = fb.block("then")
            nb = fb.block("next")
            fb.end(_t("br", cond["line"], cond=c, then=tb["label"],
                       els=nb["label"]))
            fb.start(tb)
            self._body(fb, body)
            if fb.cur is not None:
                fb.end(_t("jmp", ln, to=join["label"]))
            fb.start(nb)
        self._body(fb, s["els"])
        if fb.cur is not None:
            fb.end(_t("jmp", ln, to=join["label"]))
        fb.start(join)

    def _while(self, fb, s):
        ln = s["line"]
        header = fb.block("loop")
        fb.end(_t("jmp", ln, to=header["label"]))
        fb.start(header)
        c = self._expr(fb, s["cond"])
        bodyb = fb.block("body")
        exitb = fb.block("exit")
        fb.end(_t("br", s["cond"]["line"], cond=c, then=bodyb["label"],
                   els=exitb["label"]))
        fb.loops.append({"header": header, "exit": exitb, "incr": None})
        fb.start(bodyb)
        self._body(fb, s["body"])
        if fb.cur is not None:
            fb.end(_t("jmp", ln, to=header["label"]))
        fb.loops.pop()
        fb.start(exitb)

    def _for(self, fb, s):
        # Desugar to len/index/while over private frame slots. The sequence
        # object itself is shared (like interp's `seq = it`), so mutation
        # during iteration stays visible on both sides.
        ln = s["line"]
        tag = fb.temp()[1:]  # unique per loop, e.g. "7" -> $it7/$i7
        it = f"$it{tag}"
        ix = f"$i{tag}"
        t = self._expr(fb, s["iter"])
        d = fb.temp()
        fb.emit(_n("iterseq", ln, dest=d, src=t))
        fb.emit(_n("stvar", ln, name=it, src=d))
        z = fb.temp()
        fb.emit(_n("const", ln, dest=z, val=0))
        fb.emit(_n("stvar", ln, name=ix, src=z))
        header = fb.block("loop")
        fb.end(_t("jmp", ln, to=header["label"]))
        fb.start(header)
        a = fb.temp()
        fb.emit(_n("load", ln, dest=a, name=ix))
        b = fb.temp()
        fb.emit(_n("load", ln, dest=b, name=it))
        n = fb.temp()
        fn = fb.temp()
        fb.emit(_n("load", ln, dest=fn, name="len"))
        fb.emit(_n("call", ln, dest=n, fn=fn, args=[b]))
        c = fb.temp()
        fb.emit(_n("bin", ln, dest=c, binop="<", l=a, r=n))
        bodyb = fb.block("body")
        exitb = fb.block("exit")
        fb.end(_t("br", ln, cond=c, then=bodyb["label"], els=exitb["label"]))
        incrb = fb.block("incr")
        fb.loops.append({"header": header, "exit": exitb, "incr": incrb})
        fb.start(bodyb)
        e = fb.temp()
        fb.emit(_n("load", ln, dest=e, name=it))
        k = fb.temp()
        fb.emit(_n("load", ln, dest=k, name=ix))
        v = fb.temp()
        fb.emit(_n("index", ln, dest=v, obj=e, idx=k))
        if s["var"] in fb.gnames:
            fb.emit(_n("stglobal", ln, name=s["var"], src=v))
        else:
            fb.emit(_n("stvar", ln, name=s["var"], src=v))
        self._body(fb, s["body"])
        if fb.cur is not None:
            fb.end(_t("jmp", ln, to=incrb["label"]))
        fb.start(incrb)
        a2 = fb.temp()
        fb.emit(_n("load", ln, dest=a2, name=ix))
        one = fb.temp()
        fb.emit(_n("const", ln, dest=one, val=1))
        a3 = fb.temp()
        fb.emit(_n("bin", ln, dest=a3, binop="+", l=a2, r=one))
        fb.emit(_n("stvar", ln, name=ix, src=a3))
        fb.end(_t("jmp", ln, to=header["label"]))
        fb.loops.pop()
        fb.start(exitb)

    # ----- expressions -----

    def _expr(self, fb, e):
        t = e["t"]
        ln = e["line"]
        if t == "num" or t == "str":
            d = fb.temp()
            fb.emit(_n("const", ln, dest=d, val=e["val"]))
            return d
        if t == "var":
            d = fb.temp()
            fb.emit(_n("load", ln, dest=d, name=e["name"]))
            return d
        if t == "list":
            items = [self._expr(fb, x) for x in e["items"]]
            d = fb.temp()
            fb.emit(_n("build_list", ln, dest=d, items=items))
            return d
        if t == "dict":
            pairs = [(self._expr(fb, k), self._expr(fb, v))
                     for k, v in e["pairs"]]
            d = fb.temp()
            fb.emit(_n("build_dict", ln, dest=d, pairs=pairs))
            return d
        if t == "index":
            obj = self._expr(fb, e["obj"])
            idx = self._expr(fb, e["idx"])
            d = fb.temp()
            fb.emit(_n("index", ln, dest=d, obj=obj, idx=idx))
            return d
        if t == "attr":
            obj = self._expr(fb, e["obj"])
            d = fb.temp()
            fb.emit(_n("attr", ln, dest=d, obj=obj, name=e["name"]))
            return d
        if t == "slice":
            obj = self._expr(fb, e["obj"])
            start = self._expr(fb, e["start"]) \
                if e["start"] is not None else None
            stop = self._expr(fb, e["stop"]) \
                if e["stop"] is not None else None
            d = fb.temp()
            fb.emit(_n("slice", ln, dest=d, obj=obj, start=start, stop=stop))
            return d
        if t == "bin":
            if e["op"] == "and":
                return self._logic(fb, e, True)
            if e["op"] == "or":
                return self._logic(fb, e, False)
            l = self._expr(fb, e["l"])
            r = self._expr(fb, e["r"])
            d = fb.temp()
            fb.emit(_n("bin", ln, dest=d, binop=e["op"], l=l, r=r))
            return d
        if t in ("neg", "unot", "not"):
            v = self._expr(fb, e["val"])
            d = fb.temp()
            fb.emit(_n("un", ln, dest=d, unop=t, v=v))
            return d
        if t == "call":
            fn = self._expr(fb, e["fn"])
            args = [self._expr(fb, a) for a in e["args"]]
            d = fb.temp()
            fb.emit(_n("call", ln, dest=d, fn=fn, args=args))
            return d
        raise HSErr(f"IR: unsupported '{t}'", ln)

    def _logic(self, fb, e, is_and):
        # short-circuit like interp: only one side's value survives
        ln = e["line"]
        l = self._expr(fb, e["l"])
        brb = fb.cur["label"]
        rb = fb.block("rhs")
        jb = fb.block("join")
        if is_and:
            fb.end(_t("br", ln, cond=l, then=rb["label"], els=jb["label"]))
        else:
            fb.end(_t("br", ln, cond=l, then=jb["label"], els=rb["label"]))
        fb.start(rb)
        r = self._expr(fb, e["r"])
        rl = rb["label"]
        fb.end(_t("jmp", ln, to=jb["label"]))
        rl = fb.blocks[-2]["label"] if False else rl
        fb.start(jb)
        d = fb.temp()
        jb["instrs"].append(_n("phi", ln, dest=d, arms=[(brb, l), (rl, r)]))
        return d


# ---------- verifier ----------

def verify_module(m):
    if m["entry"] not in m["funcs"]:
        raise HSErr("IR: missing entry", 0)
    seen = set()
    for name in m["order"]:
        if name in seen:
            raise HSErr(f"IR: duplicate function '{name}'", 0)
        seen.add(name)
        if name not in m["funcs"]:
            raise HSErr(f"IR: missing function '{name}'", 0)
        _verify_func(m["funcs"][name], m["funcs"])


def _verify_func(fn, funcs):
    labels = [b["label"] for b in fn["blocks"]]
    if len(set(labels)) != len(labels):
        raise HSErr(f"IR: duplicate block label in '{fn['dispname']}'", 0)
    by = {b["label"]: b for b in fn["blocks"]}
    if fn["entry"] not in by:
        raise HSErr(f"IR: missing entry block in '{fn['dispname']}'", 0)
    defs = {}
    for b in fn["blocks"]:
        for ins in b["instrs"]:
            d = ins.get("dest")
            if d is not None:
                if d in defs:
                    raise HSErr(f"IR: temp '{d}' redefined", ins["line"])
                defs[d] = b["label"]
    preds = {l: set() for l in labels}
    succs = {l: [] for l in labels}

    def _edge(frm, to, tm):
        _need(by, to, tm)
        preds[to].add(frm)
        succs[frm].append(to)

    for b in fn["blocks"]:
        tm = b["term"]
        if tm is None:
            raise HSErr(f"IR: block '{b['label']}' has no terminator",
                        b["instrs"][-1]["line"] if b["instrs"] else 0)
        if tm["term"] == "jmp":
            _edge(b["label"], tm["to"], tm)
        elif tm["term"] == "br":
            _edge(b["label"], tm["then"], tm)
            _edge(b["label"], tm["els"], tm)
        elif tm["term"] != "ret":
            raise HSErr(f"IR: bad terminator '{tm['term']}'", tm["line"])

    # reachable set: dominance is only checked where execution can go.
    # Code after return lives in dead blocks and is exempt (but still
    # needs labels, terminators and well-formed instructions).
    reach = set()
    stack = [fn["entry"]]
    while stack:
        l = stack.pop()
        if l in reach:
            continue
        reach.add(l)
        stack.extend(succs[l])

    dom = {l: set(labels) for l in labels}
    dom[fn["entry"]] = {fn["entry"]}
    changed = True
    while changed:
        changed = False
        for l in labels:
            if l == fn["entry"]:
                continue
            ps = preds[l]
            new = set.intersection(*(dom[p] for p in ps)) | {l} if ps \
                else {l}
            if new != dom[l]:
                dom[l] = new
                changed = True

    def _use(t, at, ln):
        if t not in defs:
            raise HSErr(f"IR: undefined temp '{t}'", ln)
        if at in reach and defs[t] not in dom[at]:
            raise HSErr(f"IR: temp '{t}' does not dominate use", ln)

    for b in fn["blocks"]:
        tm = b["term"]
        if tm["term"] == "br":
            _use(tm["cond"], b["label"], tm["line"])
        elif tm["term"] == "ret":
            if tm["val"] is not None:
                _use(tm["val"], b["label"], tm["line"])
    for b in fn["blocks"]:
        for ins in b["instrs"]:
            op = ins["op"]
            ln = ins["line"]
            if op == "phi":
                if b["label"] == fn["entry"]:
                    raise HSErr("IR: phi in entry block", ln)
                if not ins["arms"]:
                    raise HSErr("IR: phi with no arms", ln)
                for al, at in ins["arms"]:
                    if al not in preds[b["label"]]:
                        raise HSErr(
                            f"IR: phi arm from non-predecessor '{al}'", ln)
                    # the arm value flows along the edge: its definition
                    # must dominate the predecessor it comes from
                    _use(at, al, ln)
            elif op in ("const", "load", "stvar", "stglobal", "import"):
                pass
            elif op == "attr":
                _use(ins["obj"], b["label"], ln)
            elif op == "setattr":
                _use(ins["obj"], b["label"], ln)
                _use(ins["val"], b["label"], ln)
            elif op == "mkfunc":
                if ins["func"] not in funcs:
                    raise HSErr(f"IR: unknown function '{ins['func']}'", ln)
            elif op == "build_list":
                for x in ins["items"]:
                    _use(x, b["label"], ln)
            elif op == "build_dict":
                for k, v in ins["pairs"]:
                    _use(k, b["label"], ln)
                    _use(v, b["label"], ln)
            elif op == "index":
                _use(ins["obj"], b["label"], ln)
                _use(ins["idx"], b["label"], ln)
            elif op == "slice":
                _use(ins["obj"], b["label"], ln)
                for k in ("start", "stop"):
                    if ins[k] is not None:
                        _use(ins[k], b["label"], ln)
            elif op == "setindex":
                for k in ("obj", "idx", "val"):
                    _use(ins[k], b["label"], ln)
            elif op == "iterseq":
                _use(ins["src"], b["label"], ln)
            elif op == "bin":
                _use(ins["l"], b["label"], ln)
                _use(ins["r"], b["label"], ln)
            elif op == "un":
                _use(ins["v"], b["label"], ln)
            elif op == "call":
                _use(ins["fn"], b["label"], ln)
                for a in ins["args"]:
                    _use(a, b["label"], ln)
            elif op == "print":
                for a in ins["args"]:
                    _use(a, b["label"], ln)
            else:
                raise HSErr(f"IR: bad op '{op}'", ln)


def _need(by, lab, tm):
    if lab not in by:
        raise HSErr(f"IR: jump to missing block '{lab}'", tm["line"])


# ---------- pretty printer ----------

def _q(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        out = []
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
            elif 32 <= o <= 126:
                out.append(ch)
            elif o <= 0xFFFF:
                out.append(f"\\u{o:04x}")
            else:
                o -= 0x10000
                out.append(f"\\u{(0xD800 + (o >> 10)):04x}")
                out.append(f"\\u{(0xDC00 + (o & 0x3FF)):04x}")
        return '"' + "".join(out) + '"'
    return str(v)


def _unq(lit, line):
    # inverse of _q for string literals (handles surrogate pairs)
    if len(lit) < 2 or not lit.startswith('"') or not lit.endswith('"'):
        raise HSErr("IR: bad string literal", line)
    body = lit[1:-1]
    out = []
    i = 0
    while i < len(body):
        c = body[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= len(body):
            raise HSErr("IR: bad string escape", line)
        e = body[i]
        i += 1
        if e == "n":
            out.append("\n")
        elif e == "t":
            out.append("\t")
        elif e == "r":
            out.append("\r")
        elif e == '"':
            out.append('"')
        elif e == "\\":
            out.append("\\")
        elif e == "u":
            hexd = body[i:i + 4]
            if len(hexd) != 4 or not all(ch in "0123456789abcdefABCDEF"
                                        for ch in hexd):
                raise HSErr("IR: bad string escape", line)
            i += 4
            cp = int(hexd, 16)
            if 0xD800 <= cp <= 0xDBFF and body[i:i + 2] == "\\u":
                hex2 = body[i + 2:i + 6]
                if len(hex2) == 4 and all(
                        ch in "0123456789abcdefABCDEF" for ch in hex2):
                    lo = int(hex2, 16)
                    if 0xDC00 <= lo <= 0xDFFF:
                        out.append(chr(0x10000 + ((cp - 0xD800) << 10) +
                                        (lo - 0xDC00)))
                        i += 6
                        continue
            out.append(chr(cp))
        else:
            raise HSErr("IR: bad string escape", line)
    return "".join(out)


def _const_val(text, line):
    if text in ("true", "false", "null"):
        return {"true": True, "false": False, "null": None}[text]
    if text.startswith('"'):
        return _unq(text, line)
    if text.lstrip("+-").isdigit():
        return int(text)
    try:
        return float(text)
    except ValueError:
        raise HSErr("IR: bad const value", line)


def dump_module(m):
    # Canonical text: `hs.py ir` prints this; parse_module reads it back.
    # Every instruction/terminator carries its source line as ` @N` so a
    # reparsed module executes with identical error lines. Function headers
    # use the unique key (`fib$L2`); the display name is re-derived.
    out = []
    for name in m["order"]:
        fn = m["funcs"][name]
        out.append(f"func {name}({', '.join(fn['params'])}):")
        for b in fn["blocks"]:
            out.append(f"{b['label']}:")
            for ins in b["instrs"]:
                out.append(f"  {dump_instr(ins)} @{ins['line']}")
            out.append(f"  {dump_term(b['term'])} @{b['term']['line']}")
    return "\n".join(out) + "\n"


def dump_instr(ins):
    op = ins["op"]
    if op == "const":
        return f"{ins['dest']} = const {_q(ins['val'])}"
    if op == "load":
        return f"{ins['dest']} = load {ins['name']}"
    if op == "stvar":
        return f"stvar {ins['name']} {ins['src']}"
    if op == "stglobal":
        return f"stglobal {ins['name']} {ins['src']}"
    if op == "mkfunc":
        return f"{ins['dest']} = mkfunc {ins['func']}"
    if op == "bin":
        return f"{ins['dest']} = bin {ins['binop']} {ins['l']} {ins['r']}"
    if op == "un":
        return f"{ins['dest']} = un {ins['unop']} {ins['v']}"
    if op == "call":
        args = ", ".join(ins["args"])
        return f"{ins['dest']} = call {ins['fn']}({args})"
    if op == "print":
        return "print" + (" " + ", ".join(ins["args"]) if ins["args"] else "")
    if op == "import":
        return f"import {ins['name']}"
    if op == "attr":
        return f"{ins['dest']} = attr {ins['obj']} {ins['name']}"
    if op == "setattr":
        return f"setattr {ins['obj']} {ins['name']} {ins['val']}"
    if op == "build_list":
        return f"{ins['dest']} = build_list [{', '.join(ins['items'])}]"
    if op == "build_dict":
        ps = " ".join(f"({k}: {v})" for k, v in ins["pairs"])
        return f"{ins['dest']} = build_dict" + (" " + ps if ps else "")
    if op == "index":
        return f"{ins['dest']} = index {ins['obj']} {ins['idx']}"
    if op == "setindex":
        return f"setindex {ins['obj']} {ins['idx']} {ins['val']}"
    if op == "slice":
        s = ins["start"] if ins["start"] is not None else "-"
        e = ins["stop"] if ins["stop"] is not None else "-"
        return f"{ins['dest']} = slice {ins['obj']} {s} {e}"
    if op == "setindex":
        return f"setindex {ins['obj']} {ins['idx']} {ins['val']}"
    if op == "iterseq":
        return f"{ins['dest']} = iterseq {ins['src']}"
    if op == "phi":
        arms = " ".join(f"[{a}: {t}]" for a, t in ins["arms"])
        return f"{ins['dest']} = phi {arms}"
    return f"<bad {op}>"


def dump_term(tm):
    if tm["term"] == "jmp":
        return f"jmp {tm['to']}"
    if tm["term"] == "br":
        return f"br {tm['cond']} {tm['then']} {tm['els']}"
    if tm["term"] == "ret":
        return f"ret {tm['val']}" if tm["val"] is not None else "ret"
    return "<bad term>"


# ---------- text parser (inverse of dump_module) ----------

import re as _re

_FUNC_RE = _re.compile(r"func (\S+)\((.*)\):$")
_LABEL_RE = _re.compile(r"[A-Za-z_][A-Za-z0-9_$]*$")
_LINE_RE = _re.compile(r"^(.*) @(\d+)$")


def _disp_of(key):
    # qnames look like `fib$L2` or `pkg.mod.f$L12`; the display name is
    # the bare function name (what arity errors quote, like interp).
    if "$L" in key:
        head, tail = key.rsplit("$L", 1)
        if head and tail.isdigit():
            return head.rsplit(".", 1)[-1]
    return key


def _split_top(s):
    # split on ", " but not inside quotes/brackets/parens
    parts, depth, cur, instr = [], 0, "", False
    i = 0
    while i < len(s):
        c = s[i]
        if instr:
            cur += c
            if c == "\\" and i + 1 < len(s):
                cur += s[i + 1]
                i += 1
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
            cur += c
        elif c in "[(":
            depth += 1
            cur += c
        elif c in "])":
            depth -= 1
            cur += c
        elif c == "," and depth == 0 and s[i:i + 2] == ", ":
            parts.append(cur)
            cur = ""
            i += 1
        else:
            cur += c
        i += 1
    if cur != "" or parts:
        parts.append(cur)
    return parts


def parse_module(text):
    funcs = {}
    order = []
    fn = None
    blk = None
    for rawno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("func "):
            m = _FUNC_RE.match(line)
            if not m:
                raise HSErr("IR: bad func header", 0)
            key, params = m.group(1), m.group(2)
            if key in funcs:
                raise HSErr(f"IR: duplicate function '{key}'", 0)
            ps = [] if params == "" else [p for p in params.split(", ")]
            for p in ps:
                if not _LABEL_RE.match(p or " "):
                    raise HSErr("IR: bad param", 0)
            fn = {"name": key, "dispname": _disp_of(key), "params": ps,
                  "blocks": [], "entry": None, "globals": []}
            funcs[key] = fn
            order.append(key)
            blk = None
            continue
        if fn is None:
            raise HSErr("IR: code outside function", 0)
        if not line.startswith((" ", "\t")) and line.endswith(":"):
            lab = line[:-1]
            if not _LABEL_RE.match(lab):
                raise HSErr("IR: bad block label", 0)
            blk = {"label": lab, "instrs": [], "term": None}
            fn["blocks"].append(blk)
            if fn["entry"] is None:
                fn["entry"] = lab
            continue
        if blk is None:
            raise HSErr("IR: code outside block", 0)
        m = _LINE_RE.match(line.strip())
        if not m:
            raise HSErr("IR: bad line (want `<code> @N`)", 0)
        code, lns = m.group(1), int(m.group(2))
        if blk["term"] is not None:
            raise HSErr("IR: code after terminator", lns)
        ins = _parse_code(code, lns)
        if "term" in ins:
            blk["term"] = ins
        else:
            blk["instrs"].append(ins)
    if "<main>" not in funcs:
        raise HSErr("IR: missing entry", 0)
    for fn in funcs.values():
        # `global` declarations are not printed; re-derive them from the
        # stores (the builder emits stglobal exactly for declared names,
        # and bare `global g` without a store needs no entry: reads use
        # load either way, matching interp's chain lookup)
        fn["globals"] = sorted({ins["name"] for b in fn["blocks"]
                                for ins in b["instrs"]
                                if ins["op"] == "stglobal"})
    return {"funcs": funcs, "order": order, "entry": "<main>"}


def _parse_code(code, ln):
    if code.startswith("jmp "):
        return _t("jmp", ln, to=_label(code[4:], ln))
    if code.startswith("br "):
        _, c, t, e = code.split()
        return _t("br", ln, cond=_temp(c, ln), then=_label(t, ln),
                   els=_label(e, ln))
    if code == "ret" or code.startswith("ret "):
        rest = code[3:].strip()
        return _t("ret", ln, val=_temp(rest, ln) if rest else None)
    if code.startswith("print"):
        rest = code[5:].strip()
        args = [] if rest == "" else [_temp(a.strip(), ln)
                                     for a in _split_top(rest)]
        return _n("print", ln, args=args)
    if code.startswith("import "):
        return _n("import", ln, name=code[7:])
    if code.startswith("setattr "):
        _, o, nm, v = code.split()
        return _n("setattr", ln, obj=_temp(o, ln), name=nm,
                  val=_temp(v, ln))
    if code.startswith("stvar "):
        _, name, src = code.split()
        return _n("stvar", ln, name=name, src=_temp(src, ln))
    if code.startswith("stglobal "):
        _, name, src = code.split()
        return _n("stglobal", ln, name=name, src=_temp(src, ln))
    if code.startswith("setindex "):
        _, o, ix, v = code.split()
        return _n("setindex", ln, obj=_temp(o, ln), idx=_temp(ix, ln),
                  val=_temp(v, ln))
    m = _re.match(r"(%\d+) = (.*)$", code)
    if not m:
        raise HSErr("IR: bad instruction", ln)
    dest, rhs = m.group(1), m.group(2)
    if rhs.startswith("const "):
        return _n("const", ln, dest=dest, val=_const_val(rhs[6:], ln))
    if rhs.startswith("load "):
        return _n("load", ln, dest=dest, name=rhs[5:])
    if rhs.startswith("mkfunc "):
        return _n("mkfunc", ln, dest=dest, func=rhs[7:])
    if rhs.startswith("bin "):
        _, op, l, r = rhs.split()
        return _n("bin", ln, dest=dest, binop=op, l=_temp(l, ln),
                  r=_temp(r, ln))
    if rhs.startswith("un "):
        _, op, v = rhs.split()
        return _n("un", ln, dest=dest, unop=op, v=_temp(v, ln))
    if rhs.startswith("call "):
        m2 = _re.match(r"(%\d+)\((.*)\)$", rhs[5:])
        if not m2:
            raise HSErr("IR: bad call", ln)
        args = [] if m2.group(2) == "" else [_temp(a.strip(), ln)
                                            for a in _split_top(m2.group(2))]
        return _n("call", ln, dest=dest, fn=_temp(m2.group(1), ln), args=args)
    if rhs.startswith("build_list "):
        inner = rhs[11:]
        if not (inner.startswith("[") and inner.endswith("]")):
            raise HSErr("IR: bad build_list", ln)
        inner = inner[1:-1]
        items = [] if inner == "" else [_temp(a.strip(), ln)
                                       for a in _split_top(inner)]
        return _n("build_list", ln, dest=dest, items=items)
    if rhs == "build_dict" or rhs.startswith("build_dict "):
        rest = rhs[10:].strip()
        pairs = []
        if rest != "":
            # pairs are `(temp: temp)` units joined by ") ("; temps never
            # nest, so a flat scan is exact (a ", "-split would not be:
            # the dump joins pairs with a space, not a comma)
            for pm in _re.finditer(r"\(([^()]*): ([^()]*)\)", rest):
                pairs.append((_temp(pm.group(1), ln),
                              _temp(pm.group(2), ln)))
            if " ".join(f"({k}: {v})" for k, v in pairs) != rest:
                raise HSErr("IR: bad build_dict", ln)
        return _n("build_dict", ln, dest=dest, pairs=pairs)
    if rhs.startswith("index "):
        _, o, ix = rhs.split()
        return _n("index", ln, dest=dest, obj=_temp(o, ln), idx=_temp(ix, ln))
    if rhs.startswith("attr "):
        _, o, nm = rhs.split()
        return _n("attr", ln, dest=dest, obj=_temp(o, ln), name=nm)
    if rhs.startswith("slice "):
        _, o, s, e = rhs.split()
        return _n("slice", ln, dest=dest, obj=_temp(o, ln),
                  start=None if s == "-" else _temp(s, ln),
                  stop=None if e == "-" else _temp(e, ln))
    if rhs.startswith("iterseq "):
        return _n("iterseq", ln, dest=dest, src=_temp(rhs[8:], ln))
    if rhs.startswith("phi "):
        rest = rhs[4:]
        arms = []
        for pm in _re.finditer(r"\[([^]]*): (%\d+)\]", rest):
            arms.append((_label(pm.group(1), ln), pm.group(2)))
        if not arms or " ".join(f"[{a}: {t}]" for a, t in arms) != rest:
            raise HSErr("IR: bad phi", ln)
        return _n("phi", ln, dest=dest, arms=arms)
    raise HSErr("IR: bad instruction", ln)


def _temp(s, ln):
    if not _re.match(r"%\d+$", s):
        raise HSErr("IR: bad temp", ln)
    return s


def _label(s, ln):
    if not _LABEL_RE.match(s):
        raise HSErr("IR: bad label", ln)
    return s


# ---------- reference interpreter (must match interp.py) ----------

from interp import disp, wrap_i64, is_num, is_int, tname
from interp import HSBuiltin


class IRFunc:
    def __init__(self, fdef, closure, line):
        self.fdef = fdef
        self.closure = closure
        self.line = line


class IRMod:
    def __init__(self, name, frame, basedir):
        self.name = name
        self.frame = frame
        self.basedir = basedir

    def __repr__(self):
        return f"<module {self.name}>"


_IR_MODS = {}  # abspath -> {"state": "busy"|"done", "mod": IRMod}
_IR_SHELL = {}  # dotted name -> IRMod (empty parent packages)
_BUILTIN_ROOT = None


def _ir_find(name, basedir, ln):
    rel = name.replace(".", "/") + ".hs"
    dirs = [basedir] + [d for d in os.environ.get("HSPATH", "").split(":")
                        if d] + [os.getcwd()]
    for d in dirs:
        if not d:
            continue
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            return os.path.abspath(p)
    raise HSErr(f"cannot find module '{name}'", ln)


def _ir_shell(name):
    m = _IR_SHELL.get(name)
    if m is None:
        f = Frame(parent=_BUILTIN_ROOT, root=None, is_root=True)
        f.basedir = ""
        m = IRMod(name, f, "")
        _IR_SHELL[name] = m
    return m


def _ir_load(name, path, ln):
    ent = _IR_MODS.get(path)
    if ent is not None:
        if ent["state"] == "done":
            return ent["mod"]
        raise HSErr(f"circular import '{name}'", ln)
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        interp.reset_parse_state()
        prog = interp.parse_program(src)
    except HSErr as e:
        raise HSErr(f"in module '{name}': {e.msg}", e.line)
    mod = IRMod(name, None, os.path.dirname(path))
    _IR_MODS[path] = {"state": "busy", "mod": mod}
    try:
        pfx = name + "."
        sub = build_module(prog, pfx)
        verify_module(sub)
        _FUNCS.update(sub["funcs"])
        f = Frame(parent=_BUILTIN_ROOT, root=None, is_root=True,
                  gnames=sub["funcs"][sub["entry"]]["globals"])
        f.basedir = os.path.dirname(path)
        mod.frame = f
        try:
            _exec(sub["funcs"][sub["entry"]], f)
        except _Ret:
            pass  # module body finished (same as falling off the end)
    except HSErr as e:
        del _IR_MODS[path]
        raise HSErr(f"in module '{name}': {e.msg}", e.line)
    _IR_MODS[path] = {"state": "done", "mod": mod}
    return mod


def _ir_import(name, frame, ln):
    # returns (leafmod, topmod, topname); the caller binds topname.
    if "." in name:
        parent, _, leaf = name.rpartition(".")
        try:
            pmod = _ir_import(parent, frame, ln)[0]
        except HSErr as e:
            if f"cannot find module '{parent}'" not in str(e):
                raise
            pmod = _ir_shell(parent)
        path = _ir_find(name, frame.basedir, ln)
        leafmod = _ir_load(name, path, ln)
        pmod.frame.vars[leaf] = leafmod
        topname = name.split(".")[0]
        try:
            topmod = _ir_import(topname, frame, ln)[0]
        except HSErr:
            topmod = _ir_shell(topname)
        return leafmod, topmod, topname
    if name in _IR_SHELL:
        m = _IR_SHELL[name]
        return m, m, name
    path = _ir_find(name, frame.basedir, ln)
    m = _ir_load(name, path, ln)
    return m, m, name


class _Ret(Exception):
    def __init__(self, value):
        self.value = value


class Frame:
    def __init__(self, parent=None, root=None, is_root=False, gnames=(),
                 basedir=""):
        self.vars = {}
        self.parent = parent
        self.root = self if is_root else root
        self.globals = set(gnames)
        self.basedir = basedir or (parent.basedir if parent is not None
                                   else "")

    def get(self, name, line):
        f = self
        while f is not None:
            if name in f.vars:
                return f.vars[name]
            f = f.parent
        raise HSErr(f"unknown variable '{name}'", line)

    def set(self, name, val):
        if name in self.globals:
            self.root.vars[name] = val
        else:
            self.vars[name] = val


def _binop(op, l, r, ln):
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
        return l >> r
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
            raise HSErr(f"operator '{op}' needs numbers, got "
                        f"{tname(l)} and {tname(r)}", ln)
        if op == "-":
            return (float(l) - float(r)) if isinstance(l, float) or \
                isinstance(r, float) else l - r
        if op == "*":
            return (float(l) * float(r)) if isinstance(l, float) or \
                isinstance(r, float) else l * r
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
    raise HSErr(f"IR: bad binop '{op}'", ln)


def _unop(op, v, ln):
    if op == "neg":
        if is_num(v):
            return -v
        raise HSErr(f"cannot negate {tname(v)}", ln)
    if op == "unot":
        if not is_int(v):
            raise HSErr(f"cannot bitwise-not {tname(v)}", ln)
        return wrap_i64(~v)
    if op == "not":
        return not v
    raise HSErr(f"IR: bad unop '{op}'", ln)


def _index(obj, idx, ln):
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
        if not isinstance(idx, str):
            raise HSErr("dict key must be Str", ln)
        if idx not in obj:
            raise HSErr(f"key {idx!r} not found", ln)
        return obj[idx]
    raise HSErr(f"cannot index {tname(obj)}", ln)


def _slice(obj, start, stop, ln):
    lo = start
    if lo is not None and (not isinstance(lo, int) or isinstance(lo, bool)):
        raise HSErr("slice index must be Int", ln)
    hi = stop
    if hi is not None and (not isinstance(hi, int) or isinstance(hi, bool)):
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


def _setindex(obj, idx, val, ln):
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
        if not isinstance(idx, str):
            raise HSErr("dict key must be Str", ln)
        obj[idx] = val
        return
    raise HSErr(f"cannot assign into {tname(obj)}", ln)


def _iterseq(v, ln):
    if isinstance(v, dict):
        return list(v.keys())
    if isinstance(v, (list, str)):
        return v
    raise HSErr(f"not iterable: {tname(v)}", ln)


def _call(fn, args, ln):
    if isinstance(fn, HSBuiltin):
        if fn.name not in IR_BUILTINS:
            raise HSErr(f"IR: builtin '{fn.name}' not in subset", ln)
        return fn.fn(args, ln)
    if isinstance(fn, IRFunc):
        fdef = fn.fdef
        if len(args) != len(fdef["params"]):
            raise HSErr(f"{fdef['dispname']} wants {len(fdef['params'])} "
                        f"args, got {len(args)}", ln)
        fr = Frame(parent=fn.closure, root=fn.closure.root,
                   gnames=fdef["globals"])
        for n, v in zip(fdef["params"], args):
            fr.vars[n] = v
        try:
            _exec(fdef, fr)
        except _Ret as r:
            return r.value
        return None
    raise HSErr(f"not callable: {tname(fn)}", ln)


def _exec(fdef, frame):
    by = {b["label"]: b for b in fdef["blocks"]}
    temps = {}
    lab = fdef["entry"]
    prev = None
    while True:
        b = by[lab]
        for ins in b["instrs"]:
            op = ins["op"]
            ln = ins["line"]
            if op == "const":
                temps[ins["dest"]] = ins["val"]
            elif op == "load":
                temps[ins["dest"]] = frame.get(ins["name"], ln)
            elif op == "stvar":
                frame.set(ins["name"], temps[ins["src"]])
            elif op == "stglobal":
                frame.root.vars[ins["name"]] = temps[ins["src"]]
            elif op == "mkfunc":
                temps[ins["dest"]] = IRFunc(_FUNCS[ins["func"]], frame, ln)
            elif op == "bin":
                temps[ins["dest"]] = _binop(ins["binop"], temps[ins["l"]],
                                            temps[ins["r"]], ln)
            elif op == "un":
                temps[ins["dest"]] = _unop(ins["unop"], temps[ins["v"]],
                                           ln)
            elif op == "call":
                temps[ins["dest"]] = _call(temps[ins["fn"]],
                                          [temps[a] for a in ins["args"]], ln)
            elif op == "print":
                sys.stdout.write(" ".join(
                    disp(temps[a]) for a in ins["args"]) + "\n")
            elif op == "import":
                _leaf, top, topname = _ir_import(ins["name"], frame, ln)
                frame.set(topname, top)
            elif op == "attr":
                obj = temps[ins["obj"]]
                if not isinstance(obj, IRMod):
                    raise HSErr("only modules have attributes", ln)
                nm = ins["name"]
                if nm not in obj.frame.vars:
                    raise HSErr(f"module '{obj.name}' has no attribute "
                                f"'{nm}'", ln)
                temps[ins["dest"]] = obj.frame.vars[nm]
            elif op == "setattr":
                obj = temps[ins["obj"]]
                if not isinstance(obj, IRMod):
                    raise HSErr("only modules have attributes", ln)
                obj.frame.vars[ins["name"]] = temps[ins["val"]]
            elif op == "build_list":
                temps[ins["dest"]] = [temps[x] for x in ins["items"]]
            elif op == "build_dict":
                d = {}
                for k, v in ins["pairs"]:
                    kk = temps[k]
                    if not isinstance(kk, str):
                        raise HSErr("dict key must be Str", ln)
                    d[kk] = temps[v]
                temps[ins["dest"]] = d
            elif op == "index":
                temps[ins["dest"]] = _index(temps[ins["obj"]],
                                            temps[ins["idx"]], ln)
            elif op == "slice":
                temps[ins["dest"]] = _slice(
                    temps[ins["obj"]],
                    temps[ins["start"]] if ins["start"] is not None else None,
                    temps[ins["stop"]] if ins["stop"] is not None else None,
                    ln)
            elif op == "setindex":
                _setindex(temps[ins["obj"]], temps[ins["idx"]],
                          temps[ins["val"]], ln)
            elif op == "iterseq":
                temps[ins["dest"]] = _iterseq(temps[ins["src"]], ln)
            elif op == "phi":
                for al, at in ins["arms"]:
                    if al == prev:
                        temps[ins["dest"]] = temps[at]
                        break
                else:
                    raise HSErr("IR: no phi arm for entry", ln)
            else:
                raise HSErr(f"IR: bad op '{op}'", ln)
        tm = b["term"]
        if tm["term"] == "jmp":
            prev, lab = lab, tm["to"]
        elif tm["term"] == "br":
            prev = lab
            lab = tm["then"] if temps[tm["cond"]] else tm["els"]
        elif tm["term"] == "ret":
            raise _Ret(temps[tm["val"]] if tm["val"] is not None else None)
        else:
            raise HSErr("IR: bad terminator", tm["line"])


_FUNCS = {}


def build_module(prog, pfx=""):
    b = Builder(pfx)
    return b.build(prog, pfx)


def run_module(m, basedir=""):
    global _FUNCS, _BUILTIN_ROOT
    _FUNCS = m["funcs"]
    _IR_MODS.clear()
    _IR_SHELL.clear()
    verify_module(m)
    root = Frame(is_root=True)
    for n, fn in interp.BUILTINS.items():
        root.vars[n] = interp.HSBuiltin(n, fn)
    root.basedir = basedir
    _BUILTIN_ROOT = root
    frame = Frame(parent=root, root=root,
                  gnames=m["funcs"][m["entry"]]["globals"])
    frame.basedir = basedir
    frame.root = frame  # `global` writes to the main frame, like interp's
    # gbase (the builtins env stays reachable as the parent chain)
    main = m["funcs"][m["entry"]]
    try:
        _exec(main, frame)
    except _Ret:
        pass  # top-level return ends the program (interp would traceback;
        # IR defines it as a clean exit — see plan Task 1)
    except RecursionError:
        raise HSErr("recursion too deep", None)


def main(argv):
    if len(argv) < 2:
        print("usage: ir.py prog.hs [args...]", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"error: cannot read {argv[1]}: {e.strerror or e}",
              file=sys.stderr)
        return 1
    try:
        interp.reset_parse_state()
        prog = interp.parse_program(src)
        run_module(build_module(prog),
                   os.path.dirname(os.path.abspath(argv[1])))
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    except RecursionError:
        print("error: recursion too deep", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
