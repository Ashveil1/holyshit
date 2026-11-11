#!/usr/bin/env python3
"""py2hs reserved-name coverage gate + module-scope collision diagnostics.

Coverage: every interp.BUILTINS name must be covered by py2hs's HS_BUILTINS
or HS_RESERVED, so a Python local or parameter of that name is renamed
(name_) instead of silently shadowing the builtin in translated hs.

Diagnostics: py2hs warns (side channel only, NOT prevention - the clobber
still happens and callers that ignore the collector see nothing) when a
direct top-level def or a class emitted at module scope collides with a
covered name. LIMITATION: ind==0 detects only direct top-level and hoisted
defs/classes; module-level bindings nested inside top-level if/try/while
containers, defs nested inside functions, and function-nested classes
arrive at ind>=1 and are NOT diagnosed."""
import ast
import os
import re
import subprocess
import sys
import tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import interp
import py2hs

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def tr(src, warn="collect"):
    """Translate one small source; returns (errs, output, warnings)."""
    w = [] if warn == "collect" else None
    with tempfile.TemporaryDirectory() as td:
        inp = os.path.join(td, "in.py")
        out = os.path.join(td, "out.holy")
        open(inp, "w").write(src)
        if w is None:
            errs = py2hs.translate([inp], out, os.path.join(ROOT, "x64.py"))
        else:
            errs = py2hs.translate([inp], out, os.path.join(ROOT, "x64.py"), w)
        return errs, open(out).read(), w


def uncovered(builtins, reserved, reference):
    return sorted(set(reference) - (set(builtins) | set(reserved)))


@check
def c1():
    missing = uncovered(py2hs.HS_BUILTINS, py2hs.HS_RESERVED, interp.BUILTINS)
    assert not missing, f"py2hs reserved-name coverage gap: {missing}"
    return "coverage: interp.BUILTINS subset of HS_BUILTINS|HS_RESERVED"


@check
def c2():
    probe = uncovered(py2hs.HS_BUILTINS - {"byte_len"}, py2hs.HS_RESERVED, interp.BUILTINS)
    assert probe == ["byte_len"], f"coverage probe must fail closed, got {probe}"
    return "fail-closed probe reports a dropped name"


@check
def c3():
    src = ("def f(read_bytes, byte_len, tcp_recv):\n"
           "    x = read_bytes\n"
           "    y = byte_len\n"
           "    return tcp_recv\n")
    _, hs, w = tr(src)
    for name in ("read_bytes", "byte_len", "tcp_recv"):
        assert not re.search(r"\b%s\b" % name, hs), f"unrenamed {name} in translated output: {hs!r}"
        assert hs.count(name + "_") == 2, f"{name}_ must appear at param + use sites: {hs!r}"
    # nm renaming is a binding rewrite, not a module-scope name collision
    assert not [x for x in w if "read_bytes" in x or "byte_len" in x or "tcp_recv" in x], w
    return "nm collision renaming at param/use sites (no diagnostics)"


@check
def c4():
    _, hs, _ = tr("def g(total):\n    return total\n")
    assert "def g(" in hs and "total" in hs, f"non-collision identifiers must be untouched: {hs!r}"
    return "non-collision identifiers untouched"


@check
def c5():
    src = "def byte_len(s):\n    return 999\n"
    errs_a, out_a, _ = tr(src, warn="legacy")
    errs_b, out_b, w = tr(src)
    assert out_a == out_b, "collector must not change output bytes"
    assert errs_a == errs_b, "collector must not change the errs return"
    return "legacy call shape == collector call shape (output + return identical)"


@check
def c6():
    # The silent case: an UNCALLED module-level def still clobbers the
    # builtin for hand-spliced patch code; the diagnostic must flag it
    # while the emitted interface stays byte-identical (raw def kept).
    errs, hs, w = tr("def byte_len(s):\n    return 999\n")
    hits = [x for x in w if "'byte_len'" in x]
    assert len(hits) == 1 and "top-level def" in hits[0], f"expected one def diagnostic: {w!r}"
    assert "def byte_len(s):" in hs, f"interface must stay raw: {hs!r}"
    assert errs == [], f"collision is a warning, not an errs entry: {errs!r}"
    return "uncalled top-level def collision diagnosed; raw def preserved; errs unchanged"


@check
def c7():
    errs, hs, w = tr("class read_bytes:\n  def f(self):\n    return 1\n")
    hits = [x for x in w if "'read_bytes'" in x]
    assert len(hits) == 1 and "class" in hits[0], f"expected one class diagnostic: {w!r}"
    assert "class read_bytes" in hs, f"interface must stay raw: {hs!r}"
    assert errs == [], errs
    return "class-name collision diagnosed; raw class preserved"


@check
def c8():
    _, _, w = tr("class self_:\n  def f(self):\n    return 1\n")
    hits = [x for x in w if "'self_'" in x]
    assert len(hits) == 1, f"HS_RESERVED name must be diagnosed: {w!r}"
    return "HS_RESERVED names included in diagnostics"


@check
def c9():
    # Hoisted nested class: emitted name byte_len is the collision, even
    # though neither source name (byte, len) is covered alone.
    _, hs, w = tr("class byte:\n  class len:\n    pass\n")
    hits = [x for x in w if "'byte_len'" in x]
    assert len(hits) == 1 and "class" in hits[0], f"emitted-name collision must be diagnosed: {w!r}"
    assert "class byte_len" in hs, f"hoisted class must be emitted: {hs!r}"
    return "hoisted Outer_Inner emitted-name collision diagnosed (byte.len -> byte_len)"


@check
def c10():
    _, hs, w = tr("class Outer:\n  class Inner:\n    pass\n")
    assert w == [], f"non-colliding hoisted class must stay quiet: {w!r}"
    assert "class Outer_Inner" in hs, hs
    return "non-colliding hoisted class quiet"


@check
def c11():
    # LIMITATION PIN: module-level bindings inside top-level containers and
    # defs nested in functions are NOT diagnosed (ind >= 1). Documented, not
    # universal module-scope safety.
    src1 = "if True:\n    def byte_len(s):\n        return 1\n"
    src2 = "def outer():\n    def byte_len(s):\n        return 1\n    return byte_len\n"
    for src in (src1, src2):
        _, _, w = tr(src)
        assert w == [], f"container/nested def must NOT be diagnosed (documented limitation): {w!r}"
    return "limitation pinned: container/nested defs not diagnosed"


@check
def c12():
    # Methods are class-scoped (no module clobber); module-level assigns are
    # already nm-renamed by target(). Neither is a diagnostic case.
    _, _, w = tr("class C:\n  def byte_len(self, x):\n    return x\n")
    assert w == [], f"method must not be diagnosed: {w!r}"
    _, hs, w = tr("read_bytes = 5\n")
    assert w == [], f"module assign already renamed, no diagnostic: {w!r}"
    assert "read_bytes_ = 5" in hs, hs
    return "method and module-assign negatives quiet"


@check
def c13():
    # Corpus gate: all four actual pipeline input selections stay
    # warning-free. Pipeline preps preserve def/class name sets exactly
    # (verified), so raw selections cover the prepped translator inputs.
    sels = [["x64gen.py", "irx64.py"], ["iropt.py"]]
    ir = ast.parse(open(os.path.join(ROOT, "ir.py")).read())
    for lo, hi, kinds in ((69, 833, (ast.ClassDef, ast.FunctionDef)),
                          (831, 1037, (ast.FunctionDef,))):
        items = [n for n in ir.body if isinstance(n, kinds) and lo <= n.lineno < hi]
        sels.append([None, ast.unparse(ast.Module(body=items, type_ignores=[]))])
    with tempfile.TemporaryDirectory() as td:
        for i, sel in enumerate(sels):
            if sel[0] is None:
                p = os.path.join(td, "ir-sel-%d.py" % i)
                open(p, "w").write(sel[1])
                sel = [p]
            else:
                sel = [os.path.join(ROOT, s) for s in sel]
            w = []
            errs = py2hs.translate(sel, os.path.join(td, "out-%d.holy" % i),
                                   os.path.join(ROOT, "x64.py"), w)
            assert w == [], f"corpus selection {i} must stay warning-free: {w!r}"
    return "corpus gate: all 4 pipeline input selections warning-free"


@check
def c14():
    with tempfile.TemporaryDirectory() as td:
        bad = os.path.join(td, "bad.py")
        open(bad, "w").write("def byte_len(s):\n    return 999\n")
        out = os.path.join(td, "bad.holy")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/py2hs.py"),
                            bad, out], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "WARNING name-collision: top-level def 'byte_len'" in r.stdout, r.stdout
        assert "def byte_len(s):" in open(out).read(), "CLI output must stay raw"
        r2 = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/py2hs.py"),
                             os.path.join(ROOT, "x64gen.py") + "," + os.path.join(ROOT, "irx64.py"),
                             os.path.join(td, "all.holy")], capture_output=True, text=True)
        assert r2.returncode == 0, r2.stderr
        assert "WARNING" not in r2.stdout, f"current corpus must not warn: {r2.stdout[:400]}"
        assert "UNSUPPORTED FunctionDef:12448" in r2.stdout, "UNSUPPORTED contract unchanged"
    return "CLI side channel: WARNING on collision, zero-warning corpus, UNSUPPORTED unchanged"


failures = 0
for fn in CHECKS:
    msg = fn()
    failures += 0
print(f"{len(CHECKS)}/{len(CHECKS)} py2hs reserved-name coverage (59 builtins) + fail-closed probe + nm collision renaming + module-scope collision diagnostics")
