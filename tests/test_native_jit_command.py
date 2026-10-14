#!/usr/bin/env python3
"""One command builds the hs JIT driver and runs source without Python/gcc."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='hs jit source space ') as d:
    d=Path(d);bindir=d/'bin';bindir.mkdir()
    for name in ['dirname','sha256sum','mktemp','rm']:
        (bindir/name).symlink_to(shutil.which(name))
    source=d/'source file.hs'
    source.write_text('print argv()\nprint env("HS_JIT_COMMAND")\nprint 1 / 0\n')
    env=dict(os.environ,PATH=str(bindir),HS_JIT_COMMAND='works',TMPDIR=str(d))
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/run-jit-native.sh'),str(source),'hello world','$5'],env=env,capture_output=True,text=True,timeout=240)
    ok=r.returncode!=0 and r.stdout=='[hello world, $5]\nworks\n' and 'division by zero' in r.stderr and not list(d.glob('holyshit-jit.*'))
    if not ok:print('FAIL native JIT command',r.returncode,repr(r.stdout),r.stderr[-400:])
print('1/1 native JIT command gate' if ok else '0/1 native JIT command gate')
sys.exit(not ok)
