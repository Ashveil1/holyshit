#!/usr/bin/env python3
"""Negative U64 FFI arguments are rejected before a C side effect."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory() as d:
    d=Path(d);c=d/'counter.c';so=d/'counter.so';exe=str(d/'program')
    c.write_text('static long long count; void take(unsigned long long n){count++;} long long seen(void){return count;}')
    subprocess.run(['gcc','-shared','-fPIC',str(c),'-o',str(so)],check=True,capture_output=True)
    source=d/'bad.hs';source.write_text('extern from "'+str(so)+'":\n  U0 take(U64 n)\n  I64 seen()\nfor v in [-1, true, "x"]:\n  try:\n    take(v)\n  except:\n    print "rejected"\nprint seen()\ntake(0)\nprint seen()\n')
    env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
    passed=0
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),exe],env=env,capture_output=True,text=True,timeout=60)
            if r.returncode==0:r=subprocess.run([exe],env=env,capture_output=True,text=True,timeout=20)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=60)
        ok=r.returncode==0 and r.stdout=='rejected\n'*3+'0\n1\n';passed+=int(ok)
        if not ok:print('FAIL',backend,r.returncode,repr(r.stdout),r.stderr[-150:])
print(f'{passed}/4 U64 conversion-before-call gates')
sys.exit(passed!=4)
