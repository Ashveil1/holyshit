#!/usr/bin/env python3
"""JIT corpus parity gate: python3 tests/test_jit_corpus.py

Builds the eager in-process JIT driver (selfhost/be/jit_run.holy) once, then
runs every runnable tests/<name>.holy through BOTH the interpreter and the
JIT driver and compares (exit code, stdout, stderr) byte for byte.

Every corpus entry is classified:
- parity:     must match the interpreter byte for byte (the gate)
- divergence: documented native/JIT-vs-interp difference, asserted NOT to be
              byte-equal so a future fix forces reclassification here and in
              docs/jit-corpus.md
mod_*.holy helpers and *.nativeonly programs follow the other runners and
are not executed directly.
"""
import functools
import glob
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DIVERGENCE = {
    "err_umix": "interp rejects I64+U64 mixing; the x64 subset accepts it "
                "(roadmap 3.4, needs an owner decision)",
    "t_bits": "62-bit x64 Int vs 64-bit interpreter Int "
              "(roadmap 3.4, needs an owner decision)",
    "t_circ": "interp nests 'in module' prefixes on loader errors; the "
              "self-hosted loader reports the innermost error only",
    "t_ffi": "the JIT driver cannot bind C-source externs "
             "(extern from \"file.c\"); library externs work and the Python "
             "native path covers C sources via gcc (test_native.py)",
    "t_sock": "the self-hosted x64 backend has no socket/http/ticks runtime "
              "support yet; the Python native path covers it (test_native.py)",
}


def _start_www():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    h = functools.partial(Quiet, directory=os.path.join(HERE, "www"))
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
    # per-test env overlay: tests/<name>.env has KEY=VAL lines (# comments ok)
    e = dict(_BASE_ENV)
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


def _run(cmd, stdin, env):
    # t_fs uses a fixed scratch dir: start clean so ls() is deterministic.
    shutil.rmtree("/tmp/opencode/hs_fs_test", ignore_errors=True)
    r = subprocess.run(cmd, input=stdin, capture_output=True, timeout=120,
                       env=env, cwd=ROOT)
    return (r.returncode, r.stdout, r.stderr)


fails = 0
total = 0
with tempfile.TemporaryDirectory(prefix="hs-jit-corpus.") as d:
    driver = os.path.join(d, "jit")
    r = subprocess.run([os.path.join(ROOT, "bootstrap", "hs-hosted-x86_64"),
                        os.path.join(ROOT, "selfhost", "be", "jit_run.holy"),
                        driver],
                       capture_output=True, timeout=600, env=_BASE_ENV)
    if r.returncode != 0:
        print(f"FAIL jit driver build: {r.stderr.decode().strip()[-400:]}")
        sys.exit(1)
    for prog in sorted(glob.glob(os.path.join(HERE, "*.holy"))):
        name = os.path.splitext(os.path.basename(prog))[0]
        if name.startswith("mod_"):
            continue  # helper module, imported by other tests, never run directly
        if os.path.exists(os.path.join(HERE, name + ".nativeonly")):
            continue  # interp skips these; no reference to compare against
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
        env = _test_env(name)
        try:
            ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog] + pargs, stdin, env)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: interpreter timeout")
            fails += 1
            continue
        try:
            got = _run([driver, prog] + pargs, stdin, env)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: JIT timeout")
            fails += 1
            continue
        same = ref == got
        if name in DIVERGENCE:
            if same:
                print(f"FAIL {name}: now byte-identical to interp; move it out "
                      f"of DIVERGENCE (was: {DIVERGENCE[name]})")
                fails += 1
            else:
                print(f"ok   {name} (documented divergence)")
            continue
        if not same:
            print(f"FAIL {name}: rc {ref[0]} -> {got[0]}\n"
                  f"--- interp stdout ---\n{ref[1].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- jit stdout ---\n{got[1].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- interp stderr ---\n{ref[2].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- jit stderr ---\n{got[2].decode('utf-8', 'replace')[-400:]}")
            fails += 1
            continue
        print(f"ok   {name}")

if fails:
    print(f"{total - fails}/{total} jit corpus parity")
    sys.exit(1)
print(f"{total}/{total} jit corpus parity")
