#!/usr/bin/env python3
"""AST backend: package-cycle imports must not crash the module walkers.

Regression: import std.font pulls std.gfx, whose modules carry a
back-reference through the std namespace, so the prog's embedded module
graph (_mods/imports/submods) is cyclic. x64gen's uses_json and
scan_uses_bytes walkers recursed into it without a visited set and
segfaulted the AST backend (ir_backend=False); the IR backend was fine.
"""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_xkernel

os.environ["HSPATH"] = str(ROOT) + os.pathsep + os.environ.get("HSPATH", "")

REPRO = 'import std.font\nprint std.font.measure("HI", 1)\n'

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    src = d / "main.holy"
    src.write_text(REPRO)
    with contextlib.redirect_stdout(io.StringIO()):
        rc_ast = build_xkernel(str(src), str(d / "ast"), ir_backend=False)
        rc_ir = build_xkernel(str(src), str(d / "ir"), ir_backend=True)
    assert rc_ast == 0, "AST backend failed on the std.font import cycle"
    assert rc_ir == 0, "IR backend failed on the std.font import cycle"
print("1/1 AST backend survives package-cycle imports")
