#!/usr/bin/env python3
"""holyshit formatter: parse .hs and re-emit canonical source.

    python3 fmt.py prog.hs        # canonical text to stdout
    python3 fmt.py -w prog.hs     # rewrite in place

Canonical form: 2-space indent, `print x` (no parens), single spaces around
operators, one statement per line, no blank-line preservation, no comments
(the lexer drops comments, so fmt strips them -- documented limitation).
Idempotent: fmt(fmt(x)) == fmt(x).
"""
import sys

import interp
from interp import HSErr

_BIN_PREC = {
    "or": 1, "and": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 4, "-": 4, "*": 5, "/": 5, "%": 5,
}


def _prec(e):
    if e["t"] == "bin":
        return _BIN_PREC[e["op"]]
    if e["t"] == "not":
        return 6
    if e["t"] == "neg":
        return 7
    return 8  # atoms, calls, index, ...


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


def fmt_num(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, float):
        return repr(v)
    return str(v)


def fmt_expr(e):
    t = e["t"]
    if t == "num":
        return fmt_num(e["val"])
    if t == "str":
        return '"' + esc(e["val"]) + '"'
    if t == "var":
        return e["name"]
    if t == "list":
        return "[" + ", ".join(fmt_expr(x) for x in e["items"]) + "]"
    if t == "dict":
        return "{" + ", ".join(f"{fmt_expr(k)}: {fmt_expr(v)}" for k, v in e["pairs"]) + "}"
    if t == "neg":
        return "-" + _atom(e["val"], 7)
    if t == "not":
        return "not " + _atom(e["val"], 6)
    if t == "bin":
        p = _BIN_PREC[e["op"]]
        l = _side(e["l"], p, "l", e["op"])
        r = _side(e["r"], p, "r", e["op"])
        return f"{l} {e['op']} {r}"
    if t == "call":
        return fmt_expr(e["fn"]) + "(" + ", ".join(fmt_expr(a) for a in e["args"]) + ")"
    if t == "index":
        return f"{_atom(e['obj'], 8)}[{fmt_expr(e['idx'])}]"
    if t == "slice":
        s = "" if e["start"] is None else fmt_expr(e["start"])
        p = "" if e["stop"] is None else fmt_expr(e["stop"])
        return f"{_atom(e['obj'], 8)}[{s}:{p}]"
    if t == "attr":
        return f"{_atom(e['obj'], 8)}.{e['name']}"
    if t == "field":
        s = f"{_atom(e['obj'], 8)}.{e['name']}"
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
    if c == parent and side == "r" and op in ("-", "/", "%", "<", ">", "<=", ">="):
        return f"({fmt_expr(e)})"
    return fmt_expr(e)


def fmt_block(body, ind):
    out = []
    for s in body:
        out.extend(fmt_stmt(s, ind))
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
    if t == "setindex":
        return [p + f"{fmt_expr(s['obj'])}[{fmt_expr(s['idx'])}] = " + fmt_expr(s["val"])]
    if t == "setattr":
        return [p + f"{fmt_expr(s['obj'])}.{s['name']} = " + fmt_expr(s["val"])]
    if t == "def":
        out = [p + f"def {s['name']}(" + ", ".join(s["params"]) + "):"]
        out.extend(fmt_block(s["body"], ind + 1))
        return out
    if t == "if":
        out = _suite(f"if {fmt_expr(s['cond'])}:", s["then"], ind)
        for ec, eb in s["elifs"]:
            out.extend(_suite(f"elif {fmt_expr(ec)}:", eb, ind))
        if s["els"]:
            out.extend(_suite("else:", s["els"], ind))
        return out
    if t == "while":
        return _suite(f"while {fmt_expr(s['cond'])}:", s["body"], ind)
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
        prog = interp.parse_program(src)
        out = fmt_program(prog)
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
