#!/usr/bin/env python3
"""Bytes type, stage 1 (user-approved representation option A: Unicode Str +
separate Bytes). Interp-only and purely additive:

- read_bytes(path) -> Bytes: the missing raw-read primitive. Lossless by
  construction - no decoding, so no invalid-byte policy is decided here.
- byte_len/byte_find/byte_at accept Bytes in addition to Str. Str behavior
  is unchanged (UTF-8 re-encode semantics stay pinned by test_byteops.py
  and test_rawbytes.py).
- len(Bytes) is the byte count; print/str render Bytes as Python b'...'.

The x64/be.holy backends do not know Bytes yet; that is the planned
shared-backend stage with the OS-coordinated seed protocol. Keep this
suite gated to interp+native until then. The invalid-byte boundary policy
for tcp_recv/http_get/read_text stays explicitly undecided and untouched.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERP = os.path.join(ROOT, "interp.py")

fails = 0
total = 0


HS = os.path.join(ROOT, "hs.py")
BACKENDS = ("interp", "native")


def run(src, files, backend):
    global fails, total
    with tempfile.TemporaryDirectory() as d:
        for name, data in files.items():
            mode = "wb" if isinstance(data, bytes) else "w"
            with open(os.path.join(d, name), mode) as f:
                f.write(data)
        p = os.path.join(d, "prog.holy")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src.replace("__D__", d))
        if backend == "interp":
            cmd = [sys.executable, INTERP, p]
        else:
            cmd = [sys.executable, HS, "run", p, "--backend", backend]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return r.returncode, r.stdout.decode("utf-8", "replace"), \
            r.stderr.decode("utf-8", "replace")


def check(name, src, want_out=None, want_err=None, files=None):
    global fails, total
    for backend in BACKENDS:
        total += 1
        rc, out, err = run(src, files or {}, backend)
        if want_out is not None:
            ok = rc == 0 and out == want_out and not err
            detail = f"want_out={want_out!r} got={out!r} rc={rc} err={err[-200:]!r}"
        else:
            ok = rc != 0 and want_err in err
            detail = f"want_err={want_err!r} got_err={err[-200:]!r} rc={rc} out={out!r}"
        print(("ok  " if ok else "FAIL") + f" {name} [{backend}]")
        if not ok:
            fails += 1
            print("  " + detail)


# raw roundtrip through write_bytes/read_bytes: invalid UTF-8 bytes survive
check("roundtrip_raw", """
write_bytes("__D__/bin.dat", [72, 105, 128, 255, 10])
b = read_bytes("__D__/bin.dat")
print byte_len(b)
print len(b)
print byte_at(b, 0)
print byte_at(b, 1)
print byte_at(b, 2)
print byte_at(b, 3)
print byte_at(b, 4)
""", want_out="5\n5\n72\n105\n128\n255\n10\n")

# valid UTF-8 file read as Bytes: raw byte view, Str needles encode UTF-8
check("utf8_bytes_view", """
write_text("__D__/t.txt", "héllo")
b = read_bytes("__D__/t.txt")
print byte_len(b)
print byte_at(b, 1)
print byte_at(b, 2)
print byte_find(b, "é")
print byte_find(b, "llo")
print byte_find(b, "z")
print byte_at(b, -1)
""", want_out="6\n195\n169\n1\n3\n-1\n111\n")

# Bytes print/str render as Python b'...'
check("display_form", """
write_bytes("__D__/bin.dat", [72, 105, 128, 255, 10])
b = read_bytes("__D__/bin.dat")
print b
print str(b)
""", want_out="b'Hi\\x80\\xff\\n'\nb'Hi\\x80\\xff\\n'\n")

# Str byte_* behavior unchanged (pins existing UTF-8 re-encode semantics)
check("str_semantics_unchanged", """
print byte_len("é")
print byte_at("é", 0)
print byte_find("héllo", "ll")
""", want_out="2\n195\n3\n")

# Bytes equality is by payload and never equals Str
check("equality", """
write_bytes("__D__/bin.dat", [65, 66])
a = read_bytes("__D__/bin.dat")
b = read_bytes("__D__/bin.dat")
print a == b
print a != b
print a == "AB"
""", want_out="true\nfalse\nfalse\n")

# error surfaces
check("read_bytes_no_arg", "read_bytes()\n",
      want_err="read_bytes wants read_bytes(path)")
check("read_bytes_missing", 'b = read_bytes("__D__/nope.bin")\n',
      want_err="read_bytes failed:")
check("byte_at_oob", """
write_bytes("__D__/bin.dat", [1])
b = read_bytes("__D__/bin.dat")
print byte_at(b, 9)
""", want_err="index out of range")
check("byte_len_int", "print byte_len(5)\n",
      want_err="byte_len wants byte_len(s)")
check("bytes_in_arith", """
write_bytes("__D__/bin.dat", [1])
b = read_bytes("__D__/bin.dat")
print b + 1
""", want_err="Bytes")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
