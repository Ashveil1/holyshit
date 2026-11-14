#!/usr/bin/env python3
"""Generate tests/py2hs_corpus goldens via scripts/py2hs.py (trusted oracle).

Each entry: name -> ("ok", source) producing <name>.py + <name>.holy,
or ("fail", source, diagnostic) producing <name>.py + <name>.fail.
Idempotent: rewrites the whole corpus directory from scratch.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import py2hs

CORPUS = os.path.join(ROOT, "tests", "py2hs_corpus")
ASM = os.path.join(ROOT, "x64.py")

CASES = {
    # ---- constants ----
    "const_int": ("ok", "a = 0\nb = 42\nc = 0x1f\nd = 0o17\ne = 0b101\nf = 1_000_000\ng = -7\n"),
    "const_int_wide": ("ok", "a = 9223372036854775807\nb = 0xFFFFFFFFFFFFFFFF\nc = 18446744073709551615\n"),
    "const_str": ("ok", 'a = "hi"\nb = "a\\nb\\tc\\"d\\\\e"\nc = "x" + "y"\n'),
    "const_str_ctrl": ("ok", 'a = "pre\\x01post"\nb = "del\\x7f"\n'),
    "const_str_triple": ("ok", 'a = """line1\nline2"""\n'),
    "const_bytes": ("ok", 'a = b"\\x00\\x01ABC"\nb = b""\n'),
    "const_none_bool": ("ok", "a = None\nb = True\nc = False\n"),
    # ---- collection literals ----
    "lit_collections": ("ok", "a = [1, 2, 3]\nb = (1, 2)\nc = {1, 2}\nd = {\"k\": 1, 2: \"v\"}\ne = []\nf = {}\ng = ()\n"),
    "lit_dict_tuple_key": ("ok", "d = {(1, 2): \"x\"}\nd[(3, 4)] = \"y\"\nv = d[(1, 2)]\n"),
    # ---- operators ----
    "binops": ("ok", "a = 1 + 2\nb = 3 - 4\nc = 5 * 6\nd = 7 & 8\ne = 9 | 10\nf = 11 ^ 12\ng = 13 << 2\nh = 14 >> 1\ni = 15 // 4\nj = 16 % 5\nk = 2 ** 8\n"),
    "binop_seqmul": ("ok", 'a = [0] * 4\nb = "ab" * 3\nc = b"\\x00" * 8\n'),
    "binop_setunion": ("ok", "a = {1} | {2}\n"),
    "binop_mask64": ("ok", "a = x & 0xFFFFFFFFFFFFFFFF\n"),
    "unary": ("ok", "a = -x\nb = ~y\nc = not z\nd = +w\ne = -5\n"),
    "boolop": ("ok", "a = x and y\nb = x or y or z\nc = (x and y) or z\n"),
    "compare": ("ok", "a = x == y\nb = x != y\nc = x < y <= z\nd = x in y\ne = x not in y\nf = x is y\ng = x is not y\n"),
    "compare_is_bool": ("ok", "a = x is True\nb = y is not False\n"),
    "ifexp": ("ok", "a = 1 if x else 2\n"),
    # ---- subscripts / slices ----
    "subscript": ("ok", "a = xs[0]\nb = xs[i]\nxs[1] = 9\nd[\"k\"] = v\n"),
    "slice_forms": ("ok", "a = xs[1:2]\nb = xs[:3]\nc = xs[4:]\nd = xs[:]\n"),
    # ---- calls / attributes ----
    "call_simple": ("ok", "def f(a, b):\n    return a\nr = f(1, 2)\n"),
    "call_kwargs": ("ok", "def f(a, b, c):\n    return b\nr = f(1, c=3, b=2)\n"),
    "call_kwargs_skip": ("ok", "def f(a, b, c):\n    return a\nr = f(1, c=9)\n"),
    "call_method": ("ok", "class C:\n    def m(self, a, b):\n        return a\nc = C()\nr = c.m(1, 2)\n"),
    "attr_chain": ("ok", "a = x.y.z\nb = x.y()\n"),
    "lambda_": ("ok", "f = lambda a, b: a + b\n"),
    "print_": ("ok", 'def f(x):\n    print("hi", x)\n'),
    # ---- builtins mapping ----
    "funcs_map": ("ok", "a = sorted(d.items())\nb = enumerate(xs)\nc = reversed(xs)\nd = all(xs)\ne = any(xs)\nf = min(1, 2)\ng = max(1, 2)\nh = abs(x)\ni = list(xs)\nj = hex(x)\nk = ord(c)\nl = chr(n)\nm = dict()\nn = sum(xs)\no = zip(a, b)\np = map(f, xs)\n"),
    "funcs_isinstance": ("ok", "a = isinstance(x, int)\nb = isinstance(y, (str, list))\n"),
    "methods_map": ("ok", 'a = d.get("k")\nb = d.get("k", 0)\nc = d.setdefault("k", 1)\nd = d.items()\ne = s.add(x)\nf = d.update(o)\ng = xs.extend(ys)\nh = xs.pop()\ni = s.startswith("a")\nj = s.endswith("b")\nk = s.replace("a", "b")\nl = b.decode("utf-8")\nm = s.encode("utf-8")\nn = xs.index(v)\no = s.discard(x)\np = d.copy()\nq = xs.insert(0, v)\nr = s.strip()\ns = s.lower()\nt = s.upper()\nu = s.count("x")\nv = xs.sort()\nw = xs.remove(v)\nx = s.isdigit()\ny = s.format(a)\n'),
    "methods_split_join_find": ("ok", 'a = s.split(",")\nb = s.split()\nc = ",".join(xs)\nd = s.find("x")\ne = s.rfind("x")\nf = s.rsplit(",")\n'),
    "modfuncs": ("ok", "import struct\na = struct.pack(\"<I\", 1)\nb = struct.unpack(\"<I\", d)\n"),
    # ---- comprehensions ----
    "comp_forms": ("ok", "a = [x for x in xs]\nb = [x for x in xs if x]\nc = {x for x in xs}\nd = {x: x for x in xs}\ne = (x for x in xs)\nf = [k for k, v in d.items()]\n"),
    # ---- f-strings ----
    "fstring": ("ok", 'a = f"x={x}"\nb = f"{x!r}"\nc = f"{x:03d}"\nd = f"pre {a} mid {b} post"\n'),
    "namedexpr": ("ok", "if (n := len(xs)) > 0:\n    b = n\n"),
    # ---- statements ----
    "assign_multi": ("ok", "a = b = 1\n"),
    "assign_tuple_unpack": ("ok", "def f():\n    x, y = 2, 3\n    p, q = pair\n"),
    "augassign": ("ok", "a += 1\nb -= 2\nc *= 3\nd &= 4\ne |= 5\nf ^= 6\ng <<= 1\nh >>= 1\ni //= 2\nj %= 3\n"),
    "if_elif_else": ("ok", "if x:\n    a = 1\nelif y:\n    a = 2\nelif z:\n    a = 3\nelse:\n    a = 4\n"),
    "while_loop": ("ok", "while x:\n    break\nwhile y:\n    continue\n"),
    "for_forms": ("ok", "for i in range(10):\n    a = i\nfor x in xs:\n    b = x\nfor k, v in d.items():\n    c = k\n"),
    "try_forms": ("ok", "try:\n    a = 1\nexcept Exception as e:\n    b = 2\n"),
    "try_finally": ("ok", "try:\n    a = 1\nexcept Exception as e:\n    b = 2\nfinally:\n    c = 3\n"),
    "with_open": ("ok", 'with open("f") as fh:\n    data = fh.read()\n'),
    "raise_forms": ("ok", "def f():\n    raise \"boom\"\ndef g():\n    try:\n        f()\n    except Exception as e:\n        raise\n"),
    "assert_": ("ok", "assert x > 0\n"),
    "del_item": ("ok", "del d[\"k\"]\n"),
    "pop_discard_stmt": ("ok", "def f(xs, d, s, x):\n    xs.pop()\n    d.pop(\"k\", None)\n    s.discard(x)\n"),
    "return_forms": ("ok", "def f():\n    return\ndef g():\n    return 1\n"),
    "docstring_skip": ("ok", 'def f():\n    """doc"""\n    return 1\n'),
    # ---- defs / classes ----
    "def_defaults": ("ok", "def f(a, b=2, c=3):\n    return a\nr = f(1)\ns = f(1, 5)\n"),
    "class_basic": ("ok", "class C:\n    K = 5\n    def m(self):\n        return self.K\n"),
    "class_nested": ("ok", "class Outer:\n    class Inner:\n        def m(self):\n            return 1\n"),
    "class_inherit": ("ok", "class B:\n    def m(self):\n        return 1\nclass D(B):\n    def n(self):\n        return 2\n"),
    "class_init_call": ("ok", "class C:\n    def __init__(self, a):\n        self.a = a\nc = C(1)\n"),
    "import_drop": ("ok", "import os\nfrom sys import path\na = 1\n"),
    "main_guard_drop": ("ok", "a = 1\nif __name__ == \"__main__\":\n    main()\n"),
    # ---- name handling ----
    "name_mangle": ("ok", "def f(len_, print_):\n    range_ = len_\n    return range_\n"),
    # ---- rejects ----
    "fail_comp_multi_gen": ("fail", "bad = [x for x in xs for y in ys]\ngood = 7\n", "multiple comprehension generators"),
    "fail_comp_multi_filter": ("fail", "bad = [x for x in xs if x if x > 1]\ngood = 7\n", "multiple comprehension filters"),
    "fail_comp_async": ("fail", "bad = [x async for x in xs]\ngood = 7\n", "async comprehension"),
    "fail_slice_step": ("fail", "bad = xs[::-1]\ngood = 7\n", "slice step"),
    "fail_dict_starstar": ("fail", "bad = {**a}\ngood = 7\n", "dict **"),
    "for_deep_target": ("ok", "for a, (b, c) in xs:\n    good = 7\n"),
    "fail_deep_for_target": ("fail", "for a, (b, (c, d)) in xs:\n    z = 1\ngood = 7\n", "deep for target"),
    "fail_yield": ("fail", "def bad():\n    yield 1\ngood = 7\n", "Yield|unsupported|unsupported"),
    "fail_global": ("fail", "def bad():\n    global x\ngood = 7\n", "Global|unsupported"),
    "fail_unsupported_expr": ("fail", "bad = await x\ngood = 7\n", "Await|unsupported"),
}


def main():
    if os.path.isdir(CORPUS):
        shutil.rmtree(CORPUS)
    os.makedirs(CORPUS)
    ok = fail = 0
    for name in sorted(CASES):
        kind, src = CASES[name][0], CASES[name][1]
        inp = os.path.join(CORPUS, name + ".py")
        out = os.path.join(CORPUS, name + ".holy")
        open(inp, "w").write(src)
        errs = py2hs.translate([inp], out, ASM)
        text = open(out).read() if os.path.exists(out) else ""
        if kind == "ok":
            assert not errs, (name, errs)
            assert text.strip(), name
            ok += 1
        else:
            diag = CASES[name][2]
            assert errs, (name, "expected failure")
            assert any(any(part in e for part in diag.split("|")) for e in errs), (name, errs, diag)
            open(os.path.join(CORPUS, name + ".fail"), "w").write(errs[0].split(" ", 1)[1] + "\n")
            os.remove(out)
            fail += 1
    print("ok=%d fail=%d" % (ok, fail))


if __name__ == "__main__":
    main()
