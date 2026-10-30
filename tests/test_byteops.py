#!/usr/bin/env python3
"""byte_len/byte_find/byte_at: identical byte semantics on every backend.

The corpus t_byteops.holy gates value parity; this suite gates the error
surface (substring per backend: native error lines differ by design) and
the boundary cases: negative wrap, unsigned high bytes, empty needle.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HS = os.path.join(ROOT, "hs.py")
INTERP = os.path.join(ROOT, "interp.py")

CASES = [
    # (name, src, want_stdout or None, want_err_substr or None)
    ("oob_hi", 'print(byte_at("hi", 2))\n', None, "index out of range"),
    ("oob_neg", 'print(byte_at("hi", -3))\n', None, "index out of range"),
    ("oob_empty", 'print(byte_at("", 0))\n', None, "index out of range"),
    ("len_type", 'print(byte_len(5))\n', None, "byte_len wants byte_len(s)"),
    ("len_arity", 'print(byte_len("a", "b"))\n', None, "byte_len wants byte_len(s)"),
    ("find_type", 'print(byte_find("a", 1))\n', None, "byte_find wants byte_find(s, sub)"),
    ("at_type_f", 'print(byte_at("a", 1.5))\n', None, "byte_at wants byte_at(s, i)"),
    ("at_type_s", 'print(byte_at(5, 0))\n', None, "byte_at wants byte_at(s, i)"),
    ("at_type_b", 'print(byte_at("a", true))\n', None, "byte_at wants byte_at(s, i)"),
    ("high_bytes", 'print(byte_at("🙂", 0), byte_at("🙂", -1))\n', "240 130\n", None),
    ("empty_needle", 'print(byte_find("abc", ""), byte_find("", ""))\n', "0 0\n", None),
    ("shadow", 'def byte_len(x):\n  return 42\nprint(byte_len("abc"))\nprint(byte_at("abc", 0))\n', "42\n97\n", None),
]

BACKENDS = [("interp", None), ("native", None), ("x64", None)]

fails = 0
total = 0
with tempfile.TemporaryDirectory() as d:
    for name, src, want_out, want_err in CASES:
        p = os.path.join(d, name + ".holy")
        with open(p, "w") as f:
            f.write(src)
        for backend, _ in BACKENDS:
            total += 1
            if backend == "interp":
                cmd = [sys.executable, INTERP, p]
            else:
                cmd = [sys.executable, HS, "run", p, "--backend", backend]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if want_err is not None:
                ok = r.returncode != 0 and want_err in r.stderr
            else:
                ok = r.returncode == 0 and r.stdout == want_out and not r.stderr
            print(("ok  " if ok else "FAIL") + f" {name} [{backend}]")
            if not ok:
                fails += 1
                print(f"  rc={r.returncode} out={r.stdout!r} err={r.stderr[-200:]!r}")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
