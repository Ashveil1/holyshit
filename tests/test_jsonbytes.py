#!/usr/bin/env python3
"""JSON non-ASCII byte handling: interp/x64/x64-ast parity, native surface.

runtime/json.holy now takes every string length with byte_len, so JSON byte
offsets cannot move when len(Str) flips to code points later. These cases
gate what the shared corpus cannot:

- json_str escaping of non-ASCII: interp (CPython ensure_ascii) and the x64
  parser agree on \\uXXXX + surrogate pairs. The native rt.c encoder passes
  bytes >= 0x20 raw instead - a pre-existing divergence (native never reads
  runtime/json.holy), excluded here and reported, not enshrined as correct.
- error text per backend: interp/x64 use CPython's messages; native rt.c has
  its own wording (same style as test_byteops.py's error-surface split).
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import x64gen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HS = os.path.join(ROOT, "hs.py")
INTERP = os.path.join(ROOT, "interp.py")

# (name, src, want_stdout, err per backend or None)
SAME = None
CASES = [
    ("escape_thai", 'print json_str(json_parse("{\\"t\\": \\"ไทย\\"}"))\n',
     '{"t": "\\u0e44\\u0e17\\u0e22"}\n', None),
    ("escape_astral", 'print json_str(json_parse("\\"\\\\ud83d\\\\ude42\\""))\n',
     '"\\ud83d\\ude42"\n', None),
    ("roundtrip_mixed",
     'v = json_parse("{\\"s\\": \\"สวัสดี\\", \\"n\\": 42}")\nprint json_str(v)\nprint v["n"]\n',
     '{"s": "\\u0e2a\\u0e27\\u0e31\\u0e2a\\u0e14\\u0e35", "n": 42}\n42\n', None),
    ("trailing_data", 'print json_parse("\\"ไทย\\" x")\n', None,
     {"interp": "Extra data", "x64": "Extra data", "x64-ast": "Extra data",
      "native": "trailing data"}),
    ("truncated_escape", 'print json_parse("\\"\\\\u0e0\\"")\n', None,
     {"interp": "Invalid \\uXXXX escape", "x64": "Invalid \\uXXXX escape",
      "x64-ast": "Invalid \\uXXXX escape", "native": "bad \\u escape"}),
]

# escaping parity is gated where the implementations share CPython's contract
ESC_BACKENDS = ["interp", "x64", "x64-ast"]
ALL_BACKENDS = ["interp", "native", "x64", "x64-ast"]

fails = 0
total = 0
with tempfile.TemporaryDirectory() as d:
    for name, src, want_out, want_err in CASES:
        p = os.path.join(d, name + ".holy")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src)
        backends = ALL_BACKENDS if want_err is not None else ESC_BACKENDS
        for backend in backends:
            total += 1
            if backend == "x64-ast":
                out = os.path.join(d, name + "-ast")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    rc = x64gen.build_x64_ast(p, out)
                if rc != 0:
                    print(f"FAIL {name} [{backend}] build rc={rc} err={err.getvalue()!r}")
                    fails += 1
                    continue
                cmd = [out]
            elif backend == "interp":
                cmd = [sys.executable, INTERP, p]
            else:
                cmd = [sys.executable, HS, "run", p, "--backend", backend]
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            stderr = r.stderr.decode("utf-8", "replace")
            if want_err is not None:
                ok = r.returncode != 0 and want_err[backend] in stderr
            else:
                ok = (r.returncode == 0
                      and r.stdout.decode("utf-8", "replace") == want_out
                      and not stderr)
            print(("ok  " if ok else "FAIL") + f" {name} [{backend}]")
            if not ok:
                fails += 1
                print(f"  rc={r.returncode} out={r.stdout!r} err={stderr[-200:]!r}")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
