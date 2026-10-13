"""IR optimizer (v0.7): constant folding + dead-const removal.

Runs on the flat CFG from ir.build_module. Temps are single-assignment, so a
temp defined by `const` is a known constant everywhere it is used. Only
operations whose result is the same on every backend are folded: plain Int
(not Bool/Float) + - * and comparisons, with the result well inside the 62-bit
tagged range (x64 Ints are 62-bit, interp's are 64-bit; folding never
changes which side of that line a program lands on). Anything that could
raise (division, shifts, type errors) is left for run time. Disable with
HS_NOOPT=1 (differential tests run both ways).
"""

import os

LIM = 1 << 60


def _isint(v):
    return type(v) is int


def _fold(op, a, b):
    if op == "+":
        r = a + b
    elif op == "-":
        r = a - b
    elif op == "*":
        r = a * b
    elif op == "<":
        return a < b
    elif op == ">":
        return a > b
    elif op == "<=":
        return a <= b
    elif op == ">=":
        return a >= b
    elif op == "==":
        return a == b
    elif op == "!=":
        return a != b
    else:
        return None
    return r if -LIM < r < LIM else None


def _walk(v, out):
    if isinstance(v, str):
        if v.startswith("%"):
            out.add(v)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _walk(x, out)
    elif isinstance(v, dict):
        for x in v.values():
            _walk(x, out)


def _uses(ins, out):
    for k, v in ins.items():
        if k != "dest":
            _walk(v, out)


def optimize_func(fn):
    consts = {}
    n_fold = 0
    for b in fn["blocks"]:
        for ins in b["instrs"]:
            if ins["op"] == "const":
                consts[ins["dest"]] = ins["val"]
            elif ins["op"] == "bin":
                l, r = consts.get(ins["l"]), consts.get(ins["r"])
                if ins["l"] in consts and ins["r"] in consts and \
                        _isint(l) and _isint(r):
                    v = _fold(ins["binop"], l, r)
                    if v is not None:
                        d = ins["dest"]
                        line = ins["line"]
                        ins.clear()
                        ins.update({"op": "const", "line": line, "dest": d,
                                    "val": v})
                        consts[d] = v
                        n_fold += 1
    # drop consts nobody reads (loop: a dropped const can free another)
    while True:
        used = set()
        for b in fn["blocks"]:
            for ins in b["instrs"]:
                _uses(ins, used)
            tm = b["term"]
            if tm is not None:
                _uses(tm, used)
        dropped = 0
        for b in fn["blocks"]:
            keep = []
            for ins in b["instrs"]:
                if ins["op"] == "const" and ins["dest"] not in used:
                    dropped += 1
                else:
                    keep.append(ins)
            b["instrs"] = keep
        if not dropped:
            break
    return n_fold


def optimize_module(m):
    if os.environ.get("HS_NOOPT"):
        return 0
    total = 0
    for fn in m["funcs"].values():
        total += optimize_func(fn)
    return total
