#!/usr/bin/env python3
"""selfhost/elf.holy (ELF writer in hs) must emit exactly the bytes of x64.py's
layout()/pack() for static images."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import x64  # noqa: E402

cases = [(b"\xc3", b"", 0), (bytes(range(256)) * 20, b"\x01\x02\x03", 7),
         (b"\x90" * 3000, bytes(5000), 100), (b"\x90" * 4000, b"x" * 9, 0)]
ok = True
for code, data, entry in cases:
    want = x64.pack(code, data, entry, x64.layout(len(code), len(data))).hex()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.txt")
        open(p, "w").write(f"{entry}\n{code.hex()}\n{data.hex()}\n")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "run",
                            os.path.join(ROOT, "selfhost", "elf_run.holy"),
                            "--backend", "interp", p], capture_output=True, text=True)
    if r.stdout.strip() != want:
        ok = False
        print("FAIL elf.holy vs x64.py", len(code), len(data), r.stderr[-200:])
if ok:
    print(f"ok   elf.holy == x64.py on {len(cases)} images")
print("1/1 passed" if ok else "0/1 passed")
sys.exit(0 if ok else 1)
