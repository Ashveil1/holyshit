#!/usr/bin/env python3
"""holyshit formatter: parse .hs and re-emit canonical source.

    python3 fmt.py prog.hs        # canonical text to stdout
    python3 fmt.py -w prog.hs     # rewrite in place

Canonical form: 2-space indent, `print x` (no parens), single spaces around
operators, one statement per line, no blank-line preservation. `fmt_program_c`
keeps comments (full-line ones go before the next statement, trailing ones stay on their line).
Idempotent: fmt(fmt(x)) == fmt(x).
"""
import sys

import interp
from interp import HSErr

_BIN_PREC = {
    "or": 1, "and": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 4, "-": 4,
    "*": 5, "/": 5, "%": 5,
    # bitwise binds tighter than +- and looser than */ (same as interp)
    "<<": 6, ">>": 6, "&": 6, "|": 6, "^": 6,
}


def _prec(e):
    if e["t"] == "var" and e["name"] in _LAM:
        return 0  # a lambda extends as far right as possible: parenthesize as an operand
    if e["t"] == "bin":
        return 9 if e.get("fs") is not None else _BIN_PREC[e["op"]]
    if e["t"] == "not":
        return 3 if e.get("notin") else 7
    if e["t"] == "call" and e.get("inop"):
        return 3
    if e["t"] == "index" and e.get("tern"):
        return 0  # ternary binds loosest: parenthesize as an operand
    if e["t"] == "neg":
        return 8
    if e["t"] == "unot":
        return 8
    return 9  # atoms, calls, index, ...


def esc(s):
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
        elif o < 0x20:
            out.append(f"\\u{o:04x}")
        else:
            out.append(ch)
    return "".join(out)


def fmt_num(v, raw=None):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, float):
        # keep 1.5e3 / .5e1 as written; fall back to repr() otherwise
        return raw if raw else repr(v)
    if raw and isinstance(v, int) and not isinstance(v, bool):
        return raw  # keep 0xAB as written (page-table flags stay readable)
    return str(v)


def fmt_expr(e):
    t = e["t"]
    if t == "num":
        return fmt_num(e["val"], e.get("raw"))
    if t == "str":
        return '"' + esc(e["val"]) + '"'
    if t == "var":
        d = _LAM.get(e["name"])
        if d is not None:
            _reg_lams(d["body"])
            ps = ", ".join(d["params"])
            ret = d["body"][-1]["val"]
            return ("lambda " + ps if ps else "lambda") + ": " + fmt_expr(ret)
        return e["name"]
    if t == "list":
        return "[" + ", ".join(fmt_expr(x) for x in e["items"]) + "]"
    if t == "dict":
        return "{" + ", ".join(f"{fmt_expr(k)}: {fmt_expr(v)}" for k, v in e["pairs"]) + "}"
    if t == "neg":
        return "-" + _atom(e["val"], 8)
    if t == "not" and e.get("notin"):
        c = e["val"]
        l = _side(c["args"][1], 3, "l", "in")
        r = _side(c["args"][0], 3, "r", "in")
        return f"{l} not in {r}"
    if t == "not":
        return "not " + _atom(e["val"], 7)
    if t == "unot":
        return "~" + _atom(e["val"], 8)
    if t == "bin" and e.get("fs") is not None:
        out = []
        for q in e["fs"]:
            if isinstance(q, str):
                out.append(esc(q).replace("{", "{{").replace("}", "}}"))
            else:
                out.append("{" + fmt_expr(q) + "}")
        return 'f"' + "".join(out) + '"'
    if t == "bin":
        p = _BIN_PREC[e["op"]]
        l = _side(e["l"], p, "l", e["op"])
        r = _side(e["r"], p, "r", e["op"])
        return f"{l} {e['op']} {r}"
    if t == "call" and e.get("lc"):
        _reg_lams(e["hl"])
        c = e.get("c")
        return ("[" + fmt_expr(e["e"]) + " for " + e["x"] + " in "
                + fmt_expr(e["it"]) + ("" if c is None else " if " + fmt_expr(c))
                + "]")
    if t == "call" and e.get("inop"):
        l = _side(e["args"][1], 3, "l", "in")
        r = _side(e["args"][0], 3, "r", "in")
        return f"{l} in {r}"
    if t == "call" and e.get("mcall"):
        return (fmt_expr(e["fn"]) + "(" +
                ", ".join(fmt_expr(a) for a in e["args"][1:]) + ")")
    if t == "call" and e.get("method"):
        # method sugar: keep the receiver.name(args) spelling
        return (_atom(e["args"][0], 9) + "." + e["method"] + "(" +
                ", ".join(fmt_expr(a) for a in e["args"][1:]) + ")")
    if t == "call":
        return _atom(e["fn"], 9) + "(" + ", ".join(fmt_expr(a) for a in e["args"]) + ")"
    if t == "index" and e.get("tern"):
        return (f"{_atom(e['a'], 1)} if {_atom(e['c'], 1)} else "
                f"{fmt_expr(e['b'])}")
    if t == "index" and e.get("dot") is not None:
        return f"{_atom(e['obj'], 9)}.{e['dot']}"
    if t == "index":
        return f"{_atom(e['obj'], 9)}[{fmt_expr(e['idx'])}]"
    if t == "slice":
        s = "" if e["start"] is None else fmt_expr(e["start"])
        p = "" if e["stop"] is None else fmt_expr(e["stop"])
        return f"{_atom(e['obj'], 9)}[{s}:{p}]"
    if t == "attr":
        return f"{_atom(e['obj'], 9)}.{e['name']}"
    if t == "field":
        s = f"{_atom(e['obj'], 9)}.{e['name']}"
        if e["idx"] is not None:
            s += f"[{fmt_expr(e['idx'])}]"
        return s
    if t == "deref":
        return "*" + _atom(e["val"], 7)
    if t == "sizeof":
        return f"sizeof({e['stype']})"
    raise HSErr(f"fmt: bad expr {t}", e.get("line"))


def _atom(e, level):
    s = fmt_expr(e)
    if _prec(e) < level:
        return f"({s})"
    return s


def _side(e, parent, side, op):
    c = _prec(e)
    if c < parent:
        return f"({fmt_expr(e)})"
    # right operand at equal precedence: only + and * are safe to flatten
    # (a & (b | c) must keep its parens, as must a - (b - c))
    if c == parent and side == "r" and op not in ("+", "*"):
        return f"({fmt_expr(e)})"
    return fmt_expr(e)


_LAM = {}  # parse-time lambda defs (name -> def node), re-inlined on print


def _reg_lams(body):
    for s in body:
        if s["t"] == "def" and s.get("lam"):
            _LAM[s["name"]] = s


_CMT = None  # comment state while formatting with comments (see fmt_program_c)


def _flush_comments(out, upto, ind):
    """Emit pending full-line comments that start before source line `upto`."""
    while _CMT["full"] and (upto is None or _CMT["full"][0][0] < upto):
        _, text = _CMT["full"].pop(0)
        out.append(("  " * ind) + text)


def fmt_block(body, ind):
    out = []
    _reg_lams(body)
    for s in body:
        if s["t"] == "def" and (s.get("lam") or s.get("clsmember")):
            continue  # lambda: printed where used; method: printed by its class
        if _CMT is not None and s.get("line"):
            _flush_comments(out, s["line"], ind)
        lines = fmt_stmt(s, ind)
        if _CMT is not None and s.get("line") and lines:
            tr = _CMT["trail"].pop(s["line"], None)
            if tr:
                lines[0] = lines[0] + "  " + tr
        out.extend(lines)
    return out


def _suite(head, body, ind):
    out = [("  " * ind) + head]
    out.extend(fmt_block(body, ind + 1))
    return out


def fmt_stmt(s, ind):
    t = s["t"]
    p = "  " * ind
    if t == "pass":
        return [p + "pass"]
    if t == "break":
        return [p + "break"]
    if t == "continue":
        return [p + "continue"]
    if t == "expr":
        return [p + fmt_expr(s["val"])]
    if t == "print":
        if not s["args"]:
            return [p + "print"]
        # an arg starting with '(' would be eaten as print-parens: wrap it
        parts = []
        for a in s["args"]:
            f = fmt_expr(a)
            if f.startswith("("):
                f = f"({f})"
            parts.append(f)
        return [p + "print " + ", ".join(parts)]
    if t == "return":
        if s["val"] is None:
            return [p + "return"]
        return [p + "return " + fmt_expr(s["val"])]
    if t == "raise":
        if s["val"] is None:
            return [p + "raise"]
        return [p + "raise " + fmt_expr(s["val"])]
    if t == "global":
        return [p + "global " + ", ".join(s["names"])]
    if t == "import":
        return [p + "import " + s["name"]]
    if t == "set":
        return [p + f"{s['name']} = " + fmt_expr(s["val"])]
    if t == "setindex" and s.get("dot") is not None:
        return [p + f"{fmt_expr(s['obj'])}.{s['dot']} = " + fmt_expr(s["val"])]
    if t == "setindex":
        return [p + f"{fmt_expr(s['obj'])}[{fmt_expr(s['idx'])}] = " + fmt_expr(s["val"])]
    if t == "setattr":
        return [p + f"{fmt_expr(s['obj'])}.{s['name']} = " + fmt_expr(s["val"])]
    if t == "def" and s.get("cls"):
        out = [p + f"class {s['cls']}" + (f"({s['base']})" if s.get("base") else "") + ":"]
        for i, m in enumerate(s["methods"]):
            out.extend(fmt_stmt(dict(m, name=m["orig"], clsmember=False), ind + 1))
        if not s["methods"]:
            out.append(p + "  pass")
        return out
    if t == "def":
        ps = list(s["params"])
        dfl = s.get("defaults", [])
        for i, e in enumerate(dfl):
            j = len(ps) - len(dfl) + i
            ps[j] = ps[j] + "=" + fmt_expr(e)
        out = [p + f"def {s['name']}(" + ", ".join(ps) + "):"]
        out.extend(fmt_block(s["body"], ind + 1))
        return out
    if t == "if" and s.get("asrt"):
        m = s.get("m")
        return [p + "assert " + fmt_expr(s["c"])
                + ("" if m is None else ", " + fmt_expr(m))]
    if t == "if":
        out = _suite(f"if {fmt_expr(s['cond'])}:", s["then"], ind)
        for ec, eb in s["elifs"]:
            out.extend(_suite(f"elif {fmt_expr(ec)}:", eb, ind))
        if s["els"]:
            out.extend(_suite("else:", s["els"], ind))
        return out
    if t == "while":
        return _suite(f"while {fmt_expr(s['cond'])}:", s["body"], ind)
    if t == "for" and s.get("tup"):
        return _suite(f"for {', '.join(s['tup'])} in {fmt_expr(s['iter'])}:",
                      s["body"][len(s["tup"]):], ind)
    if t == "for":
        return _suite(f"for {s['var']} in {fmt_expr(s['iter'])}:", s["body"], ind)
    if t == "try":
        out = _suite("try:", s["body"], ind)
        if s.get("ebody") is not None:
            head = "except:" if s["ename"] is None else f"except as {s['ename']}:"
            out.extend(_suite(head, s["ebody"], ind))
        if s.get("fbody") is not None:
            out.extend(_suite("finally:", s["fbody"], ind))
        return out
    if t == "extern":
        head = "extern:"
        if s["lib"] is not None:
            head = f'extern from "{esc(s["lib"])}":'
        out = [p + head]
        for d in s["decls"]:
            params = ", ".join(f"{ft} {pn}" for pn, ft in d["params"])
            out.append("  " * (ind + 1) + f"{d['rtype']} {d['name']}({params})")
        return out
    if t == "unsafe":
        out = [p + "unsafe:"]
        out.extend(fmt_block(s["body"], ind + 1))
        return out
    if t == "struct":
        L = interp.HS_STRUCTS.get(s["name"], {"fields": {}, "size": 0})
        out = [p + f"struct {s['name']}:"]
        for fname in sorted(L["fields"], key=lambda k: L["fields"][k][1]):
            ft, _off, count = L["fields"][fname]
            if ft.startswith("Ptr:"):
                decl = f"{ft[4:]}* {fname}"
            else:
                decl = f"{ft} {fname}"
            if count > 1:
                decl += f"[{count}]"
            out.append("  " * (ind + 1) + decl)
        return out
    if t == "udecl":
        ut = s["utype"]
        if ut.startswith("Ptr:"):
            head = ut[4:] + "*"
        else:
            head = ut
        if s["init"] is not None:
            return [p + f"{head} {s['name']} = " + fmt_uexpr(s["init"])]
        return [p + f"{head} {s['name']}"]
    if t == "store":
        return [p + f"*{fmt_expr(s['ptr'])} = " + fmt_uexpr(s["val"])]
    if t == "fstore":
        base = f"{fmt_expr(s['obj'])}.{s['name']}"
        if s["idx"] is not None:
            base += f"[{fmt_uexpr(s['idx'])}]"
        return [p + base + " = " + fmt_uexpr(s["val"])]
    raise HSErr(f"fmt: bad stmt {t}", s.get("line"))


def fmt_uexpr(e):
    # unsafe expressions share the printer (field/sizeof/deref handled above)
    return fmt_expr(e)


def fmt_program(prog):
    return "\n".join(fmt_block(prog, 0)) + "\n"


def extract_comments(src):
    """Return (full, trail): full-line comments [(line, text)] in order and
    trailing comments {line: text}. String-aware, 1-based lines."""
    full, trail = [], {}
    for ln, raw in enumerate(src.split("\n"), 1):
        in_str = False
        i = 0
        n = len(raw)
        while i < n:
            c = raw[i]
            if in_str:
                if c == "\\" and i + 1 < n:
                    i += 2
                    continue
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "#" or (c == "/" and i + 1 < n and raw[i + 1] == "/"):
                text = raw[i:].rstrip()
                if raw[:i].strip():
                    trail[ln] = text
                else:
                    full.append((ln, text))
                break
            i += 1
    return full, trail


def fmt_program_c(prog, src):
    """Like fmt_program but keeps comments: a full-line comment goes before the
    next statement (at its indent), a trailing comment stays on its statement's
    first line, leftovers go at the end. Blank lines are still dropped."""
    global _CMT
    full, trail = extract_comments(src)
    _CMT = {"full": full, "trail": trail}
    try:
        lines = fmt_block(prog, 0)
        _flush_comments(lines, None, 0)
        # trailing comments whose line did not start a statement: keep them
        for ln in sorted(_CMT["trail"]):
            lines.append(_CMT["trail"][ln])
    finally:
        _CMT = None
    return "\n".join(lines) + "\n"


def strip_comments(src):
    """Blank out `#` and `//` comments (string-aware), keeping line structure.

    The lexer drops comments, so the printer cannot reproduce them. This lets
    `--check` compare structure only instead of failing on every comment.
    """
    out = []
    i = 0
    n = len(src)
    in_str = False
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "#" or (c == "/" and i + 1 < n and src[i + 1] == "/"):
            while i < n and src[i] != "\n":
                out.append(" ")
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def squash(text):
    """Canonical comparison form: comments and blank lines do not count."""
    return "\n".join(ln.rstrip() for ln in text.split("\n") if ln.strip()) + "\n"


def is_canonical(src, out):
    """Would formatting change anything meaningful? (comments/blanks ignored)"""
    return squash(strip_comments(src)) == squash(out)


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print("usage: fmt.py prog.hs [-w]", file=sys.stderr)
        return 2
    write = "-w" in argv
    path = argv[1] if argv[1] != "-w" else argv[2]
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        interp.reset_parse_state()
        prog = interp.parse_program(src, raw=True)
        out = fmt_program_c(prog, src)
    except HSErr as e:
        print(str(e), file=sys.stderr)
        return 1
    if write:
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
