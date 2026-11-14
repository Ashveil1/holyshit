"""CPython ast oracle for selfhost/py/pyparse_run.holy.

Walks the CPython 3.11 AST of a Python file and prints the canonical
S-expression dump defined by selfhost/py/pydump.holy's PYDUMP_SCHEMA.
The field mapping mirrors exactly what scripts/py2hs.py consumes.
"""
import ast
import json
import sys


def dump_leaf(v):
    if v is None:
        return "()"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return json.dumps(v)
    return str(v)


def dump_any(v):
    if v is None:
        return "()"
    if isinstance(v, list):
        return "[" + " ".join(dump_any(x) for x in v) + "]"
    if isinstance(v, dict):
        return dump_node(v)
    return dump_leaf(v)


def const_kind(v):
    if isinstance(v, bool):
        return "bool"
    if v is None:
        return "none"
    if isinstance(v, int):
        return "int"
    if isinstance(v, str):
        return "str"
    if isinstance(v, bytes):
        return "bytes"
    if isinstance(v, float):
        return "float"
    if v is Ellipsis:
        return "ellipsis"
    raise AssertionError(type(v))


def const_val(v):
    if isinstance(v, bytes):
        return list(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, int):
        return str(v)
    if v is Ellipsis:
        return None
    return v


def kwlist(kws):
    return [{"t": "keyword", "arg": k.arg, "value": conv(k.value), "line": k.value.lineno}
            for k in kws]


def conv(n):
    if n is None:
        return None
    t = type(n).__name__
    ln = getattr(n, "lineno", 0)
    if t == "Constant":
        return {"t": t, "line": ln, "kind": const_kind(n.value), "v": const_val(n.value)}
    if t == "Name":
        return {"t": t, "line": ln, "id": n.id}
    if t == "Attribute":
        return {"t": t, "line": ln, "value": conv(n.value), "attr": n.attr}
    if t == "Call":
        return {"t": t, "line": ln, "func": conv(n.func),
                "args": [conv(a) for a in n.args], "keywords": kwlist(n.keywords)}
    if t == "UnaryOp":
        return {"t": t, "line": ln, "op": type(n.op).__name__, "operand": conv(n.operand)}
    if t == "BinOp":
        return {"t": t, "line": ln, "op": type(n.op).__name__,
                "l": conv(n.left), "r": conv(n.right)}
    if t == "BoolOp":
        return {"t": t, "line": ln, "op": type(n.op).__name__,
                "values": [conv(v) for v in n.values]}
    if t == "Compare":
        return {"t": t, "line": ln, "left": conv(n.left),
                "ops": [type(o).__name__ for o in n.ops],
                "comparators": [conv(c) for c in n.comparators]}
    if t == "IfExp":
        return {"t": t, "line": ln, "body": conv(n.body),
                "test": conv(n.test), "orelse": conv(n.orelse)}
    if t == "Subscript":
        return {"t": t, "line": ln, "value": conv(n.value), "slice": conv(n.slice)}
    if t == "Slice":
        return {"t": t, "line": ln, "lower": conv(n.lower),
                "upper": conv(n.upper), "step": conv(n.step)}
    if t in ("Tuple", "List", "Set"):
        return {"t": t, "line": ln, "elts": [conv(e) for e in n.elts]}
    if t == "Dict":
        return {"t": t, "line": ln, "keys": [conv(k) for k in n.keys],
                "values": [conv(v) for v in n.values]}
    if t == "JoinedStr":
        return {"t": t, "line": ln, "values": [conv(v) for v in n.values]}
    if t == "FormattedValue":
        spec = None
        if n.format_spec is not None:
            spec = "".join(v.value for v in n.format_spec.values)
        return {"t": t, "line": ln, "value": conv(n.value),
                "spec": spec, "conv": n.conversion}
    if t == "NamedExpr":
        return {"t": t, "line": ln, "target": conv(n.target), "value": conv(n.value)}
    if t == "Lambda":
        args = [a.arg for a in n.args.args]
        nd = len(args) - len(n.args.defaults)
        defaults = [None] * nd + [conv(d) for d in n.args.defaults]
        return {"t": t, "line": ln, "args": args, "defaults": defaults,
                "body": conv(n.body)}
    if t in ("ListComp", "SetComp", "GeneratorExp"):
        return {"t": t, "line": ln, "elt": conv(n.elt),
                "generators": [conv_comp(g) for g in n.generators]}
    if t == "DictComp":
        return {"t": t, "line": ln, "key": conv(n.key), "value": conv(n.value),
                "generators": [conv_comp(g) for g in n.generators]}
    if t in ("Yield", "Await"):
        return {"t": t, "line": ln, "value": conv(n.value)}
    if t == "FunctionDef":
        args = [a.arg for a in n.args.args]
        nd = len(args) - len(n.args.defaults)
        defaults = [None] * nd + [conv(d) for d in n.args.defaults]
        return {"t": t, "line": ln, "name": n.name, "args": args,
                "defaults": defaults, "body": [conv(s) for s in n.body]}
    if t == "ClassDef":
        return {"t": t, "line": ln, "name": n.name,
                "bases": [conv(b) for b in n.bases],
                "body": [conv(s) for s in n.body]}
    if t == "Expr":
        return {"t": t, "line": ln, "value": conv(n.value)}
    if t == "Return":
        return {"t": t, "line": ln, "value": conv(n.value)}
    if t in ("Pass", "Break", "Continue"):
        return {"t": t, "line": ln}
    if t == "Assert":
        return {"t": t, "line": ln, "test": conv(n.test), "msg": conv(n.msg)}
    if t == "Raise":
        return {"t": t, "line": ln, "exc": conv(n.exc)}
    if t == "Delete":
        return {"t": t, "line": ln, "targets": [conv(x) for x in n.targets]}
    if t in ("Import", "ImportFrom"):
        return {"t": "Import", "line": ln}
    if t == "AugAssign":
        return {"t": t, "line": ln, "target": conv(n.target),
                "op": type(n.op).__name__, "value": conv(n.value)}
    if t == "Assign":
        return {"t": t, "line": ln, "targets": [conv(x) for x in n.targets],
                "value": conv(n.value)}
    if t == "If":
        return {"t": t, "line": ln, "test": conv(n.test),
                "body": [conv(s) for s in n.body],
                "orelse": [conv(s) for s in n.orelse]}
    if t == "While":
        return {"t": t, "line": ln, "test": conv(n.test),
                "body": [conv(s) for s in n.body],
                "orelse": [conv(s) for s in n.orelse]}
    if t == "For":
        return {"t": t, "line": ln, "target": conv(n.target),
                "iter": conv(n.iter), "body": [conv(s) for s in n.body],
                "orelse": [conv(s) for s in n.orelse]}
    if t == "Try":
        hs = [{"t": "handler", "line": h.lineno, "name": h.name,
               "body": [conv(s) for s in h.body]} for h in n.handlers]
        return {"t": t, "line": ln, "body": [conv(s) for s in n.body],
                "handlers": hs, "finalbody": [conv(s) for s in n.finalbody]}
    if t == "With":
        items = [{"t": "withitem", "line": n.lineno, "context": conv(w.context_expr),
                  "vars": conv(w.optional_vars)} for w in n.items]
        return {"t": t, "line": ln, "items": items,
                "body": [conv(s) for s in n.body]}
    if t in ("Global", "Nonlocal"):
        return {"t": t, "line": ln}
    raise AssertionError(t)


def conv_comp(g):
    return {"t": "comprehension", "line": g.target.lineno, "target": conv(g.target),
            "iter": conv(g.iter), "ifs": [conv(c) for c in g.ifs]}


# the schema field lists, kept in sync with pydump.holy
import re
SCHEMA = {}


def load_schema():
    src = open(__file__.replace("dump_pyast.py", "pydump.holy")).read()
    for m in re.finditer(r'PYDUMP_SCHEMA\["(\w+)"\] = \[([^\]]*)\]', src):
        SCHEMA[m.group(1)] = re.findall(r'"(\w+)"', m.group(2))


def dump_node(n):
    t = n["t"]
    out = "(" + t + " " + str(n["line"])
    for f in SCHEMA[t]:
        out += " " + dump_any(n.get(f))
    return out + ")"


def main(path):
    load_schema()
    src = open(path, encoding="utf-8", newline="").read()
    tree = ast.parse(src)
    print(dump_any([conv(s) for s in tree.body]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
