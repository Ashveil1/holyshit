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

    # Internal callable keys in ordinary guest Dicts carry no authority.
    record_sources = []
    for value in ['{"hs_ir_builtin": "len"}', '{"hs_ir_fn": "missing", "closure": {}}']:
        for expression in ['print f', 'print str(f)', 'print float(f)', 'print f("abc")',
                           'print keys(f)', 'print f == f', 'print len(f)']:
            record_sources.append('f = ' + value + '\ntry:\n  ' + expression +
                                  '\nexcept as error:\n  print error\n')
    record_sources += [
        'def outer(x):\n  def inner(y):\n    return x + y\n  return inner\nf = outer(4)\nprint f(7)\n',
        'f = len\na = [f]\nd = {"call": a[0]}\nprint d["call"]("abc")\n',
        'def f():\n  return 1\ntry:\n  print f["closure"]\nexcept as error:\n  print error\n',
        'f = len\ntry:\n  f["hs_ir_builtin"] = "str"\nexcept as error:\n  print error\nprint f("abc")\n',
    ]
    for source in record_sources:
        prog = os.path.join(d, "records.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL callable record parity: {source!r}: {ref!r} != {got!r}")
    print("18 callable handle/guest Dict cases checked")

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

    module_sources = []
    for expression in ['print f', 'print str(f)', 'print float(f)', 'print f()',
                       'print keys(f)', 'print len(f)', 'print f["hs_ir_mod"]',
                       'print f.missing', 'f.missing = 1']:
        module_sources.append('f = {"hs_ir_mod": "fake", "frame": {}}\ntry:\n  ' +
                              expression + '\nexcept as error:\n  print error\n')
    for expression in ['print counter["frame"]', 'counter["frame"] = {}',
                       'print counter()', 'print float(counter)']:
        module_sources.append('import counter\ntry:\n  ' + expression +
                              '\nexcept as error:\n  print error\nprint counter.bump()\n')
    module_sources.append('import counter\na = counter\nprint a, str(a)\na.value = 7\nprint counter.bump()\n')
    for source in module_sources:
        prog = os.path.join(module_dir, "module_records.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL module handle parity: {source!r}: {ref!r} != {got!r}")
    print("14 module handle/guest Dict cases checked")

    display_sources = [
        'def f():\n  return 1\nprint f\nprint str(f)\n',
        'f = len\nprint f\nprint str(f)\n',
        'def outer():\n  def nested():\n    return 2\n  return nested\nprint outer()\n',
        'import counter\nprint counter, str(counter)\n',
        'def f():\n  return 1\nprint [f, len, {"call": f}]\n',
        'import counter\nprint {"module": [counter, len]}\n',
        'def f():\n  return 1\nprint str([f, len])\nprint str({"f": f})\n',
        'print {"hs_ir_fn": "plain", "hs_ir_mod": "plain"}\n',
    ]
    for source in display_sources:
        prog = os.path.join(module_dir, "display_handles.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL handle display parity: {source!r}: {ref!r} != {got!r}")
    print("8 callable/module display cases checked")

    handle_error_sources = []
    for value in ['len', 'counter', 'local_fn']:
        for operation in ['len', 'int']:
            for caught in (False, True):
                source = 'import counter\ndef local_fn():\n  return 1\nf = ' + value + '\n'
                expr = 'print ' + operation + '(f)'
                if caught:
                    source += 'try:\n  ' + expr + '\nexcept as error:\n  print error\n'
                else:
                    source += expr + '\n'
                handle_error_sources.append(source)
    for source in handle_error_sources:
        prog = os.path.join(module_dir, "handle_errors.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL handle error parity: {source!r}: {ref!r} != {got!r}")
    print("12 handle len/int error cases checked")

    for value in ['len', 'counter', 'local_fn']:
        for span in [':', '0:1', '1:', ':1']:
            source = 'import counter\ndef local_fn():\n  return 1\nf = ' + value + '\n'
            source += 'try:\n  print f[' + span + ']\nexcept as error:\n  print error\n'
            prog = os.path.join(module_dir, "handle_slices.holy")
            with open(prog, "w") as f:
                f.write(source)
            ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
            got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                       [driver, prog], b"", _BASE_ENV)
            total += 1
            if ref != got:
                fails += 1
                print(f"FAIL handle slice parity: {source!r}: {ref!r} != {got!r}")
    print("12 handle slice error cases checked")

    op_cases = 0
    for value in ['len', 'counter', 'local_fn']:
        expressions = ['f ' + op + ' 1' for op in ['+', '-', '*', '/', '%', '<<', '>>', '&', '|', '^', '<', '>', '<=', '>=']]
        expressions += ['1 ' + op + ' f' for op in ['+', '-', '*', '/', '%', '<<', '>>', '&', '|', '^', '<', '>', '<=', '>=']]
        expressions += ['-f', '~f', 'not f', 'f == f', 'f != f', 'f == 1']
        source = 'import counter\ndef local_fn():\n  return 1\nf = ' + value + '\n'
        for expr in expressions:
            source += 'try:\n  print ' + expr + '\nexcept as error:\n  print error\n'
        prog = os.path.join(module_dir, "handle_ops.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        op_cases += len(expressions)
        if ref != got:
            fails += 1
            print(f"FAIL handle operation parity for {value}: {ref!r} != {got!r}")
    print(f"{op_cases} handle operator expressions checked in 3 programs")

    contains_sources = []
    for value in ['len', 'counter', 'local_fn']:
        for expr in ['contains(f, 1)', 'contains("abc", f)']:
            for caught in (False, True):
                source = 'import counter\ndef local_fn():\n  return 1\nf = ' + value + '\n'
                if caught:
                    source += 'try:\n  print ' + expr + '\nexcept as error:\n  print error\n'
                else:
                    source += 'print ' + expr + '\n'
                contains_sources.append(source)
    contains_sources.append('import counter\ndef local_fn():\n  return 1\nf = local_fn\nprint contains([f, len, counter], f), contains([f, len, counter], len), contains([f, len, counter], counter)\nprint contains([f], len), contains("abc", "b"), contains({"key": f}, "key")\n')
    for source in contains_sources:
        prog = os.path.join(module_dir, "handle_contains.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL handle contains parity: {source!r}: {ref!r} != {got!r}")
    print("13 handle contains error/control programs checked")

    json_sources = []
    for value in ['len', 'counter', 'local_fn']:
        for shape in ['f', '[f]', '{"nested": [f]}']:
            for caught in (False, True):
                source = 'import counter\ndef local_fn():\n  return 1\nf = ' + value + '\n'
                expr = 'print json_str(' + shape + ')'
                if caught:
                    source += 'try:\n  ' + expr + '\nexcept as error:\n  print error\n'
                else:
                    source += expr + '\n'
                json_sources.append(source)
    json_sources += [
        'try:\n  print json_str({"first": len, 2: 0})\nexcept as error:\n  print error\n',
        'a = []\nappend(a, a)\ntry:\n  print json_str(a)\nexcept as error:\n  print error\n',
        'print json_str({"x": [null, true, false, 3, "str"], "tag": {"hs_ir_mod": "plain"}})\n',
    ]
    for depth in [200, 201]:
        json_sources.append('v = len\ni = 0\nwhile i < ' + str(depth) + ':\n  v = [v]\n  i = i + 1\ntry:\n  print json_str(v)\nexcept as error:\n  print error\n')
    json_sources.append('try:\n  json_save(1, len)\nexcept as error:\n  print error\n')
    json_path = os.path.join(module_dir, "preserved.json")
    for value in ['len', 'counter', 'local_fn']:
        source = 'import counter\ndef local_fn():\n  return 1\n'
        source += 'path = ' + repr(json_path).replace("'", '"') + '\nwrite_text(path, "keep")\n'
        source += 'try:\n  json_save(path, {"nested": [' + value + ']})\nexcept as error:\n  print error\nprint read_text(path)\n'
        json_sources.append(source)
    for source in json_sources:
        prog = os.path.join(module_dir, "handle_json.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL handle JSON parity: {source!r}: {ref!r} != {got!r}")
    print("27 handle JSON error/order/depth/save/control programs checked")

    byte_cases = ['[]', '[0, 1, 127, 128, 255]', '[256]', '[-1]', '[true]', '["x"]', '[len]', '1', 'null']
    for payload in byte_cases:
        target = os.path.join(module_dir, "bytes.bin")
        source = 'f = write_bytes\npath = ' + repr(target).replace("'", '"') + '\nwrite_text(path, "keep")\n'
        source += 'try:\n  print f(path, ' + payload + ')\nexcept as error:\n  print error\n'
        prog = os.path.join(module_dir, "write_bytes.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        with open(target, "rb") as f:
            ref_bytes = f.read()
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        with open(target, "rb") as f:
            got_bytes = f.read()
        total += 1
        if ref != got or ref_bytes != got_bytes:
            fails += 1
            print(f"FAIL write_bytes {payload}: {ref!r}/{ref_bytes!r} != {got!r}/{got_bytes!r}")
    for expr in ['f()', 'f("path")', 'f("path", [], 1)', 'f(1, [])']:
        for caught in (False, True):
            source = 'f = write_bytes\n'
            if caught:
                source += 'try:\n  print ' + expr + '\nexcept as error:\n  print error\n'
            else:
                source += 'print ' + expr + '\n'
            prog = os.path.join(module_dir, "write_bytes_errors.holy")
            with open(prog, "w") as f:
                f.write(source)
            ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
            got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                       [driver, prog], b"", _BASE_ENV)
            total += 1
            if ref != got:
                fails += 1
                print(f"FAIL write_bytes error {source!r}: {ref!r} != {got!r}")
    print("17 write_bytes value/error/file-content programs checked")

    modulo_sources = []
    for value in ['true', 'null', '"s"', '[]', '{}', 'len', 'counter', 'local_fn']:
        for expr in [value + ' % 3', '3 % ' + value]:
            for caught in (False, True):
                source = 'import counter\ndef local_fn():\n  return 1\n'
                if caught:
                    source += 'try:\n  print ' + expr + '\nexcept as error:\n  print error\n'
                else:
                    source += 'print ' + expr + '\n'
                modulo_sources.append(source)
    modulo_sources.append('print 7 % 3, -7 % 3, 7 % -3, -7 % -3\nprint 7.5 % 3\ntry:\n  print 1 % 0\nexcept as error:\n  print error\n')
    for source in modulo_sources:
        prog = os.path.join(module_dir, "modulo_types.holy")
        with open(prog, "w") as f:
            f.write(source)
        ref = _run([sys.executable, os.path.join(ROOT, "interp.py"), prog], b"", _BASE_ENV)
        got = _run(([OPTIONS.arm64_qemu] if OPTIONS.arm64_qemu else []) +
                   [driver, prog], b"", _BASE_ENV)
        total += 1
        if ref != got:
            fails += 1
            print(f"FAIL modulo type parity: {source!r}: {ref!r} != {got!r}")
    print("33 modulo type/error/control programs checked")

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
