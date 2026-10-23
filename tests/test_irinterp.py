#!/usr/bin/env python3
"""irinterp parity gate: python3 tests/test_irinterp.py

Builds the hs-written IR interpreter tier (selfhost/be/irinterp_run.holy) and
runs every runnable tests/<name>.holy through both interp.py and the driver,
comparing (exit code, stdout, stderr) byte for byte.

- parity:     must match interp.py byte for byte
- refused:    the driver refuses up front (rc 3, "error: irinterp: unsupported
              ...") before running anything: unsafe/ffi ops and
              builtins outside the supported subset. Pinned so adding support
              forces a move into parity.
- divergence: documented difference, asserted NOT byte-equal
"""
import argparse
import functools
import glob
import http.server
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--arm64-qemu", metavar="PATH",
                    help="build an AArch64 driver and execute it with this QEMU")
OPTIONS = parser.parse_args()
ARM64 = bool(OPTIONS.arm64_qemu) or platform.machine() in ("aarch64", "arm64")




REFUSED = set(['err_fficall', 'err_ffitype', 'err_structfield', 'err_umix', 't_bitmap', 't_bits', 't_ffi', 't_ffimod', 't_ffistruct', 't_ffivariadic', 't_heap', 't_readmem', 't_sock', 't_struct', 'uasm', 'ufunc', 'unsafe'])
DIVERGENCE = {
    "t_load64": "hosted Int is 62-bit; interp.py is 64-bit (roadmap 3.4)",
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
with tempfile.TemporaryDirectory(prefix="hs-irinterp.") as d:
    driver = os.path.join(d, "irinterp")
    # The pinned seed is x86-64. On arm64 use the reference A64 stage0
    # to build a native hs interpreter; program execution itself is in hs.
    builder = ([sys.executable, os.path.join(ROOT, "a64build.py")]
               if ARM64 else
               [os.path.join(ROOT, "bootstrap", "hs-hosted-x86_64")])
    r = subprocess.run(builder + [
                        os.path.join(ROOT, "selfhost", "be", "irinterp_run.holy"),
                        driver],
                       capture_output=True, timeout=600, env=_BASE_ENV)
    if r.returncode != 0:
        print(f"FAIL irinterp driver build: {r.stderr.decode().strip()[-400:]}")
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
            got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                       [driver, prog] + pargs, stdin, env)
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: irinterp timeout")
            fails += 1
            continue
        same = ref == got
        refused = got[0] == 3 and got[2].startswith(b"error: irinterp: unsupported")
        if name in REFUSED:
            if refused and got[1] == b"":
                print(f"ok   {name} (refused)")
            else:
                print(f"FAIL {name}: expected an up-front refusal (rc 3), got rc {got[0]}")
                fails += 1
            continue
        if refused:
            print(f"FAIL {name}: refused ({got[2].decode().strip()}); add to REFUSED or fix")
            fails += 1
            continue
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
                  f"--- irinterp stdout ---\n{got[1].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- interp stderr ---\n{ref[2].decode('utf-8', 'replace')[-400:]}\n"
                  f"--- irinterp stderr ---\n{got[2].decode('utf-8', 'replace')[-400:]}")
            fails += 1
            continue
        print(f"ok   {name}")

if fails:
    print(f"{total - fails}/{total} irinterp parity")
    sys.exit(1)
print(f"{total}/{total} irinterp parity")
