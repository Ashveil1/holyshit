#!/usr/bin/env python3
"""Python-free native kernel command preserves images and failure output."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_xkernel
passed=failed=0
with tempfile.TemporaryDirectory(prefix='hs kernel space ') as d:
    d=Path(d);bindir=d/'bin';bindir.mkdir()
    for name in ['dirname','sha256sum','mktemp','rm','mv']:
        (bindir/name).symlink_to(shutil.which(name))
    env=dict(os.environ,PATH=str(bindir))
    for name in (n for n in (sys.argv[1:] or ['kx2','kiotest']) if n!='invalid'):
        out=d/'kernel image.elf';want=d/'reference'
        os.environ['HSPATH']=str(ROOT)+':'+str(ROOT/'kernel')
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build_xkernel(str(ROOT/'kernel'/f'{name}.holy'),str(want))
        r=subprocess.run(['/bin/sh',str(ROOT/'scripts/build-kernel-native.sh'),str(ROOT/'kernel'/f'{name}.holy'),str(out)],cwd=d,env=env,capture_output=True,text=True,timeout=180)
        ok=rc==0 and r.returncode==0 and out.read_bytes()==want.read_bytes()
        passed+=int(ok);failed+=int(not ok)
        if not ok:print('FAIL native kernel command',name,r.returncode,r.stderr[-400:])
    source=d/'bad source.holy';source.write_text('if\n');out=d/'keep.elf';out.write_bytes(b'preserve')
    if sys.argv[1:] and 'invalid' not in sys.argv[1:]:
        print(f'{passed}/{passed+failed} native kernel command gates (PATH without Python/gcc)');sys.exit(bool(failed))
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/build-kernel-native.sh'),str(source),str(out)],env=env,capture_output=True,text=True,timeout=180)
    ok=r.returncode!=0 and out.read_bytes()==b'preserve'
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL native kernel command preserves output',r.returncode,r.stderr[-400:])
print(f'{passed}/{passed+failed} native kernel command gates (PATH without Python/gcc)')
sys.exit(bool(failed))
