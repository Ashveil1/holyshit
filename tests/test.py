#!/usr/bin/env python3
"""holyshit test runner: python3 tests/test.py
Each test = tests/<name>.holy + tests/<name>.expected (stdout).
Optional: tests/<name>.stdin (fed to stdin), tests/<name>.fail (expects
nonzero exit; compares stderr instead of stdout).
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INTERP = os.path.join(ROOT, "interp.py")


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
for prog in sorted(glob.glob(os.path.join(HERE, "*.holy"))):
    name = os.path.splitext(os.path.basename(prog))[0]
    if name.startswith("mod_"):
        continue  # helper module, imported by other tests, never run directly
    if os.path.exists(os.path.join(HERE, name + ".nativeonly")):
        print(f"skip {name} (native only)")
        continue
    total += 1
    stdin = None
    sin_path = os.path.join(HERE, name + ".stdin")
    if os.path.exists(sin_path):
        with open(sin_path, "rb") as f:
            stdin = f.read()
    pargs = []
    args_path = os.path.join(HERE, name + ".args")
    if os.path.exists(args_path):
        with open(args_path, encoding="utf-8") as f:
            pargs = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
    r = subprocess.run([sys.executable, INTERP, prog] + pargs, input=stdin,
                       capture_output=True, timeout=60, env=_test_env(name))
    fail_path = os.path.join(HERE, name + ".fail")
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
