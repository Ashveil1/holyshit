#!/usr/bin/env python3
"""Native repl differential: python3 tests/test_repl_native.py
Builds selfhost/repl.holy with xbuild and runs scripted stdin sessions
against it and `python3 interp.py --repl` (non-tty, so no prompts/banner),
requiring byte-identical stdout and exit codes. The one pinned deviation is
unsafe/ffi input: refused up front by the native session (irinterp
preflight), executed by the CPython interpreter.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = 0
total = 0


def check(name, cond, detail=""):
    global fails, total
    total += 1
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        fails += 1


SESSIONS = {
    "arith_vars": "1 + 1\nx = 5\nx * 3\n",
    "def_call": "def f(a):\n  return a * 2\n\nf(21)\n",
    "closures": "def make(n):\n  def add(x):\n    return x + n\n"
                "  return add\n\ng = make(10)\ng(5)\n",
    "recursion": "def fib(n):\n  if n < 2:\n    return n\n"
                 "  return fib(n - 1) + fib(n - 2)\n\nfib(10)\n",
    "displays": "[1, \"a\", true]\n{\"k\": 1}\nnull\n1.5 + 1\n1.0\n"
                "\"hello\"\n0 - 3\ntrue\n[1, [2, {\"a\": \"b\"}]]\n\"q\\\"q\"\n",
    "runtime_errors": "1 / 0\ny_undefined\n2 + 2\n",
    "parse_error": "def broken(:\n5 + 5\n",
    "try_raise": "try:\n  raise \"boom\"\nexcept as e:\n  print \"caught\", e\n"
                 "\n6 * 7\n",
    "print_stmt": "print(\"side\", 7)\n",
    "comments_blanks": "# a comment\n\n4 + 4\n",
    "eof_in_block": "def f():\n  return 1\n",
    "loop_state": "total = 0\nfor i in range(4):\n  total = total + i\n"
                  "\ntotal\n",
}

UNSAFE_SESSION = "unsafe:\n  Ptr p = alloc(8)\n\n4 + 4\n"


def run(argv, script, cwd):
    return subprocess.run(argv, input=script, capture_output=True,
                          text=True, cwd=cwd, timeout=60)


def main():
    with tempfile.TemporaryDirectory() as td:
        exe = os.path.join(td, "hs_repl_native")
        env = dict(os.environ)
        env["HSPATH"] = os.path.join(ROOT, "selfhost") + os.pathsep + \
            os.path.join(ROOT, "selfhost", "be")
        env["HSROOT"] = ROOT
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "hs.py"), "xbuild",
             os.path.join(ROOT, "selfhost", "repl.holy"), "-o", exe],
            capture_output=True, text=True, env=env)
        check("native repl builds", r.returncode == 0 and os.path.exists(exe),
              (r.stdout + r.stderr)[-200:])
        if r.returncode != 0 or not os.path.exists(exe):
            print(f"{total - fails}/{total} passed")
            sys.exit(1)

        with open(os.path.join(td, "support.holy"), "w",
                  encoding="utf-8") as f:
            f.write("value = 19\n")

        py_argv = [sys.executable, os.path.join(ROOT, "interp.py"), "--repl"]
        sessions = dict(SESSIONS)
        sessions["import_attr_error"] = "import support\nsupport.value\n"
        for name, script in sorted(sessions.items()):
            py = run(py_argv, script, td)
            hs = run([exe], script, td)
            check(f"session {name}",
                  (py.returncode, py.stdout, py.stderr)
                  == (hs.returncode, hs.stdout, hs.stderr),
                  f"\n  py: {py.returncode} {py.stdout!r} {py.stderr[-120:]!r}"
                  f"\n  hs: {hs.returncode} {hs.stdout!r} {hs.stderr[-120:]!r}")

        # Pinned deviation: a file using unsafe ops runs under the CPython
        # interpreter; the native session refuses it up front and goes on.
        py = run(py_argv, UNSAFE_SESSION, td)
        hs = run([exe], UNSAFE_SESSION, td)
        check("pinned deviation: unsafe refused natively, runs under Python",
              py.returncode == 0 and py.stdout == "8\n"
              and hs.returncode == 0
              and hs.stdout.startswith("error: irinterp: unsupported ")
              and hs.stdout.endswith("8\n"),
              f"\n  py: {py.returncode} {py.stdout!r}"
              f"\n  hs: {hs.returncode} {hs.stdout!r}")

    print(f"{total - fails}/{total} passed")
    sys.exit(bool(fails))


if __name__ == "__main__":
    main()
