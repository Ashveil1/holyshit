#!/usr/bin/env python3
"""Dev-time translator for the emitter modules (gcrt.py style) into hs.
Handles the plain subset those files use: calls, assignments (incl. tuple
unpacking), for-loops, nested defs, returns, simple expressions. The result
is only trusted through the byte-identical differential tests (test_gcrt.py).
usage: py2hs.py in.py out.hs"""
import ast
import sys

ARENA_NAMES = {}


class T:
    def __init__(self):
        self.out = []
        self.alias = {}
        self.n = 0

    def w(self, ind, s):
        self.out.append("  " * ind + s)

    def tmp(self):
        self.n += 1
        return f"_u{self.n}"

    def e(self, x):
        if isinstance(x, ast.Constant):
            v = x.value
            if isinstance(v, str):
                return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
            if v is True:
                return "true"
            if v is False:
                return "false"
            if v is None:
                return "null"
            return str(v)
        if isinstance(x, ast.Name):
            return self.alias.get(x.id, x.id)
        if isinstance(x, ast.Attribute):
            if isinstance(x.value, ast.Name):
                if x.value.id == "a":
                    return "asm." + x.attr
                if x.value.id == "g":
                    return x.attr
            raise ValueError(ast.dump(x))
        if isinstance(x, ast.Call):
            if isinstance(x.func, ast.Attribute) and x.func.attr == "lea_m" \
                    and len(x.args) == 5 and x.func.value.id == "a":
                d, b, disp, ix, sc = [self.e(y) for y in x.args]
                return f"asm.lea_mx({d}, {b}, {ix}, {sc}, {disp})"
            return self.e(x.func) + "(" + ", ".join(self.e(a) for a in x.args) + ")"
        if isinstance(x, ast.UnaryOp) and isinstance(x.op, ast.USub):
            if isinstance(x.operand, ast.Constant):
                return str(-x.operand.value)
            return "(0 - " + self.e(x.operand) + ")"
        if isinstance(x, ast.BinOp):
            op = {ast.Add: "+", ast.Mult: "*", ast.Sub: "-", ast.LShift: "<<"}[type(x.op)]
            return "(" + self.e(x.left) + " " + op + " " + self.e(x.right) + ")"
        if isinstance(x, ast.Tuple) or isinstance(x, ast.List):
            return "[" + ", ".join(self.e(a) for a in x.elts) + "]"
        raise ValueError(ast.dump(x))

    def body(self, stmts, ind):
        for s in stmts:
            self.st(s, ind)

    def st(self, s, ind):
        if isinstance(s, ast.FunctionDef):
            ps = ", ".join(a.arg for a in s.args.args)
            self.w(ind, f"def {s.name}({ps}):")
            self.body(s.body, ind + 1)
            return
        if isinstance(s, ast.Expr):
            if isinstance(s.value, ast.Constant):
                return
            self.w(ind, self.e(s.value))
            return
        if isinstance(s, ast.Return):
            self.w(ind, "return " + (self.e(s.value) if s.value else "null"))
            return
        if isinstance(s, ast.Assign):
            tg = s.targets[0]
            v = s.value
            if isinstance(tg, ast.Name) and isinstance(v, ast.Attribute) \
                    and isinstance(v.value, ast.Name) and v.value.id in ("a", "g"):
                if v.value.id == "a" and v.attr != "a":
                    self.alias[tg.id] = "asm." + v.attr
                elif v.value.id == "g" and v.attr != "a":
                    self.alias[tg.id] = v.attr
                return
            if isinstance(tg, ast.Tuple):
                names = [t.id for t in tg.elts]
                if isinstance(v, ast.GeneratorExp):
                    call = self.e(v.elt)
                    for nm in names:
                        self.w(ind, f"{nm} = {call}")
                elif isinstance(v, ast.Tuple):
                    for nm, el in zip(names, v.elts):
                        self.w(ind, f"{nm} = {self.e(el)}")
                else:
                    raise ValueError("tuple assign")
                return
            self.w(ind, f"{tg.id} = {self.e(v)}")
            return
        if isinstance(s, ast.For):
            it = s.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) \
                    and it.func.id == "range":
                it_s = "range(" + ", ".join(self.e(a) for a in it.args) + ")"
            elif isinstance(it, ast.Call) and it.func.id == "reversed":
                it_s = "reversed(" + self.e(it.args[0]) + ")"
            else:
                it_s = self.e(it)
            tgt = s.target
            if isinstance(tgt, ast.Tuple):
                nm = ", ".join(t.id for t in tgt.elts)
            else:
                nm = tgt.id
            self.w(ind, f"for {nm} in {it_s}:")
            self.body(s.body, ind + 1)
            return
        raise ValueError(type(s).__name__)


def main(src, dst, imports=""):
    tree = ast.parse(open(src).read())
    t = T()
    for s in tree.body:
        if isinstance(s, ast.Expr):
            continue
        if isinstance(s, ast.Assign):
            t.w(0, f"{s.targets[0].id} = {t.e(s.value)}")
            continue
        t.st(s, 0)
        t.w(0, "")
    head = "import asm\n" + imports
    open(dst, "w").write(head + "\n".join(t.out) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
