#!/usr/bin/env python3
"""pylex (C2.1): hs Python-subset lexer matches CPython tokenize byte for byte.

Differential: selfhost/py/pylex_run.holy (via interp.py) vs
selfhost/py/dump_pylex.py (CPython tokenize oracle) over the frozen py2hs
corpus and the real translation targets x64.py, irx64.py, x64gen.py.
Also pins the fail-closed error surface for out-of-subset sources.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "selfhost", "py", "pylex_run.holy")
ORACLE = os.path.join(ROOT, "selfhost", "py", "dump_pylex.py")
CORPUS = os.path.join(ROOT, "tests", "py2hs_corpus")
TARGETS = [os.path.join(ROOT, f) for f in ("x64.py", "irx64.py", "x64gen.py")]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace")


def main():
    total = 0
    files = sorted(
        os.path.join(CORPUS, f) for f in os.listdir(CORPUS) if f.endswith(".py"))
    for f in files + TARGETS:
        want = run([sys.executable, ORACLE, f])
        got = run([sys.executable, os.path.join(ROOT, "interp.py"), DRIVER, f])
        assert want.returncode == 0, (f, want.stderr)
        assert got.returncode == 0, (f, got.stdout, got.stderr)
        assert got.stdout == want.stdout, (f,)
        total += 1
        print(f"ok   pylex {os.path.basename(f)}")
    bad_sources = [
        'a = "unterminated\n',
        'a = f"{x + \\n}"\n',
        'a = f"{ {1:2} }"\n',
        '\ta = 1\n',
        'a = 1__0x\n',
    ]
    for src in bad_sources:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            tf.write(src)
            path = tf.name
        try:
            got = run([sys.executable, os.path.join(ROOT, "interp.py"), DRIVER, path])
            assert got.returncode != 0, (src, got.stdout)
            assert got.stdout.startswith("error: "), (src, got.stdout)
            total += 1
        finally:
            os.unlink(path)
    print(f"{total}/{total} pylex token-stream differentials + fail-closed errors")


if __name__ == "__main__":
    main()
