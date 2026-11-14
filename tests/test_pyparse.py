#!/usr/bin/env python3
"""pyparse (C2.2): hs Python-subset parser matches CPython ast byte for byte.

Differential: selfhost/py/pyparse_run.holy (via interp.py) vs
selfhost/py/dump_pyast.py (CPython 3.11 ast oracle) over the frozen py2hs
corpus and the real translation targets x64.py, irx64.py, x64gen.py, using
the canonical S-expression dump of selfhost/py/pydump.holy's PYDUMP_SCHEMA.
Async comprehensions and dict-merge parse into marked nodes like CPython
(the pygen translator rejects them, matching py2hs); also pins fail-closed
syntax errors.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "selfhost", "py", "pyparse_run.holy")
ORACLE = os.path.join(ROOT, "selfhost", "py", "dump_pyast.py")
CORPUS = os.path.join(ROOT, "tests", "py2hs_corpus")
TARGETS = [os.path.join(ROOT, f) for f in ("x64.py", "irx64.py", "x64gen.py")]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace")


def main():
    total = 0
    files = sorted(
        os.path.join(CORPUS, f) for f in os.listdir(CORPUS) if f.endswith(".py"))
    for f in files + TARGETS:
        got = run([sys.executable, os.path.join(ROOT, "interp.py"), DRIVER, f])
        want = run([sys.executable, ORACLE, f])
        assert want.returncode == 0, (f, want.stderr)
        assert got.returncode == 0, (f, got.stdout, got.stderr)
        assert got.stdout == want.stdout, (f,)
        total += 1
        print(f"ok   pyparse {os.path.basename(f)}")
    bad_sources = [
        '@dec\ndef f():\n    pass\n',
        'async def f():\n    pass\n',
        'f(**kw)\n',
        'a = f"{ {1:2} }"\n',
        'for (name, n), label in xs:\n    pass\n',  # must PARSE (nested tuple target)
    ]
    for src in bad_sources[:-1]:
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
    # nested tuple for-target parses (regression: x64gen.py:7480)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(bad_sources[-1])
        path = tf.name
    try:
        want = run([sys.executable, ORACLE, path])
        got = run([sys.executable, os.path.join(ROOT, "interp.py"), DRIVER, path])
        assert want.returncode == 0 and got.returncode == 0, (want.stderr, got.stdout)
        assert got.stdout == want.stdout, (src,)
        total += 1
    finally:
        os.unlink(path)
    print(f"{total}/{total} pyparse AST differentials + fail-closed errors")


if __name__ == "__main__":
    main()
