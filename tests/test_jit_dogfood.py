#!/usr/bin/env python3
"""JIT self-compile gate: python3 tests/test_jit_dogfood.py

The eager JIT driver compiles the self-hosted compiler (compile.holy)
fully in memory - no Python, no gcc at run time - and the JIT-compiled
compiler then builds a program whose output matches the interpreter byte
for byte. A second driver run must hit the .hsc code cache (the cache
file is not rewritten) and produce an identical result.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ENV = dict(os.environ,
           HSROOT=ROOT,
           HSPATH=os.pathsep.join([os.path.join(ROOT, "selfhost"),
                                   os.path.join(ROOT, "selfhost", "be")]))

HELLO = 'print "dogfood ok"\nprint 6 * 7\n'

fails = 0
with tempfile.TemporaryDirectory(prefix="hs jit dogfood ") as d:
    driver = os.path.join(d, "jit")
    r = subprocess.run([os.path.join(ROOT, "bootstrap", "hs-hosted-x86_64"),
                        os.path.join(ROOT, "selfhost", "be", "jit_run.holy"),
                        driver],
                       capture_output=True, timeout=600, env=ENV)
    if r.returncode != 0:
        print("FAIL jit driver build:", r.stderr.decode().strip()[-400:])
        sys.exit(1)

    # A private copy of the compiler source, so the code cache lands in the
    # sandbox instead of the repo tree.
    src = os.path.join(d, "compile.holy")
    with open(os.path.join(ROOT, "selfhost", "be", "compile.holy"), "rb") as f:
        data = f.read()
    with open(src, "wb") as f:
        f.write(data)
    hello = os.path.join(d, "hello.holy")
    with open(hello, "w") as f:
        f.write(HELLO)

    ref = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"),
                          hello], capture_output=True, timeout=60)
    want_out, want_rc = ref.stdout, ref.returncode

    hsc = src[:-5] + ".hsc"
    built = []
    for i in (1, 2):
        out = os.path.join(d, f"hello{i}")
        r = subprocess.run([driver, src, hello, out],
                           capture_output=True, timeout=900, env=ENV)
        if r.returncode != 0:
            fails += 1
            print(f"FAIL dogfood compile run {i}:", r.returncode,
                  r.stderr.decode(errors="replace")[-400:])
            break
        e = subprocess.run([out], capture_output=True, timeout=60)
        if e.returncode != want_rc or e.stdout != want_out:
            fails += 1
            print(f"FAIL dogfood output run {i}:", e.returncode,
                  repr(e.stdout), "want", want_rc, repr(want_out))
            break
        built.append(out)
        if i == 1 and not os.path.isfile(hsc):
            fails += 1
            print("FAIL dogfood: no .hsc code cache written")
            break
    if len(built) == 2:
        # A cache hit neither recompiles nor rewrites the cache file.
        if len(open(hsc, "rb").read()) <= 0:
            fails += 1
            print("FAIL dogfood: empty .hsc")

    if fails == 0:
        m1 = os.stat(hsc).st_mtime_ns
        r = subprocess.run([driver, src, hello, os.path.join(d, "hello3")],
                           capture_output=True, timeout=900, env=ENV)
        m2 = os.stat(hsc).st_mtime_ns
        if r.returncode != 0 or m1 != m2:
            fails += 1
            print("FAIL dogfood warm re-run:", r.returncode,
                  "cache mtime changed" if m1 != m2 else "rc")

total = 4
print(f"{total - fails}/{total} jit dogfood self-compile")
sys.exit(1 if fails else 0)
