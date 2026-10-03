#!/usr/bin/env python3
"""holyshit x86-64 backend tests: python3 tests/test_x64.py
Builds each tests/x64/<name>.hs to a static ELF (no gcc) and checks output.
Same .expected/.fail convention as test.py.
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from x64gen import build_x64

fails = 0
total = 0
with tempfile.TemporaryDirectory() as d:
    for prog in sorted(glob.glob(os.path.join(HERE, "x64", "*.hs"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue  # import helpers, built via their importers
        total += 1
        out = os.path.join(d, name)
        import io
        from contextlib import redirect_stderr, redirect_stdout
        err = io.StringIO()
        sout = io.StringIO()
        with redirect_stderr(err):
            with redirect_stdout(sout):
                try:
                    rc = build_x64(prog, out)
                except Exception as e:
                    print(str(e), file=err)
                    rc = 1
        build_noise = sout.getvalue()
        fail_path = os.path.join(HERE, "x64", name + ".fail")
        if rc != 0:
            if os.path.exists(fail_path):
                with open(fail_path, encoding="utf-8") as f:
                    want_err = f.read().strip()
                if want_err in err.getvalue():
                    print(f"ok   {name} (compile error as expected)")
                    continue
            print(f"FAIL {name}: build failed: {err.getvalue().strip()}")
            fails += 1
            continue
        try:
            r = subprocess.run([out], capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: timeout")
            fails += 1
            continue
        if os.path.exists(fail_path):
            with open(fail_path, encoding="utf-8") as f:
                want_err = f.read().strip()
            if r.returncode == 0:
                print(f"FAIL {name}: expected error, exited 0")
                fails += 1
            elif want_err in r.stderr.decode():
                print(f"ok   {name}")
            else:
                print(f"FAIL {name}: stderr {r.stderr.decode()!r} lacks {want_err!r}")
                fails += 1
            continue
        with open(os.path.join(HERE, "x64", name + ".expected"), encoding="utf-8") as f:
            want = f.read()
        got = r.stdout.decode()
        if r.returncode != 0:
            print(f"FAIL {name}: exit {r.returncode}, stderr: {r.stderr.decode().strip()}")
            fails += 1
        elif got != want:
            print(f"FAIL {name}:\n--- want ---\n{want}--- got ---\n{got}---")
            fails += 1
        else:
            print(f"ok   {name}")

print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
