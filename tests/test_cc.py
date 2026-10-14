#!/usr/bin/env python3
"""selfhost/cc.hs: the compiler written in hs emits a static x86-64 ELF.
Each program is run through the reference interpreter and through the
compiled ELF; stdout must match. Programs outside the subset must be a
compile error (never silently different output)."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HS = os.path.join(ROOT, "hs.py")
CC = os.path.join(ROOT, "selfhost", "cc.hs")
total = fails = 0

PROGS = {
    "ternary": 'def f(n):\n  return "big" if n > 5 else "small"\n\ndef g(n):\n  return n * 2 if n > 0 else (0 - n if n < 0 else 99)\n\nx = 3\nprint f(x), f(9)\nprint g(4), g(0 - 3), g(0)\nprint 1 if false else 2\nprint (x if x else 7)\n',
    "defaults": 'K = 5\n\ndef f(a, b=10, c=K + 1):\n  return a * 100 + b * 10 + c\n\ndef g(s, sep=", "):\n  return s + sep + s\n\nprint f(1), f(1, 2), f(1, 2, 3)\nprint g("x"), g("x", "-")\n',
    "prelude": 'xs = [5, 3, 9, 1, 7, 3]\nprint abs(0 - 4), abs(6), min(xs), max(xs), sum(xs), min(2, 1), max(2, 8)\nprint sorted(xs), reversed(xs), enumerate([7, 8])\nprint upper("hello World"), lower("HeLLo")\nfor p in enumerate(["a", "b"]):\n  print p[0], p[1]\n',
    "prelude_user": 'def max(a, b):\n  return a * 100 + b\n\ndef abs(x):\n  return 7\n\nprint max(1, 2), abs(0 - 5), min(4, 2), sum([1, 2])\n',
    "bnot_split1": 'print 6 | 3\nprint 6 ^ 3\nprint ~0\nprint ~6\nx = 5\nprint ~x, ~(0 - 3)\nprint split("a b  c")\nprint split("  lead\\ttab\\nnl  "), split("")\nprint split("a,b,", ",")\n',
    "join": 'print join(",", ["a", "b", "c"])\nprint join("", [])\nprint join("--", ["x"])\nparts = []\nfor i in range(4):\n  append(parts, str(i * i))\nprint join(" ", parts)\ndef join2(a, b):\n  return join("+", [a, b])\nprint join2("p", "q")\n',
    "closure_cap": "def make(k):\n  def add(x):\n    return x + k\n  return add\nf = make(10)\ng = make(100)\nprint f(5), g(5)\ndef two(a, b):\n  def inner(c):\n    def deep(d):\n      return a * 1000 + b * 100 + c * 10 + d\n    return deep\n  return inner\nprint two(1, 2)(3)(4)\ndef fact_outer(n):\n  def fact(m):\n    if m <= 1:\n      return 1\n    return m * fact(m - 1)\n  return fact(n)\nprint fact_outer(6)\n",
    "lambda_hof": "sq = lambda x: x * x\nprint sq(7)\ndef apply(f, v):\n  return f(v)\nprint apply(lambda n: n + 100, 5)\ndef add_k(k):\n  return lambda x: x + k\nprint add_k(3)(4)\ndef sq2(x):\n  return x * x\nh = sq2\nprint apply(h, 9)\nfs = []\ni = 0\nwhile i < 3:\n  append(fs, lambda z: z + 1)\n  i = i + 1\nprint fs[2](41), len(fs)\n",
    "listcomp": "def f(n):\n  return [x * x for x in range(n) if x % 2 == 0]\nprint f(9)\nk = 3\nprint [x + k for x in [1, 2, 3]]\n",
    "builtin_values": "d = {\"a\": 1}\nf = has\nprint f(d, \"a\"), f(d, \"b\")\ng = keys\nprint g(d)\nh = len\nprint h([1, 2, 3])\ndef apply(fn, x):\n  return fn(x)\nprint apply(len, \"abcd\")\n",
    "fib": "def fib(n):\n  if n < 2:\n    return n\n  return fib(n - 1) + fib(n - 2)\nprint fib(22)\n",
    "arith": "a = 17\nb = 5\nprint a + b, a - b, a * b, a % b, -a % b, a % -b, -a % -b\n"
             "print 0, -1, 4611686018427387903, -4611686018427387903\n",
    "bits": "x = 0xF0F0\nprint x & 255, x | 15, x ^ 255, x << 4, x >> 4, -256 >> 4\n",
    "loop": "i = 0\nt = 0\nwhile i < 1000:\n  t = t + i * i % 7\n  i = i + 1\nprint t\n",
    "breakcont": "i = 0\nt = 0\nwhile 1 == 1:\n  i = i + 1\n  if i % 2 == 0:\n    continue\n"
                 "  if i > 21:\n    break\n  t = t + i\nprint t, i\n",
    "elif": "def sign(n):\n  if n < 0:\n    return -1\n  elif n == 0:\n    return 0\n  else:\n    return 1\n"
            "print sign(-5), sign(0), sign(9)\n",
    "args": "def f(a, b, c, d):\n  return a * 1000 + b * 100 + c * 10 + d\nprint f(1, 2, 3, 4)\n",
    "globals": "k = 10\ndef add(x):\n  return x + k\nk = 32\nprint add(1)\n",
    "locals": "def g(n):\n  s = 0\n  i = 0\n  while i < n:\n    s = s + i\n    i = i + 1\n  return s\n"
              "i = 99\nprint g(10), i\n",
    "strings": 'print "hello, world"\nprint "a", 1, "b"\nprint ""\nprint "tab\\there"\n',
    "andor": "a = 3\nb = 4\nif a < b and b < 10 or a == 0:\n  print 1\nif not (a < b):\n  print 2\n"
             "else:\n  print 3\n",
    "deep": "def s(n):\n  if n == 0:\n    return 0\n  return n + s(n - 1)\nprint s(1000)\n",
    "mutual": "def ev(n):\n  if n == 0:\n    return 1\n  return od(n - 1)\ndef od(n):\n  if n == 0:\n    return 0\n"
              "  return ev(n - 1)\nprint ev(10), od(7), ev(7)\n",
    "bools": "x = 1 < 2\nprint x, 1 > 2, true, false, null, not x, not 0, not 5\nprint true == 1, 1 == true, null == false, 3 != 4\n",
    "andor_val": "x = 5 and 7\nprint x, 0 or 9, null or 3, 1 and null, false or false\n",
    "truthy": "if 0:\n  print 1\nelse:\n  print 2\nif null:\n  print 3\nif -1:\n  print 4\nif false or 0:\n  print 5\nelse:\n  print 6\n",
    "boolarg": "def f(a, b):\n  if a:\n    return b\n  return a\nprint f(1 < 2, 5), f(2 < 1, 5), f(null, 1)\n",
    "bigint": "x = 4611686018427387903\nprint x, -x, x - 1, -x - 1\n",
    "str_basic": 's = "hello" + " " + "world"\nprint s, len(s), s[0], s[-1], s[4]\nprint s == "hello world", s != "x", "a" < "b", "ab" < "a", "b" >= "b", "" == ""\nprint "" or "dflt", "x" and "y", not ""\ndef rep(a, n):\n  r = ""\n  i = 0\n  while i < n:\n    r = r + a\n    i = i + 1\n  return r\nt = rep("ab", 50)\nprint len(t), t[99], t == rep("ab", 50), rep("x", 3) + "!"\n',
    "str_eq": "a = \"x\" + \"y\"\nprint a == \"xy\", \"xy\" == a, a == 1, 1 == a, a == null, a != \"xz\"\nprint \"abc\" < \"abd\", \"abc\" <= \"abc\", \"b\" > \"abc\", \"\" < \"a\"\n",
    "str_fn": "def f(s, n):\n  if n == 0:\n    return s\n  return f(s + s, n - 1)\nx = f(\"ab\", 10)\nprint len(x), x[1023], x[-1], len(f(\"\", 5))\n",
    "str_print": "print \"a\", \"b\" + \"c\", 1, \"d\"\nx = \"q\"\nprint x, true\n",
    'list_basic': 'x = [1, "a", true, null, [2, 3], ""]\nprint x\nprint len(x), x[1], x[-1]\nx[0] = 9\nappend(x, 7)\nprint x == [9, "a", true, null, [2, 3], "", 7], [] == [], [1] == [2], x[4][1]\nprint not [], [] or 5\nfor v in [1, 2]:\n  print v\nfor i in range(3):\n  print i\n',
    'list_grow': 'xs = []\nfor i in range(1000):\n  append(xs, i * i)\nt = 0\nfor v in xs:\n  t = t + v\nprint len(xs), t, xs[999], xs[-1], xs[500]\nys = [xs[3], xs[4]]\nprint ys\n',
    'sieve': 'def sieve(n):\n  p = []\n  i = 0\n  while i <= n:\n    append(p, true)\n    i = i + 1\n  p[0] = false\n  p[1] = false\n  for i in range(2, n + 1):\n    if p[i]:\n      j = i * i\n      while j <= n:\n        p[j] = false\n        j = j + i\n  out = []\n  for i in range(n + 1):\n    if p[i]:\n      append(out, i)\n  return out\nprint sieve(100)\nprint len(sieve(5000))\n',
    'for_ctl': 'for i in range(10):\n  if i == 2:\n    continue\n  if i == 6:\n    break\n  for j in range(i, 3):\n    print i, j\nprint "done"\nfor i in range(5, 3):\n  print "never"\n',
    'list_eq': 'a = [1, [2, "x"], [], "s"]\nb = [1, [2, "x"], [], "s"]\nprint a == b, a != b, a == [1], [1, 2] == [1, 3], [[1]] == [[1]], [1] == 1, "a" == ["a"]\nb[1][1] = "y"\nprint a == b, b\n',
    'list_fn': 'def mk(n):\n  r = []\n  for i in range(n):\n    append(r, [i, "v" + "x"])\n  return r\ndef total(xs):\n  t = 0\n  for p in xs:\n    t = t + p[0]\n  return t\nq = mk(20)\nprint total(q), len(q), q[19], q[-20]\n',
    'dict_basic': 'd = {"a": 1, "b": [2], 3: "x"}\nprint d, len(d), d["a"], d[3]\nd["c"] = 5\nd["a"] = 0\nprint d, "a" in d, "z" in d, has(d, "b"), keys(d), values(d)\nprint d == {"a": 0, "b": [2], 3: "x", "c": 5}, {} == {}, not {}\nfor k in keys(d):\n  print k, d[k]\n',
    'dict_grow': 'd = {}\nfor i in range(300):\n  d[i] = i * 2\nd["k"] = []\nappend(d["k"], 5)\nt = 0\nfor k in keys(d):\n  if k != "k":\n    t = t + d[k]\nprint len(d), t, d[299], d["k"], has(d, 150), has(d, 300)\nfor i in range(300):\n  d[i] = 0\nprint values(d)[7], len(d)\n',
    'dict_words': 'def count(ws):\n  c = {}\n  for w in ws:\n    if w in c:\n      c[w] = c[w] + 1\n    else:\n      c[w] = 1\n  return c\nc = count(["a", "b", "a", "c" + "d", "cd", "a"])\nprint c, c["a"], c["cd"]\nprint c == {"cd": 2, "a": 3, "b": 1}, c == {"a": 3}, {"x": {"y": [1]}} == {"x": {"y": [1]}}\n',
    'contains': 'print 3 in [1, 2, 3], 4 in [1, 2, 3], "ell" in "hello", "z" in "hello", "" in "x", "hello!" in "hello", 5 not in [1], "a" in ["b", "a"]\n',
    "slice_str": 's = "hello world"\nprint s[0:5], s[6:], s[:5], s[-5:], s[:-6], s[3:3], s[5:2], s[-100:100], s[:], s[2:4] + "!"\nl = [1, 2, 3, 4, 5]\nprint l[1:3], l[:2], l[-2:], l[2:], l[:], l[4:1], l[9:], l[:-1]\nm = l[1:4]\nappend(m, 9)\nprint m, l, len(l[0:0])\nprint str(0), str(-45) + "|", str(123456789012), str(true), str(false), str(null), str("x"), len(str(4611686018427387903)), str(-4611686018427387903)\nn = 0\nt = ""\nwhile n < 5:\n  t = t + str(n * n) + ","\n  n = n + 1\nprint t\n',
    "builtins": 'print find("hello", "ll"), find("hello", "z"), find("abc", ""), find("", "a")\np = split("a,b,,c", ",")\nprint p, len(p), split("abc", ","), split("a--b--", "--")\nprint int("123"), int("-45") + 1, int("0")\ntry:\n  x = int("12x")\n  print "no"\nexcept as e:\n  print "caught"\ntry:\n  print "in try"\nexcept as e2:\n  print "never"\ndef f(n):\n  if n > 2:\n    raise "too big: " + str(n)\n  return n\ntry:\n  print f(1)\n  print f(5)\n  print "unreach"\nexcept as err:\n  print "caught2"\nprint "after"\na = argv()\nprint len(a)\nwrite_bytes("/tmp/_cc_wb.out", [72, 105, 10])\nprint read_text("/tmp/_cc_wb.out"), len(read_text("/tmp/_cc_wb.out"))\n',
    "list_add": 'a = [1, 2]\nb = [3]\nprint a + b, a + [] , [] + b, len(a + b + a), [] + []\nx = a + b\nappend(x, 9)\nprint x, a, b\n',
    "for_str": 'for ch in "abc":\n  print ch\nfor k in {"x": 1, "y": 2}:\n  print k\nn = 0\nfor c in "hello world":\n  if c == "o":\n    n = n + 1\nprint n\n',
    "noreturn": "def p(n):\n  print n\np(5)\np(6)\n",
}

ERRS = {
    "closure_arity": "def mk():\n  def f(a):\n    return a\n  return f\ng = mk()\nprint g(1, 2)\n",
    "raise_uncaught": "print 1\nraise \"bye\"\n",
    "raise_in_fn": "def f():\n  raise \"x\"\ntry:\n  f()\nexcept as e:\n  print 5\nf()\n",
    'dict_nokey': 'd = {"a": 1}\nprint d["a"]\nprint d["b"]\n',
    'keys_int': 'print keys(5)\n',
    'in_int': 'print 1 in 5\n',
    'str_in_int': 'print 1 in "abc"\n',
    'list_oob': 'x = [1]\nprint 1\nprint x[1]\n',
    'list_set_oob': 'x = [1]\nx[1] = 2\n',
    'list_idx_type': 'x = [1]\nprint x[true]\n',
    'for_int': 'for v in 5:\n  print v\n',
    'append_int': 'append(3, 4)\n',
    'range_type': 'for i in range("a"):\n  print i\n',
    "str_plus_int": "print 1\nprint \"a\" + 1\n",
    "str_cmp_int": "print 2\nprint \"a\" < 1\n",
    "str_idx_oob": "s = \"abc\"\nprint 3\nprint s[3]\n",
    "str_idx_neg_oob": "s = \"abc\"\nprint s[-3]\nprint s[-4]\n",
    "str_idx_type": "s = \"abc\"\nprint s[\"a\"]\n",
    "len_int": "print len(5)\n",
}

MODS = {
    "modules": {'main': 'import util\nprint util.count, util.total(), util.bump(1), util.K\n', 'util': 'import sub\nK = [1, 2, 3]\ncount = 0\ndef bump(n):\n  global_total = n + sub.base()\n  return global_total\ndef total():\n  t = 0\n  for v in K:\n    t = t + v\n  return t\ncount = bump(10)\n', 'sub': 'B = 100\ndef base():\n  return B\n'},
}

BAD = {
    "float": "print 1.5\n",
    "div": "print 7 / 2\n",
    "unknown": "print y\n",
    "bigliteral": "print 4611686018427387904\n",
    "arity": "def f(a):\n  return a\nprint f(1, 2)\n",
    "range3": "for i in range(0, 5, 2):\n  print i\n",
}


def interp(path):
    r = subprocess.run([sys.executable, HS, "run", path, "--backend", "interp"],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def compile_prog(path, out, backend="interp"):
    return subprocess.run([sys.executable, HS, "run", CC, "--backend", backend,
                           path, out], capture_output=True, text=True)


def check(name, cond, detail=""):
    global total, fails
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        fails += 1
        print(f"FAIL {name}", detail)


with tempfile.TemporaryDirectory() as d:
    for name, src in PROGS.items():
        p = os.path.join(d, name + ".hs")
        out = os.path.join(d, name + ".bin")
        open(p, "w").write(src)
        rc, want = interp(p)
        c = compile_prog(p, out)
        if c.returncode != 0:
            check(f"cc {name}", False, c.stderr + c.stdout)
            continue
        r = subprocess.run([out], capture_output=True, text=True)
        check(f"cc {name}", rc == 0 and r.returncode == 0 and r.stdout == want,
              (rc, want, r.returncode, r.stdout, r.stderr))
    for name, files in MODS.items():
        md = os.path.join(d, "mod_" + name)
        os.makedirs(md)
        for fn, src in files.items():
            open(os.path.join(md, fn + ".hs"), "w").write(src)
        p = os.path.join(md, "main.hs")
        out = os.path.join(md, "main.bin")
        rc, want = interp(p)
        c = compile_prog(p, out)
        if c.returncode != 0:
            check(f"cc mod {name}", False, c.stderr + c.stdout)
            continue
        r = subprocess.run([out], capture_output=True, text=True)
        check(f"cc mod {name}", rc == 0 and r.returncode == 0 and r.stdout == want,
              (rc, want, r.returncode, r.stdout, r.stderr))
    for name, src in ERRS.items():
        p = os.path.join(d, "err_" + name + ".hs")
        out = os.path.join(d, "err_" + name + ".bin")
        open(p, "w").write(src)
        rc, want = interp(p)
        c = compile_prog(p, out)
        if c.returncode != 0:
            check(f"cc err {name}", False, c.stderr + c.stdout)
            continue
        r = subprocess.run([out], capture_output=True, text=True)
        check(f"cc err {name}", rc != 0 and r.returncode != 0 and r.stdout == want,
              (rc, want, r.returncode, r.stdout, r.stderr))
    for name, src in BAD.items():
        p = os.path.join(d, "bad_" + name + ".hs")
        out = os.path.join(d, "bad_" + name + ".bin")
        open(p, "w").write(src)
        c = compile_prog(p, out)
        check(f"cc rejects {name}", c.returncode != 0 and "error:" in c.stdout
              and not os.path.exists(out), (c.returncode, c.stdout, c.stderr))
    # M5: bootstrap. cc1 = cc.hs run by interp; cc2 = ELF cc1 makes from cc.hs;
    # cc3 = ELF cc2 makes from cc.hs. cc2 == cc3 byte for byte (fixed point),
    # and cc2 compiles every program above to the same bytes as cc1 did.
    cc2 = os.path.join(d, "cc2")
    cc3 = os.path.join(d, "cc3")
    c = compile_prog(CC, cc2)
    ok2 = c.returncode == 0 and os.path.exists(cc2)
    check("bootstrap: cc1 compiles cc.hs", ok2, c.stderr + c.stdout)
    if ok2:
        os.chmod(cc2, 0o755)
        r = subprocess.run([cc2, CC, cc3], capture_output=True, text=True)
        same = r.returncode == 0 and open(cc2, "rb").read() == open(cc3, "rb").read()
        check("bootstrap: cc2 == cc3 (fixed point)", same, (r.returncode, r.stdout, r.stderr))
        bad = []
        # cc2 itself has 63-bit Ints, so literals >= 2^61 (tagged 2n+1 would
        # overflow) are the documented limit: those programs need cc1
        biglit = {"arith", "bigint", "slice_str"}
        for name, src in PROGS.items():
            if name in biglit:
                continue
            p = os.path.join(d, name + ".hs")
            o1 = os.path.join(d, name + ".bin")
            o2 = os.path.join(d, name + ".cc2")
            r = subprocess.run([cc2, p, o2], capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(o2) or open(o1, "rb").read() != open(o2, "rb").read():
                bad.append(name)
        check("bootstrap: cc2 emits the same ELF as cc1 for every program", not bad, bad)
        rej = []
        for name, src in BAD.items():
            p = os.path.join(d, "bad_" + name + ".hs")
            o2 = os.path.join(d, "bad_" + name + ".cc2")
            r = subprocess.run([cc2, p, o2], capture_output=True, text=True)
            if r.returncode == 0 or os.path.exists(o2):
                rej.append(name)
        check("bootstrap: cc2 rejects what cc1 rejects", not rej, rej)
    # the same compiler run natively (gcc) emits identical bytes
    p = os.path.join(d, "fib.hs")
    o1, o2 = os.path.join(d, "fib.i"), os.path.join(d, "fib.n")
    compile_prog(p, o1, "interp")
    c = compile_prog(p, o2, "native")
    same = c.returncode == 0 and open(o1, "rb").read() == open(o2, "rb").read()
    check("cc.hs: interp and native emit identical ELF", same, c.stderr[-300:])
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
