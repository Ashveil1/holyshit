#!/usr/bin/env python3
"""SysV mixed register banks: 6 integer + 8 float args, order-sensitive."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL',label,flush=True)
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as d:
    d=Path(d);c=d/'mixed.c';so=d/'mixed.so'
    for kinds in [['I64','F64'] * 12, ['I64'] * 16, ['F64'] * 16, ['I64','F64'] * 16]:
        kinds=['I64','F64'] * 12
        types={'I64':'long long','F64':'double'}
        params=', '.join(types[k]+f' p{i}' for i,k in enumerate(kinds))
        expr=' + '.join(f'p{i} * {i+1}' for i in range(len(kinds)))
        c.write_text('double mixed('+params+') {return '+expr+';}\n')
        subprocess.run(['gcc','-shared','-fPIC',str(c),'-o',str(so)],check=True,capture_output=True)
        decl=', '.join(k+f' p{i}' for i,k in enumerate(kinds))
        args=', '.join(str(i+1)+('.5' if k=='F64' else '') for i,k in enumerate(kinds))
        source=d/'mixed.hs';source.write_text('extern from "'+str(so)+'":\n  F64 mixed('+decl+')\nprint mixed('+args+')\n')
        expected=None
        for backend in ['interp','native','x64','native-hs']:
            if backend=='native-hs':
                exe=str(d/'program')
                r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),exe],env=env,capture_output=True,text=True,timeout=60)
                if r.returncode==0:r=subprocess.run([exe],env=env,capture_output=True,text=True,timeout=20)
            else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=60)
            got=(r.returncode,r.stdout)
            if expected is None:expected=got
            check(got==expected and got[0]==0,backend+' mixed banks '+repr((got,r.stderr[-150:])))
print(f'{passed}/{passed+failed} stack FFI argument gates')
sys.exit(bool(failed))
