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


    # Wrong arity must be rejected before indexing arguments or calling the
    # host. Test indirect calls too: the source compiler cannot pre-check them.
    builtin_names = ["len", "str", "int", "float", "range", "append", "split",
                     "find", "join", "has", "contains", "keys", "values",
                     "read_text", "write_text", "append_text", "exists", "ls",
                     "mkdir", "env", "argv", "input", "json_parse", "json_str",
                     "json_load", "json_save", "open", "read", "write", "close", "system"]
    arity_total = 0
    for name in builtin_names:
        for count in ([1, 4] if name in ("argv", "input") else [0, 4]):
            for caught in (False, True):
                expression = "f(" + ", ".join(["null"] * count) + ")"
                source = "f = " + name + "\n"
                if caught:
                    source += 'try:\n  ' + expression + '\nexcept as e:\n  print e\nprint "after"\n'
                else:
                    source += expression + '\nprint "unreachable"\n'
                prog = os.path.join(d, "arity.holy")
                with open(prog, "w") as f:
                    f.write(source)
                ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
                got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                           [driver, prog], b"", _BASE_ENV)
                total += 1
                arity_total += 1
                if ref != got:
                    fails += 1
                    print(f"FAIL builtin arity {name}/{count}/caught={caught}: {ref!r} != {got!r}")
    print(f"{arity_total} builtin arity cases checked (direct aliases, caught and uncaught)")


    float_values = ["null", "[]", "{}", "len", "true", "false", "12", "2.5",
                    '"bad"', '" 2.5 "']
    for value in float_values:
        for caught in (False, True):
            source = "f = float\n"
            expression = "print f(" + value + ")"
            if caught:
                source += 'try:\n  ' + expression + '\nexcept as e:\n  print e\nprint "after"\n'
            else:
                source += expression + '\n'
            prog = os.path.join(d, "float.holy")
            with open(prog, "w") as f:
                f.write(source)
            ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
            got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                       [driver, prog], b"", _BASE_ENV)
            total += 1
            if ref != got:
                fails += 1
                print(f"FAIL float conversion {value}/caught={caught}: {ref!r} != {got!r}")
    print("20 float conversion cases checked (aliases, caught and uncaught)")


    # Guest strings must not collide with internal unbound-variable state.
    sentinel_cases = [
        'x = "u0004IRUNBOUNDu0004"\nprint x\n',
        'def echo(x):\n  return x\nprint echo("u0004IRUNBOUNDu0004")\n',
        'x = "u0004IRUNBOUNDu0004"\ndef change():\n  global x\n  x = "u0004IRUNBOUNDu0004"\nchange()\nprint x\n',
        'try:\n  raise "u0004IRUNBOUNDu0004"\nexcept as e:\n  print e\ntry:\n  print e\nexcept as e:\n  print e\n',
        'x = ["u0004IRUNBOUNDu0004"]\ny = x[0]\nprint y\n',
    ]
    for source in sentinel_cases:
        prog = os.path.join(d, "sentinel.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL guest sentinel parity: {ref!r} != {got!r}")
    print("5 guest-string/unbound-state cases checked")

    # Independent interpreter states must not share executed module frames.
    # The second run used to reuse the first run's module and miss its function
    # definitions in the new state's function table.
    module_dir = os.path.join(d, "modules")
    os.makedirs(module_dir)
    with open(os.path.join(module_dir, "counter.holy"), "w") as f:
        f.write('value = 1\ndef bump():\n  global value\n  value = value + 1\n  return value\n')
    # Module attribute reads must respect exception-name unbinding too.
    with open(os.path.join(module_dir, "expired.holy"), "w") as f:
        f.write('try:\n  raise "gone"\nexcept as e:\n  print e\n')
    for caught in (False, True):
        source = 'import expired\n'
        if caught:
            source += 'try:\n  print expired.e\nexcept as error:\n  print error\n'
            source += 'expired.e = "u0004IRUNBOUNDu0004"\nprint expired.e\n'
        else:
            source += 'print expired.e\n'
        prog = os.path.join(module_dir, "attributes.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL unbound module attribute: {ref!r} != {got!r}")

    unit = os.path.join(d, "states.holy")
    with open(unit, "w") as f:
        f.write('import normalize\nimport irbuild\nimport irinterp\n')
        f.write('source = "import counter\\nprint counter.bump()\\n"\n')
        f.write('m = irbuild.build_module(normalize.parse(source), "")\n')
        f.write('a = irinterp.create(m, ' + repr(module_dir).replace("'", '"') + ')\n')
        f.write('b = irinterp.create(m, ' + repr(module_dir).replace("'", '"') + ')\n')
        f.write('irinterp.run(a)\nassert len(keys(b["funcs"])) == len(m["order"])\nassert len(keys(m["funcs"])) == len(m["order"])\nirinterp.run(b)\nirinterp.run(a)\n')
    unit_exe = os.path.join(d, "states")
    r = subprocess.run(builder + [unit, unit_exe], capture_output=True, timeout=600, env=_BASE_ENV)
    total += 1
    if r.returncode:
        fails += 1
        print(f"FAIL state isolation build: {r.stderr!r}")
    else:
        r = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) + [unit_exe], b"", _BASE_ENV)
        if r != (0, b"2\n2\n3\n", b""):
            fails += 1
            print(f"FAIL module state isolation: {r!r}")
        else:
            print("ok independent module states and within-state import cache")

if fails:
    print(f"{total - fails}/{total} irinterp parity")
    sys.exit(1)
print(f"{total}/{total} irinterp parity")
