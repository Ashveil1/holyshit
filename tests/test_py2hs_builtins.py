#!/usr/bin/env python3
"""py2hs reserved-name coverage gate: every interp.BUILTINS name must be
covered by py2hs's HS_BUILTINS or HS_RESERVED, so a Python local or
parameter of that name is renamed (name_) instead of silently shadowing
the builtin in translated hs. Pins the fail-closed coverage probe and the
nm() renaming behavior for the byte/tcp collision names."""
import os
import re
import sys
import tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import interp
import py2hs


def uncovered(builtins, reserved, reference):
    return sorted(set(reference) - (set(builtins) | set(reserved)))


# 1/4 coverage: current py2hs sets cover every interp builtin
missing = uncovered(py2hs.HS_BUILTINS, py2hs.HS_RESERVED, interp.BUILTINS)
assert not missing, f"py2hs reserved-name coverage gap: {missing}"

# 2/4 negative check: the probe must report a deliberately dropped name
probe = uncovered(py2hs.HS_BUILTINS - {"byte_len"}, py2hs.HS_RESERVED, interp.BUILTINS)
assert probe == ["byte_len"], f"coverage probe must fail closed, got {probe}"

# 3/4 binding regression: collision names rename consistently at use sites
src = ("def f(read_bytes, byte_len, tcp_recv):\n"
       "    x = read_bytes\n"
       "    y = byte_len\n"
       "    return tcp_recv\n")
with tempfile.TemporaryDirectory() as td:
    inp = os.path.join(td, "in.py")
    out = os.path.join(td, "out.holy")
    open(inp, "w").write(src)
    errs = py2hs.translate([inp], out, os.path.join(ROOT, "x64.py"))
    assert not errs, f"translate failed: {errs}"
    hs = open(out).read()
for name in ("read_bytes", "byte_len", "tcp_recv"):
    assert not re.search(r"\b%s\b" % name, hs), f"unrenamed {name} in translated output: {hs!r}"
    assert hs.count(name + "_") == 2, f"{name}_ must appear at param + use sites: {hs!r}"

# 4/4 non-collision identifiers stay untouched
assert "def f(" in hs, f"function name must not be renamed: {hs!r}"
print("4/4 py2hs reserved-name coverage (59 builtins) + fail-closed probe + nm collision renaming")
