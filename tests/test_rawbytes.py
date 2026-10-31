#!/usr/bin/env python3
"""read_mem raw-byte path: pin the CURRENT per-backend behavior as a gated
repro, pending the text/Bytes representation decision.

This suite documents an observed divergence; it does not endorse it.
- Literal/text paths (source literals, print, JSON) agree on valid UTF-8
  across backends (stage #331's 48 checks, tests/test_jsonbytes.py).
- The read_mem path does NOT: interp decodes Latin1 and byte_* then
  UTF-8-re-encodes, so non-ASCII bytes - valid UTF-8 or not - are observed
  with different lengths and values than the compiled backends, which keep
  raw bytes. byte_* on interp is therefore not a raw-byte escape hatch
  today; a real one needs the pending representation decision.

Expected values below are the pinned CURRENT behavior (probe-verified on
master cda8aac6), per backend. A future representation change is expected
to rewrite this file deliberately.
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

PRE = """def mk(a, b):
  unsafe:
    Ptr p = alloc(4)
    store8(p, a)
    store8(p + 1, b)
    return p
s = read_mem(mk(%d, %d), 2)
"""

# (name, byte0, byte1, want per backend: (byte_len, byte_at0, byte_at1, find_A_or_-1))
INTERP_NOTE = "interp: Latin1 decode + UTF-8 re-encode (pinned divergence)"
CASES = [
    # valid UTF-8: C3 A9 = é
    ("raw_valid_utf8", 195, 169,
     {"interp": (4, 195, 131, -1), "native": (2, 195, 169, -1),
      "x64": (2, 195, 169, -1), "x64-ast": (2, 195, 169, -1)}),
    # invalid UTF-8: 0x80 then "A"
    ("raw_invalid", 128, 65,
     {"interp": (3, 194, 128, 2), "native": (2, 128, 65, 1),
      "x64": (2, 128, 65, 1), "x64-ast": (2, 128, 65, 1)}),
    # valid UTF-8: E0 B8 81 alone would be 3 bytes; use first two bytes of ก
    ("raw_thai_fragment", 224, 184,
     {"interp": (4, 195, 160, -1), "native": (2, 224, 184, -1),
      "x64": (2, 224, 184, -1), "x64-ast": (2, 224, 184, -1)}),
]

fails = 0
total = 0
with tempfile.TemporaryDirectory() as d:
    for name, b0, b1, want in CASES:
        p = os.path.join(d, name + ".holy")
        with open(p, "w", encoding="utf-8") as f:
            f.write(PRE % (b0, b1))
            f.write('print byte_len(s)\nprint byte_at(s, 0)\nprint byte_at(s, 1)\nprint byte_find(s, "A")\n')
        for backend in ("interp", "native", "x64", "x64-ast"):
            total += 1
            wl, w0, w1, wf = want[backend]
            want_out = f"{wl}\n{w0}\n{w1}\n{wf}\n"
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
            got = r.stdout.decode("utf-8", "replace")
            ok = r.returncode == 0 and got == want_out and not r.stderr
            print(("ok  " if ok else "FAIL") + f" {name} [{backend}]")
            if not ok:
                fails += 1
                print(f"  want={want_out!r} got={got!r} rc={r.returncode} err={r.stderr.decode('utf-8','replace')[-200:]!r}")

print(f"{total - fails}/{total} passed  # {INTERP_NOTE}")
sys.exit(1 if fails else 0)
