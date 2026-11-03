#!/usr/bin/env python3
"""Bytes type, stage 1 (user-approved representation option A: Unicode Str +
separate Bytes). Interp-only and purely additive:

- read_bytes(path) -> Bytes: the missing raw-read primitive. Lossless by
  construction - no decoding, so no invalid-byte policy is decided here.
- byte_len/byte_find/byte_at accept Bytes in addition to Str. Str behavior
  is unchanged (UTF-8 re-encode semantics stay pinned by test_byteops.py
  and test_rawbytes.py).
- len(Bytes) is the byte count; print/str render Bytes as Python b'...'.

be.holy (the self-hosted backend, stage 3b) knows Bytes too: the "be"
backend rows below compile with the pinned seed compiler, and the be
emission-gating fixtures pin its uses_bytes scan (same closed-world
producer rule as the x64 backends). Stage 4 flips tcp_recv/http_get to
lossless Bytes on the hosted backends (interp + native): no decoding
happens at the boundary, so no invalid-byte policy is decided there.
read_mem keeps its documented latin-1 Str bridge; read_text keeps its
pinned strict language error on invalid UTF-8.
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
INTERP = os.path.join(ROOT, "interp.py")

fails = 0
total = 0


HS = os.path.join(ROOT, "hs.py")
BACKENDS = ("interp", "native", "x64", "x64-ast")
SEED = os.path.join(ROOT, "bootstrap", "hs-hosted-x86_64")
# the hosted (be) compiler joins the matrix when the pinned seed exists
if os.path.exists(SEED):
    BACKENDS = BACKENDS + ("be",)


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
        elif backend == "x64-ast":
            out = os.path.join(d, "prog-bin")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = x64gen.build_x64_ast(p, out)
            if rc != 0:
                return rc, "", err.getvalue()
            cmd = [out]
        elif backend == "be":
            out = os.path.join(d, "prog-bin")
            env = dict(os.environ, HSROOT=ROOT,
                       HSPATH=os.path.join(ROOT, "selfhost") + ":" +
                       os.path.join(ROOT, "selfhost", "be"))
            c = subprocess.run([SEED, p, out], capture_output=True,
                               timeout=120, env=env)
            if c.returncode != 0:
                return c.returncode, "", c.stderr.decode("utf-8", "replace")
            cmd = [out]
        else:
            cmd = [sys.executable, HS, "run", p, "--backend", backend]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return r.returncode, r.stdout.decode("utf-8", "replace"), \
            r.stderr.decode("utf-8", "replace")


def check(name, src, want_out=None, want_err=None, files=None, backends=None):
    """want_err is one substring for every backend, or a per-backend dict
    (error surfaces legitimately differ per backend convention, pinned
    here like tests/test_rawbytes.py does)."""
    global fails, total
    for backend in (backends or BACKENDS):
        total += 1
        rc, out, err = run(src, files or {}, backend)
        if want_out is not None:
            ok = rc == 0 and out == want_out and not err
            detail = f"want_out={want_out!r} got={out!r} rc={rc} err={err[-200:]!r}"
        else:
            want = want_err[backend] if isinstance(want_err, dict) else want_err
            ok = rc != 0 and want in err
            detail = f"want_err={want!r} got_err={err[-200:]!r} rc={rc} out={out!r}"
        print(("ok  " if ok else "FAIL") + f" {name} [{backend}]")
        if not ok:
            fails += 1
            print("  " + detail)


# fixtures are written by the harness: x64-ast (the legacy AST-direct
# build kept for differential triage) has no write_bytes. The write->read
# roundtrip stays pinned where write_bytes exists (write_roundtrip below).
check("roundtrip_raw", """
b = read_bytes("__D__/bin.dat")
print byte_len(b)
print len(b)
print byte_at(b, 0)
print byte_at(b, 1)
print byte_at(b, 2)
print byte_at(b, 3)
print byte_at(b, 4)
""", want_out="5\n5\n72\n105\n128\n255\n10\n",
      files={"bin.dat": bytes([72, 105, 128, 255, 10])})

# write_bytes -> read_bytes roundtrip: invalid UTF-8 bytes survive.
# x64-ast is excluded: it never grew write_bytes (INLINE_ONLY in irx64).
check("write_roundtrip", """
write_bytes("__D__/out.dat", [0, 159, 146, 150])
b = read_bytes("__D__/out.dat")
print byte_len(b)
print byte_at(b, 0)
print byte_at(b, 3)
""", want_out="4\n0\n150\n", backends=("interp", "native", "x64", "be"))

# write_bytes accepts Bytes directly: verbatim persist, no int-list detour.
check("write_bytes_bytes_arg", """
b = read_bytes("__D__/bin.dat")
write_bytes("__D__/out2.dat", b)
r = read_bytes("__D__/out2.dat")
print byte_len(r)
print byte_at(r, 2)
print byte_at(r, 4)
write_bytes("__D__/empty2.dat", read_bytes("__D__/empty.dat"))
print byte_len(read_bytes("__D__/empty2.dat"))
try:
  write_bytes("__D__/x.dat", "s")
except as e:
  print e
""", want_out="5\n128\n10\n0\nwrite_bytes wants write_bytes(path, [Int 0..255]|bytes) at line 11\n",
      files={"bin.dat": bytes([72, 105, 128, 255, 10]), "empty.dat": b""},
      backends=("interp", "native", "x64", "be"))

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
b = read_bytes("__D__/bin.dat")
print b
print str(b)
""", want_out="b'Hi\\x80\\xff\\n'\nb'Hi\\x80\\xff\\n'\n",
      files={"bin.dat": bytes([72, 105, 128, 255, 10])})

# Str byte_* behavior unchanged (pins existing UTF-8 re-encode semantics)
check("str_semantics_unchanged", """
print byte_len("é")
print byte_at("é", 0)
print byte_find("héllo", "ll")
""", want_out="2\n195\n3\n")

# Bytes equality is by payload and never equals Str
check("equality", """
a = read_bytes("__D__/bin.dat")
b = read_bytes("__D__/bin.dat")
print a == b
print a != b
print a == "AB"
""", want_out="true\nfalse\nfalse\n", files={"bin.dat": bytes([65, 66])})

# error surfaces
check("read_bytes_no_arg", "read_bytes()\n",
      want_err="read_bytes wants read_bytes(path)")
check("read_bytes_missing", 'b = read_bytes("__D__/nope.bin")\n',
      want_err={"interp": "read_bytes failed:",
                "native": "read_bytes failed:",
                "x64": "open failed: errno 2",
                "x64-ast": "open failed: errno 2",
                "be": "open failed: errno 2"})
check("byte_at_oob", """
b = read_bytes("__D__/bin.dat")
print byte_at(b, 9)
""", want_err="index out of range", files={"bin.dat": bytes([1])})
check("byte_len_int", "print byte_len(5)\n",
      want_err="byte_len wants byte_len(s)")
check("bytes_in_arith", """
b = read_bytes("__D__/bin.dat")
print b + 1
""", want_err="Bytes", files={"bin.dat": bytes([1])})

# --- emission-neutrality and closed-world producer pins (x64 backends) ---

def build_img(src, files=None, ir=False, freestanding=False):
    """Compile src to an image; returns (rc, image_bytes_or_None, err)."""
    with tempfile.TemporaryDirectory() as d:
        for name, data in (files or {}).items():
            mode = "wb" if isinstance(data, bytes) else "w"
            with open(os.path.join(d, name), mode) as f:
                f.write(data)
        p = os.path.join(d, "prog.holy")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src.replace("__D__", d))
        out = os.path.join(d, "prog-bin")
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                if freestanding:
                    rc = x64gen.build_xkernel(p, out)
                elif ir:
                    rc = x64gen.build_x64(p, out)
                else:
                    rc = x64gen.build_x64_ast(p, out)
        except Exception as e:          # freestanding subset refusal
            return 1, None, str(e)
        if rc != 0:
            return rc, None, err.getvalue()
        with open(out, "rb") as f:
            return 0, f.read(), ""


def check_img(name, src, want_rodata, files=None, ir=False):
    """want_rodata=True: image must carry the Bytes rodata (flag on)."""
    global fails, total
    total += 1
    rc, img, err = build_img(src, files, ir=ir)
    ok = rc == 0 and img is not None and ((b"Bytes" in img) == want_rodata)
    print(("ok  " if ok else "FAIL") + f" {name}")
    if not ok:
        fails += 1
        print(f"  rc={rc} err={err[-160:]!r} rodata_want={want_rodata}")


# producer pin: BYTES_PRODUCERS is exactly {"read_bytes", "tcp_recv",
# "http_get"} (stage 4), and across both x64 generators the only K_BYTES
# tag WRITES are the two read_bytes re-tag sites (every other use is a
# comparison; tcp_recv/http_get tag inside native/rt.c, not in asm).
def check_producer_pin():
    global fails, total
    total += 1
    ok = x64gen.Gen.BYTES_PRODUCERS == frozenset({"read_bytes", "tcp_recv", "http_get"})
    writes = 0
    for path in ("x64gen.py", "irx64.py"):
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            src = f.read()
        n = src.count('mov_ri32("r11", Gen.K_BYTES)')
        ok = ok and src.count("K_BYTES") > 0
        writes += n
    ok = ok and writes == 2
    print(("ok  " if ok else "FAIL") + " producer_pin")
    if not ok:
        fails += 1
        print(f"  producers={x64gen.Gen.BYTES_PRODUCERS!r} tag_writes={writes}")


check_producer_pin()

# Str-only program: Bytes runtime is not emitted at all (byte-identical
# to the pre-Bytes emitter; the oracle/seed suites pin the full images).
for ir in (False, True):
    check_img(f"emission_gating_str_only[{'ir' if ir else 'ast'}]",
              'print byte_len("hi")\n', want_rodata=False, ir=ir)

# import-only: the read_bytes call lives in an imported module; the scan
# must still turn the flag on (image carries the runtime, program works).
for ir in (False, True):
    check_img(f"emission_gating_import[{'ir' if ir else 'ast'}]",
              'import helper\nb = helper.load()\nprint byte_len(b)\n',
              want_rodata=True, ir=ir,
              files={"helper.holy": 'def load():\n    return read_bytes("__D__/bin.dat")\n',
                     "bin.dat": bytes([1, 2, 3])})

# shadowed: a user def named read_bytes shadows the builtin; the call
# resolves to user code, so no Bytes can exist and the flag stays off.
for ir in (False, True):
    check_img(f"emission_gating_shadowed[{'ir' if ir else 'ast'}]",
              'def read_bytes(path):\n    return 41\nprint read_bytes("x") + 1\n',
              want_rodata=False, ir=ir)

# stage-4 producers: tcp_recv/http_get are hosted-only builtins (not in the
# x64 subset), so a raw call cannot appear in x64/be-compiled code; the
# widened producer set is pinned by check_producer_pin plus the shadow
# fixtures below, and the value-level flip is pinned by t_sock. A user def
# named after a stage-4 producer shadows it: gate off.
for ir in (False, True):
    check_img(f"emission_gating_shadowed_tcp[{'ir' if ir else 'ast'}]",
              'def tcp_recv(s, n):\n    return 41\nprint tcp_recv("x", 1) + 1\n',
              want_rodata=False, ir=ir)

# freestanding reject: read_bytes is refused with the x64-subset error,
# exactly like the other hosted-only helpers.
def check_freestanding_reject():
    global fails, total
    total += 1
    rc, img, err = build_img('b = read_bytes("/x")\n', freestanding=True)
    ok = rc != 0 and "not in x64 subset" in err
    print(("ok  " if ok else "FAIL") + " freestanding_reject")
    if not ok:
        fails += 1
        print(f"  rc={rc} err={err[-160:]!r}")


check_freestanding_reject()



# --- be (hosted compiler) emission gating: the translated uses_bytes scan ---

def be_compile(src, files=None, extra_path=None):
    """Compile src with the pinned hosted (be) compiler; returns
    (rc, image_bytes_or_None, err)."""
    with tempfile.TemporaryDirectory() as d:
        for name, data in (files or {}).items():
            mode = "wb" if isinstance(data, bytes) else "w"
            with open(os.path.join(d, name), mode) as f:
                f.write(data)
        p = os.path.join(d, "prog.holy")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src.replace("__D__", d))
        out = os.path.join(d, "prog-bin")
        env = dict(os.environ, HSROOT=ROOT,
                   HSPATH=(extra_path or "") + os.path.join(ROOT, "selfhost") +
                   ":" + os.path.join(ROOT, "selfhost", "be"))
        r = subprocess.run([SEED, p, out], capture_output=True, timeout=120,
                           env=env)
        img = None
        if r.returncode == 0 and os.path.exists(out):
            with open(out, "rb") as f:
                img = f.read()
        return r.returncode, img, r.stderr.decode("utf-8", "replace")


def check_be_img(name, src, want_bytes_rodata, files=None, extra_path=None):
    global fails, total
    if not os.path.exists(SEED):
        return
    total += 1
    rc, img, err = be_compile(src, files, extra_path)
    ok = rc == 0 and img is not None and ((b"Bytes" in img) == want_bytes_rodata)
    print(("ok  " if ok else "FAIL") + f" {name} [be]")
    if not ok:
        fails += 1
        print(f"  rc={rc} has_Bytes={(img is not None and b'Bytes' in img)} "
              f"want={want_bytes_rodata} err={err[-200:]!r}")


check_be_img("be_emission_gating_str_only",
             'print byte_len("abc")\n', False)
check_be_img("be_emission_gating_bytes",
             'b = read_bytes("/etc/hostname")\nprint byte_len(b)\n', True)
# producer-named PARAMETER is the true param-shadow case: gate must stay OFF
# (x64gen: Gen.BYTES_PRODUCERS & set(params) non-empty -> body scan suppressed)
check_be_img("be_emission_gating_param_shadowed",
             'def f(read_bytes):\n  return read_bytes("/etc/hostname")\nprint "ok"\n',
             False)
# and a def WITHOUT shadowing that calls the producer: gate must turn ON
check_be_img("be_emission_gating_def_body",
             'def go():\n  return byte_len(read_bytes("/etc/hostname"))\nprint go()\n',
             True)
check_be_img("be_emission_gating_shadowed",
             'def read_bytes(p):\n  return "s"\nprint read_bytes("x")\n',
             False)
# same shadow rule for a stage-4 producer name through be
check_be_img("be_emission_gating_shadowed_tcp",
             'def tcp_recv(s, n):\n  return "s"\nprint tcp_recv("x", 1)\n',
             False)
def check_be_img_import():
    """import fixture needs the module dir on HSPATH."""
    global fails, total
    if not os.path.exists(SEED):
        return
    total += 1
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "helper.holy"), "w") as f:
            f.write('def go():\n  return byte_len(read_bytes("/etc/hostname"))\n')
        p = os.path.join(d, "prog.holy")
        with open(p, "w") as f:
            f.write("import helper\nprint helper.go()\n")
        out = os.path.join(d, "prog-bin")
        env = dict(os.environ, HSROOT=ROOT,
                   HSPATH=d + ":" + os.path.join(ROOT, "selfhost") + ":" +
                   os.path.join(ROOT, "selfhost", "be"))
        r = subprocess.run([SEED, p, out], capture_output=True, timeout=120,
                           env=env)
        img = open(out, "rb").read() if r.returncode == 0 else None
        ok = img is not None and b"Bytes" in img
        print(("ok  " if ok else "FAIL") + " be_emission_gating_import [be]")
        if not ok:
            fails += 1
            print(f"  rc={r.returncode} err={r.stderr[-200:]!r}")


check_be_img_import()

# read_bytes as a value is a compile error through be as well
def check_be_not_a_value():
    global fails, total
    if not os.path.exists(SEED):
        return
    total += 1
    rc, img, err = be_compile("f = read_bytes\n")
    ok = rc != 0 and "not a value" in err
    print(("ok  " if ok else "FAIL") + " be_read_bytes_not_a_value [be]")
    if not ok:
        fails += 1
        print(f"  rc={rc} err={err[-200:]!r}")


check_be_not_a_value()

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
