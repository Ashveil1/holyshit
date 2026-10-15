#!/usr/bin/env python3
"""Source -> optimized CFG in hs compared with the Python pipeline."""
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
from x64gen import build_x64
passed = failed = skipped = native_skipped = large_skipped = 0
env = dict(os.environ, HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
work = tempfile.TemporaryDirectory()
exe = str(Path(work.name)/'irbuild')
oldpath = os.environ.get('HSPATH')
os.environ['HSPATH'] = env['HSPATH']
try:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT/'selfhost/be/pipeline_run.holy'), exe)
finally:
    if oldpath is None:
        os.environ.pop('HSPATH', None)
    else:
        os.environ['HSPATH'] = oldpath
if rc:
    raise SystemExit('FAIL x64 build of normalized parser')
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
    if Path(f).name == 'be.holy':
        large_skipped += 1  # 13k-line emitter: dedicated slow bootstrap gate
        continue
    try:
        interp.reset_parse_state()
        prog = interp.parse_program(Path(f).read_text())
        want = ir.build_module(prog)
        ir.verify_module(want)
    except Exception:
        skipped += 1
        continue
    astfile = type('Source', (), {'name': f})()
    r = subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run',
        str(ROOT/'selfhost/be/pipeline_run.holy'), '--backend', 'interp', astfile.name],
        env=env, capture_output=True, text=True, timeout=600)
    try:
        got = json.loads(r.stdout)
        ir.verify_module(got)
        ok = got == json.loads(json.dumps(want))
        if fits62(prog):
            native = subprocess.run([exe, astfile.name], capture_output=True, text=True, timeout=600)
            ngot = json.loads(native.stdout)
            ir.verify_module(ngot)
            ok = ok and ngot == got
        else:
            native_skipped += 1
    except Exception:
        ok = False
    if ok:
        passed += 1
    else:
        failed += 1
        print('FAIL', Path(f).name, r.stdout[:150], r.stderr[:150], flush=True)
print(f'{passed}/{passed+failed} passed (interp + x64 ({native_skipped} ASTs exceed x64 Int width); {skipped} rejected by reference parser; {large_skipped} large emitter deferred to bootstrap gate)')
sys.exit(bool(failed) or not passed)
