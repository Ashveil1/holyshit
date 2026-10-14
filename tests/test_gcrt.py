#!/usr/bin/env python3
"""selfhost/gcrt.hs (allocator + GC emitter written in hs) must emit exactly
the machine code and data of gcrt.py."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import gcrt  # noqa: E402
import x64  # noqa: E402


class G:
    def __init__(self):
        self.a = x64.Asm()
        self.n = 0

    def new_tmp(self, pfx="t"):
        self.n += 1
        return f"{pfx}{self.n}"


g = G()
g.a.data_label("gc_data_lo")
g.a.data_label("bump_ptr_")
g.a.data_qword(0)
g.a.data_label("bump_end_")
g.a.data_qword(0)
g.a.data_label("gc_data_hi")
gcrt.gc_data(g.a)
gcrt.emit_gc_malloc(g)
want = g.a.resolve(0x400000, 0x500000).hex() + " " + bytes(g.a.data).hex()
r = subprocess.run([sys.executable, os.path.join(ROOT, "hs.py"), "run",
                    os.path.join(ROOT, "selfhost", "gcrt_run.hs"),
                    "--backend", "interp"], capture_output=True, text=True)
got = r.stdout.strip()
ok = r.returncode == 0 and got == want
if ok:
    print(f"ok   gcrt.hs == gcrt.py ({len(want.split()[0]) // 2} code bytes)")
else:
    print("FAIL gcrt.hs vs gcrt.py", r.returncode, r.stderr[-400:])
    c, w = got.split(" ")[0], want.split(" ")[0]
    n = next((i for i in range(min(len(c), len(w))) if c[i] != w[i]), None)
    print("first code diff at hex offset", n, len(c), len(w))
print("1/1 passed" if ok else "0/1 passed")
sys.exit(0 if ok else 1)
