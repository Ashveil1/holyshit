#!/usr/bin/env python3
"""holyshit native test runner: python3 tests/test_native.py
Builds each tests/<name>.holy to a native binary and checks output.
Same .expected/.stdin/.fail convention as test.py.
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from hs import build


def _start_www():
    # local fixture server for t_sock (http_get + raw tcp); ephemeral port.
    import functools
    import http.server
    import threading

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    h = functools.partial(Quiet, directory=os.path.join(HERE, "www"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


_WWW = _start_www()
_PORT = _WWW.server_address[1]
_CHILD_ENV = dict(os.environ)
_CHILD_ENV["HS_WWW"] = f"http://127.0.0.1:{_PORT}"
_CHILD_ENV["HS_WWW_PORT"] = str(_PORT)

# t_fs uses a fixed scratch dir: start clean so ls() is deterministic.
import shutil
shutil.rmtree("/tmp/opencode/hs_fs_test", ignore_errors=True)


def _test_env(name):
    # per-test env overlay: tests/<name>.env has KEY=VAL lines (# comments ok)
    e = dict(_CHILD_ENV)
    p = os.path.join(HERE, name + ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip()
    return e

fails = 0
total = 0
with tempfile.TemporaryDirectory() as d:
    for prog in sorted(glob.glob(os.path.join(HERE, "*.holy"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue  # helper module, imported by other tests, never built directly
        total += 1
        out = os.path.join(d, name)
        sin_path = os.path.join(HERE, name + ".stdin")
        stdin = None
        if os.path.exists(sin_path):
            with open(sin_path, "rb") as f:
                stdin = f.read()
        pargs = []
        args_path = os.path.join(HERE, name + ".args")
        if os.path.exists(args_path):
            with open(args_path, encoding="utf-8") as f:
                pargs = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
        # capture build errors (compile error counts as nonzero exit)
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        tenv = _test_env(name)
        old_env = dict(os.environ)
        os.environ.update(tenv)  # HSPATH affects build-time imports
        try:
            with redirect_stderr(err):
                rc = build(prog, out)
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        fail_path = os.path.join(HERE, name + ".fail")
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
            r = subprocess.run([out] + pargs, input=stdin, capture_output=True, timeout=60,
                               env=tenv)
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
        with open(os.path.join(HERE, name + ".expected"), encoding="utf-8") as f:
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
