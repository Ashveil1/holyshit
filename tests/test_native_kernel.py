#!/usr/bin/env python3
"""Native hs compiler must match reference complete kernel ELF images."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_x64, build_xkernel
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel')+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
os.environ['HSPATH']=env['HSPATH']
passed=failed=0
with tempfile.TemporaryDirectory() as d:
    d=Path(d)
    with contextlib.redirect_stdout(io.StringIO()):
        rc=build_x64(str(ROOT/'selfhost/be/kernel_hex.hs'),str(d/'compiler'))
    if rc: raise SystemExit('FAIL native kernel compiler build')
    files=sys.argv[1:] or ['kernel/kx2.hs','kernel/kheaptest.hs','kernel/kring3.hs','kernel/ksyscall.hs','kernel/kpreempt.hs','kernel/kjsontest.hs','kernel/kushtest.hs']
    for name in files:
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build_xkernel(str(ROOT/name),str(d/'reference'))
        if rc: raise SystemExit('FAIL reference kernel '+name)
        r=subprocess.run([str(d/'compiler'),str(ROOT/name)],env=env,capture_output=True,text=True,timeout=240)
        try: got=bytes.fromhex(''.join(r.stdout.split()))
        except ValueError:got=b''
        want=(d/'reference').read_bytes()
        ok=r.returncode==0 and got==want
        passed+=int(ok);failed+=int(not ok)
        if not ok:
            diff=next(((i,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b),None)
            print('FAIL native kernel',name,len(got),len(want),diff,r.stderr[-250:],flush=True)
print(f'{passed}/{passed+failed} native kernel complete-image gates')
sys.exit(bool(failed) or not passed)
