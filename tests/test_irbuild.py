#!/usr/bin/env python3
"""AST->CFG hs builder compared structurally to the unoptimized Python builder."""
import glob
import json
import os
import subprocess
import tempfile
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import interp
import ir
import contextlib
import io
import traceback
import time
import resource
from x64gen import build_x64


def first_diff(a, b, path='$'):
    """Short description of the first structural difference, or None."""
    if type(a) is not type(b):
        return f'{path}: type {type(a).__name__} vs {type(b).__name__}'
    if isinstance(a, dict):
        ka, kb = set(a), set(b)
        if ka != kb:
            return (f'{path}: keys only-left {sorted(ka - kb)[:5]} '
                    f'only-right {sorted(kb - ka)[:5]}')
        for k in a:
            d = first_diff(a[k], b[k], f'{path}.{k}')
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f'{path}: length {len(a)} vs {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f'{path}[{i}]')
            if d:
                return d
        return None
    if a != b:
        return f'{path}: {repr(a)[:200]} vs {repr(b)[:200]}'
    return None
def exception_evidence(exc, stage, native, command, started, elapsed):
    """Keep the full failure, including partial output on subprocess timeouts."""
    def text(value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="backslashreplace")
        return value
    result = {
        "stage": stage,
        "exception_class": type(exc).__name__,
        "traceback": traceback.format_exc(),
        "command": command,
        "elapsed_seconds": (elapsed if elapsed is not None else
                            None if started is None else time.monotonic() - started),
        "timeout_seconds": 60 if command is not None else None,
        "returncode": None if native is None else native.returncode,
        "stdout": text(getattr(exc, "stdout", None)),
        "stderr": text(getattr(exc, "stderr", None)),
    }
    if native is not None:
        result["stdout"] = native.stdout
        result["stderr"] = native.stderr
    return result


passed = failed = skipped = native_skipped = 0
env = dict(os.environ, HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
work = tempfile.TemporaryDirectory()
exe = str(Path(work.name)/'irbuild')
oldpath = os.environ.get('HSPATH')
os.environ['HSPATH'] = env['HSPATH']
try:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT/'selfhost/be/irbuild_run.holy'), exe)
finally:
    if oldpath is None:
        os.environ.pop('HSPATH', None)
    else:
        os.environ['HSPATH'] = oldpath
if rc:
    raise SystemExit('FAIL x64 build of irbuild driver')
env = dict(os.environ, HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
def fits62(v):
    if type(v) is int:
        return -(1 << 61) <= v < (1 << 61)
    if isinstance(v, (list, tuple)):
        return all(fits62(x) for x in v)
    if isinstance(v, dict):
        return all(fits62(x) for x in v.values())
    return True

files = sum((glob.glob(str(ROOT/p)) for p in ['tests/*.holy', 'examples/*.holy', 'selfhost/*.holy', 'selfhost/be/*.holy']), [])
for f in sorted(files):
    if sys.argv[1:] and Path(f).name not in sys.argv[1:]:
        continue
    try:
        interp.reset_parse_state()
        prog = interp.parse_program(Path(f).read_text())
        want = ir.Builder().build(prog)
        ir.verify_module(want)
    except Exception:
        skipped += 1
        continue
    astfile = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(prog, astfile)
    astfile.close()
    r = subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run',
        str(ROOT/'selfhost/be/irbuild_run.holy'), '--backend', 'interp', astfile.name],
        env=env, capture_output=True, text=True, timeout=60)
    stage = 'interp-parse'
    fail_stage = None
    diag = {}
    snippet = ''
    native = None
    native_command = None
    native_started = None
    native_elapsed = None
    failure_evidence = None
    native_usage_before = None
    native_metrics = None
    try:
        got = json.loads(r.stdout)
        diag['hs-interp'] = got
        stage = 'interp-verify'
        ir.verify_module(got)
        stage = 'interp-compare'
        want_rt = json.loads(json.dumps(want))
        diag['python'] = want_rt
        ok = got == want_rt
        if not ok:
            fail_stage = 'interp-compare-mismatch'
        if fits62(prog):
            stage = 'native-run'
            native_command = [exe, astfile.name]
            native_started = time.monotonic()
            if Path(f).name == "be.holy":
                native_usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
            try:
                native = subprocess.run(native_command, capture_output=True, text=True, timeout=60)
            finally:
                native_elapsed = time.monotonic() - native_started
                if native_usage_before is not None:
                    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                    native_metrics = {
                        "input": "be.holy", "wall_seconds": native_elapsed,
                        "child_cpu_seconds": (usage.ru_utime + usage.ru_stime -
                                              native_usage_before.ru_utime - native_usage_before.ru_stime),
                        # Cumulative child high-water mark, not this invocation's
                        # RSS and not proof of scheduling contention.
                        "cumulative_child_maxrss_KiB_linux": usage.ru_maxrss,
                        "timeout_seconds": 60,
                        "returncode": None if native is None else native.returncode,
                    }
                    print("NATIVE_METRICS " + json.dumps(native_metrics), flush=True)
            stage = 'native-parse'
            snippet = native.stdout[:150] + ' stderr:' + native.stderr[:150]
            ngot = json.loads(native.stdout)
            diag['hs-native'] = ngot
            stage = 'native-verify'
            ir.verify_module(ngot)
            stage = 'native-compare'
            ok = ok and ngot == got
            if not ok and fail_stage is None:
                fail_stage = 'native-compare-mismatch'
        else:
            native_skipped += 1
    except Exception as exc:
        ok = False
        failure_evidence = exception_evidence(
            exc, stage, native, native_command, native_started, native_elapsed)
        if native_metrics is not None:
            failure_evidence["native_metrics"] = native_metrics
        fail_stage = stage + ' exception_class=' + type(exc).__name__ + ' exception:' + traceback.format_exc(limit=3).replace('\n', ' | ')[:400]
        if not snippet:
            snippet = r.stdout[:150] + ' stderr:' + r.stderr[:150]
    os.unlink(astfile.name)
    if ok:
        passed += 1
    else:
        failed += 1
        # Diagnostics only: preserve every assertion above; capture artifacts
        # and the first structural difference so a rare failure is analyzable.
        diagdir = os.environ.get('IRBUILD_DIAG_DIR') or tempfile.mkdtemp(prefix='irbuild-diag-')
        os.makedirs(diagdir, exist_ok=True)
        base = str(Path(diagdir)/Path(f).name)
        try:
            Path(base + '.ast.json').write_text(json.dumps(prog))
            if failure_evidence is not None:
                Path(base + '.exception.json').write_text(
                    json.dumps(failure_evidence, ensure_ascii=True, indent=2))
            for tag, mod in diag.items():
                Path(f'{base}.{tag}.json').write_text(json.dumps(mod, sort_keys=True))
        except Exception:
            pass
        detail = ''
        if 'hs-interp' in diag and 'python' in diag:
            d = first_diff(diag['hs-interp'], diag['python'])
            if d:
                detail += ' interp-vs-python{' + d + '}'
        if 'hs-native' in diag and 'hs-interp' in diag:
            d = first_diff(diag['hs-native'], diag['hs-interp'])
            if d:
                detail += ' native-vs-interp{' + d + '}'
        print('FAIL', Path(f).name, 'stage=' + str(fail_stage), detail[:600],
              snippet, 'diagdir=' + diagdir, flush=True)
print(f'{passed}/{passed+failed} passed (interp + x64 ({native_skipped} ASTs exceed x64 Int width); {skipped} rejected by Python builder)')
sys.exit(bool(failed) or not passed)
