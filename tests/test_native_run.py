#!/usr/bin/env python3
"""One-command source runner uses only pinned native compiler at runtime."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
with tempfile.TemporaryDirectory(prefix='hs source space ') as d:
    d=Path(d)
    # Runtime PATH has shell/checksum utilities only. Neither Python nor gcc.
    bindir=d/'bin';bindir.mkdir()
    import shutil
    for name in ['dirname','sha256sum','mktemp','rm']:
        (bindir/name).symlink_to(shutil.which(name))
    source=d/'main file.hs'
    source.write_text('print "native runner"\nprint argv()\n')
    env=dict(os.environ,PATH=str(bindir))
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/run-native.sh'),str(source),'hello world','$5'],env=env,capture_output=True,text=True,timeout=120)
    ok=r.returncode==0 and r.stdout=='native runner\n[hello world, $5]\n'
    passed+=int(ok);failed+=int(not ok)
    if not ok: print('FAIL native runner',r.returncode,repr(r.stdout),r.stderr)
    source.write_text('print 1 / 0\n')
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/run-native.sh'),str(source)],env=env,capture_output=True,text=True,timeout=120)
    ok=r.returncode!=0 and 'division by zero' in r.stderr
    passed+=int(ok);failed+=int(not ok)
    if not ok: print('FAIL native runner exit',r.returncode,r.stdout,r.stderr)
print(f'{passed}/{passed+failed} native source runner gates (PATH without Python/gcc)')
sys.exit(bool(failed))
