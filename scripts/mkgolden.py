#!/usr/bin/env python3
"""Regenerate the frozen golden corpus: python3 scripts/mkgolden.py

Runs every runnable tests/<name>.holy through the reference interpreter and
writes the exact (exit code, stdout, stderr) triple to
tests/golden/<name>.golden in a length-prefixed binary format:

    HSGOLD1\n
    rc=<int>\n
    stdout=<len>\n
    stderr=<len>\n
    \n<stdout bytes><stderr bytes>

These goldens are the frozen oracle for tests/test_golden.py, which gates
the seed-built JIT driver against them WITHOUT a live interpreter, so the
parity gate survives interp.py leaving CI. Regenerate intentionally (after a
deliberate interp behavior change), review the diff, and commit. Selection
and execution semantics mirror tests/test_jit_corpus.py exactly: mod_*.holy
helpers and *.nativeonly programs are skipped; per-test .env/.stdin/.args
files apply; the tests/www scratch server runs on an ephemeral port.
"""
import functools
import glob
import http.server
import os
import shutil
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(ROOT, "tests")
GOLDEN = os.path.join(TESTS, "golden")


def _start_www():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    h = functools.partial(Quiet, directory=os.path.join(TESTS, "www"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


_WWW = _start_www()
_PORT = _WWW.server_address[1]
_BASE_ENV = dict(os.environ)
_BASE_ENV["HS_WWW"] = f"http://127.0.0.1:{_PORT}"
_BASE_ENV["HS_WWW_PORT"] = str(_PORT)
_BASE_ENV["HSPATH"] = os.path.join(ROOT, "selfhost") + ":" + os.path.join(ROOT, "selfhost", "be")
_BASE_ENV["HSROOT"] = ROOT


def _test_env(name):
    e = dict(_BASE_ENV)
    p = os.path.join(TESTS, name + ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip()
    return e


def runnable_programs():
    for prog in sorted(glob.glob(os.path.join(TESTS, "*.holy"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue  # helper module, imported by other tests, never run directly
        if os.path.exists(os.path.join(TESTS, name + ".nativeonly")):
            continue  # interp skips these; no reference to record
        yield name, prog


def _run_interp(prog, stdin, env, pargs):
    # t_fs uses a fixed scratch dir: start clean so ls() is deterministic.
    shutil.rmtree("/tmp/opencode/hs_fs_test", ignore_errors=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "interp.py"), prog] + pargs,
                       input=stdin, capture_output=True, timeout=120,
                       env=env, cwd=ROOT)
    return (r.returncode, r.stdout, r.stderr)


def _golden_bytes(rc, out, err):
    head = f"HSGOLD1\nrc={rc}\nstdout={len(out)}\nstderr={len(err)}\n\n".encode()
    return head + out + err


def main():
    os.makedirs(GOLDEN, exist_ok=True)
    fails = 0
    total = 0
    for name, prog in runnable_programs():
        total += 1
        stdin = None
        sin_path = os.path.join(TESTS, name + ".stdin")
        if os.path.exists(sin_path):
            with open(sin_path, "rb") as f:
                stdin = f.read()
        pargs = []
        args_path = os.path.join(TESTS, name + ".args")
        if os.path.exists(args_path):
            with open(args_path, encoding="utf-8") as f:
                pargs = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
        try:
            rc, out, err = _run_interp(prog, stdin, _test_env(name), pargs)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: interpreter timeout")
            fails += 1
            continue
        with open(os.path.join(GOLDEN, name + ".golden"), "wb") as f:
            f.write(_golden_bytes(rc, out, err))
        print(f"ok   {name}")
    # stale goldens for removed programs are an error: delete intentionally
    for g in sorted(glob.glob(os.path.join(GOLDEN, "*.golden"))):
        name = os.path.splitext(os.path.basename(g))[0]
        if not os.path.exists(os.path.join(TESTS, name + ".holy")):
            print(f"STALE {name}.golden: no tests/{name}.holy - delete the golden intentionally")
            fails += 1
    if fails:
        print(f"{total - fails}/{total} goldens regenerated")
        sys.exit(1)
    print(f"{total}/{total} goldens regenerated")


if __name__ == "__main__":
    main()
