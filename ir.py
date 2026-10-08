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

Subset tonight (Task 1): num/str/var, bin (arith/cmp/bitwise/and/or),
not/neg/unot, call, print, set, def/return, global, if/elif/else,
while/break/continue, pass. Anything else fails fast with
`IR: unsupported '<t>'` so gaps are loud, never silent.

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
IR_BUILTINS = {"len", "str", "int", "float"}


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
    def __init__(self):
        self.funcs = {}
        self.order = []

    def build(self, prog):
        fb = _FuncBuild(self, "<main>", [], "<main>")
        entry = fb.block("entry")
        fb.start(entry)
        self._body(fb, prog)
        if fb.cur is not None:
            fb.end(_t("ret", prog[-1]["line"] if prog else 0, val=None))
        fn = {"name": "<main>", "dispname": "<main>", "params": [],
              "blocks": fb.blocks, "entry": entry["label"],
              "globals": sorted(fb.gnames)}
        self.funcs["<main>"] = fn
        self.order.append("<main>")
        return {"funcs": self.funcs, "order": self.order, "entry": "<main>"}

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
            fb.end(_t("jmp", ln, to=fb.loops[-1]["header"]["label"]))
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
        raise HSErr(f"IR: unsupported '{t}'", ln)

    def _def(self, fb, s):
        ln = s["line"]
        qname = f"{s['name']}$L{ln}"
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
        fb.loops.append({"header": header, "exit": exitb})
        fb.start(bodyb)
        self._body(fb, s["body"])
        if fb.cur is not None:
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
        _verify_func(m["funcs"][name])


def _verify_func(fn):
    labels = [b["label"] for b in fn["blocks"]]
    if len(set(labels)) != len(labels):
        raise HSErr(f"IR: duplicate block label in '{fn['dispname']}'", 0)
    by = {b["label"]: b for b in fn["blocks"]}
    if fn["entry"] not in by:
        raise HSErr(f"IR: missing entry block in '{fn['dispname']}'", 0)
    defs = set()
    for b in fn["blocks"]:
        for ins in b["instrs"]:
            d = ins.get("dest")
            if d is not None:
                if d in defs:
                    raise HSErr(f"IR: temp '{d}' redefined", ins["line"])
                defs.add(d)
    preds = {l: set() for l in labels}
    for b in fn["blocks"]:
        tm = b["term"]
        if tm is None:
            raise HSErr(f"IR: block '{b['label']}' has no terminator",
                        b["instrs"][-1]["line"] if b["instrs"] else 0)
        if tm["term"] == "jmp":
            _need(by, tm["to"], tm)
            preds[tm["to"]].add(b["label"])
        elif tm["term"] == "br":
            _need(by, tm["then"], tm)
            _need(by, tm["els"], tm)
            preds[tm["then"]].add(b["label"])
            preds[tm["els"]].add(b["label"])
            if tm["cond"] not in defs:
                raise HSErr(f"IR: undefined temp '{tm['cond']}'", tm["line"])
        elif tm["term"] == "ret":
            if tm["val"] is not None and tm["val"] not in defs:
                raise HSErr(f"IR: undefined temp '{tm['val']}'", tm["line"])
        else:
            raise HSErr(f"IR: bad terminator '{tm['term']}'", tm["line"])
    for b in fn["blocks"]:
        for ins in b["instrs"]:
            op = ins["op"]
            if op == "phi":
                if b["label"] == fn["entry"]:
                    raise HSErr("IR: phi in entry block", ins["line"])
                if not ins["arms"]:
                    raise HSErr("IR: phi with no arms", ins["line"])
                for al, at in ins["arms"]:
                    if al not in preds[b["label"]]:
                        raise HSErr(
                            f"IR: phi arm from non-predecessor '{al}'",
                            ins["line"])
                    if at not in defs:
                        raise HSErr(f"IR: undefined temp '{at}'", ins["line"])
            elif op in ("const", "load", "mkfunc", "stvar", "stglobal"):
                pass
            elif op == "bin":
                for k in ("l", "r"):
                    if ins[k] not in defs:
                        raise HSErr(f"IR: undefined temp '{ins[k]}'",
                                    ins["line"])
            elif op == "un":
                if ins["v"] not in defs:
                    raise HSErr(f"IR: undefined temp '{ins['v']}'", ins["line"])
            elif op == "call":
                if ins["fn"] not in defs:
                    raise HSErr(f"IR: undefined temp '{ins['fn']}'",
                                ins["line"])
                for a in ins["args"]:
                    if a not in defs:
                        raise HSErr(f"IR: undefined temp '{a}'", ins["line"])
            elif op == "print":
                for a in ins["args"]:
                    if a not in defs:
                        raise HSErr(f"IR: undefined temp '{a}'", ins["line"])
            else:
                raise HSErr(f"IR: bad op '{op}'", ins["line"])


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
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace(
            "\n", "\\n").replace("\t", "\\t") + '"'
    return str(v)


def dump_module(m):
    out = []
    for name in m["order"]:
        fn = m["funcs"][name]
        out.append(f"func {fn['dispname']}({', '.join(fn['params'])}):")
        for b in fn["blocks"]:
            out.append(f"{b['label']}:")
            for ins in b["instrs"]:
                out.append(f"  {dump_instr(ins)}")
            out.append(f"  {dump_term(b['term'])}")
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
        return f"{ins['dest']} = call {ins['fn']}({', '.join(ins['args'])})"
    if op == "print":
        return f"print {', '.join(ins['args'])}"
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


# ---------- reference interpreter (must match interp.py) ----------

from interp import disp, wrap_i64, is_num, is_int, tname
from interp import HSBuiltin


class IRFunc:
    def __init__(self, fdef, closure, line):
        self.fdef = fdef
        self.closure = closure
        self.line = line


class _Ret(Exception):
    def __init__(self, value):
        self.value = value


class Frame:
    def __init__(self, parent=None, root=None, is_root=False, gnames=()):
        self.vars = {}
        self.parent = parent
        self.root = self if is_root else root
        self.globals = set(gnames)

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


def build_module(prog):
    b = Builder()
    return b.build(prog)


def run_module(m, basedir=""):
    global _FUNCS
    _FUNCS = m["funcs"]
    verify_module(m)
    root = Frame(is_root=True)
    for n, fn in interp.BUILTINS.items():
        root.vars[n] = interp.HSBuiltin(n, fn)
    root.basedir = basedir
    frame = Frame(parent=root, root=root,
                  gnames=m["funcs"][m["entry"]]["globals"])
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
