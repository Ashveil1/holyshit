#!/usr/bin/env python3
"""hs CFG optimizer compared structurally to iropt.py."""
import glob
import random
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
import iropt
import contextlib
import io
from x64gen import build_x64
passed = failed = skipped = native_skipped = 0
env = dict(os.environ, HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
work = tempfile.TemporaryDirectory()
exe = str(Path(work.name)/'iropt')
oldpath = os.environ.get('HSPATH')
os.environ['HSPATH'] = env['HSPATH']
try:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT/'selfhost/be/iropt_run.holy'), exe)
finally:
    if oldpath is None:
        os.environ.pop('HSPATH', None)
    else:
        os.environ['HSPATH'] = oldpath
if rc:
    raise SystemExit('FAIL x64 build of optimizer driver')
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
        unoptimized = ir.Builder().build(prog)
        ir.verify_module(unoptimized)
        want = json.loads(json.dumps(unoptimized))
        iropt.optimize_module(want)
        ir.verify_module(want)
    except Exception:
        skipped += 1
        continue
    astfile = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(unoptimized, astfile)
    astfile.close()
    r = subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run',
        str(ROOT/'selfhost/be/iropt_run.holy'), '--backend', 'interp', astfile.name],
        env=env, capture_output=True, text=True, timeout=300)
    try:
        got = json.loads(r.stdout)
        ir.verify_module(got)
        ok = got == json.loads(json.dumps(want))
        if fits62(unoptimized):
            native = subprocess.run([exe, astfile.name], capture_output=True, text=True, timeout=300)
            ngot = json.loads(native.stdout)
            ir.verify_module(ngot)
            ok = ok and ngot == got
        else:
            native_skipped += 1
    except Exception:
        ok = False
    os.unlink(astfile.name)
    if ok:
        passed += 1
    else:
        failed += 1
        print('FAIL', Path(f).name, r.stdout[:150], r.stderr[:150], flush=True)
# Boundary products must not wrap back into the foldable range.
rng = random.Random(717)
vals = [-(1 << 61), -(1 << 60), -1, 0, 1, (1 << 60)-1, (1 << 61)-1]
vals += [rng.randrange(-(1 << 61), 1 << 61) for _ in range(20)]
cases = [[op, a, b] for op in ['+', '-', '*', '<', '=='] for a in vals for b in vals]
want = [iropt._fold(*c) for c in cases]
path = str(Path(work.name)/'folds.json')
Path(path).write_text(json.dumps(cases))
for backend in ['interp', 'x64']:
    r = subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run',
        str(ROOT/'selfhost/be/iropt_fold_run.holy'), '--backend', backend, path],
        capture_output=True, text=True, env=env, timeout=300)
    try:
        ok = json.loads(r.stdout) == want
    except Exception:
        ok = False
    passed += int(ok)
    failed += int(not ok)
    if not ok:
        print('FAIL bounded folding', backend, r.stderr[:150])
print(f'{passed}/{passed+failed} passed (interp + x64 ({native_skipped} ASTs exceed x64 Int width); {skipped} rejected by Python builder)')
sys.exit(bool(failed) or not passed)
