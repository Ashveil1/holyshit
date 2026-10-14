#!/usr/bin/env python3
"""Relocated code+data sections have separate RX/RW permissions and lifetime."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL',label,flush=True)
def timeout(_s,_f):raise TimeoutError('relocation fixture stalled')
signal.signal(signal.SIGALRM,timeout)
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT),PYTHONUNBUFFERED='1')
with tempfile.TemporaryDirectory() as d:
    for backend in ['interp','x64','native-hs','native-gcc']:
        print('checking',backend,flush=True)
        source=str(ROOT/'tests/jit/relocation.hs')
        if backend=='interp':command=[sys.executable,str(ROOT/'interp.py'),source]
        else:
            exe=str(Path(d)/'relocation')
            build=([str(ROOT/'bootstrap/hs-hosted-x86_64'),source,exe] if backend=='native-hs' else [sys.executable,str(ROOT/'hs.py'),'build' if backend=='native-gcc' else 'xbuild',source,'-o',exe])
            r=subprocess.run(build,env=env,capture_output=True,text=True,timeout=120)
            check(r.returncode==0,'build '+backend+r.stderr[-150:])
            if r.returncode:continue
            command=['stdbuf','-oL',exe] if backend=='native-gcc' else [exe]
        p=subprocess.Popen(command,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            signal.alarm(30)
            addresses=[int(p.stdout.readline()) for _ in range(4)]
            maps=Path(f'/proc/{p.pid}/maps').read_text().splitlines()
            def permission(addr):
                return next(line.split()[1] for line in maps if int(line.split('-')[0],16)<=addr<int(line.split()[0].split('-')[1],16))
            check(len(set(addresses))==4 and [permission(a) for a in addresses]==['r-xp','rw-p','r-xp','rw-p'],backend+' separate RX/RW independently relocated images')
            p.stdin.write('\n');p.stdin.flush()
            out=''.join(p.stdout.readline() for _ in range(4))
            maps=Path(f'/proc/{p.pid}/maps').read_text().splitlines()
            check(not any(int(line.split('-')[0],16)<=a<int(line.split()[0].split('-')[1],16) for line in maps for a in addresses),backend+' both images unmapped')
            rest,err=p.communicate('\n',timeout=20)
            check(p.returncode==0 and out=='10 20 30\n30 20 10\n30 20 10\nreleased\n' and not rest,backend+' data relocation changes execution, independent release '+repr((out,rest,err)))
        finally:
            signal.alarm(0)
            if p.poll() is None:p.kill();p.communicate()
# A throwing/invalid callback must not leak its reserved mapping.
for backend in ['interp','x64']:
    p=subprocess.Popen([sys.executable,str(ROOT/'interp.py'),str(ROOT/'tests/jit/invalid_relocation.hs')] if backend=='interp' else [sys.executable,str(ROOT/'hs.py'),'run',str(ROOT/'tests/jit/invalid_relocation.hs'),'--backend','x64'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        signal.alarm(30)
        first=p.stdout.readline();addr=int(p.stdout.readline())
        # hs.py supervises the x64 executable, so inspect its child there.
        pid=p.pid
        if backend=='x64':
            children=Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
            pid=int(children[0])
        maps=Path(f'/proc/{pid}/maps').read_text().splitlines()
        check(not any(int(line.split('-')[0],16)<=addr<int(line.split()[0].split('-')[1],16) for line in maps),backend+' invalid relocation releases reservation')
        out,err=p.communicate('\n',timeout=20)
        check(p.returncode==0 and first=='size mismatch rejected\n' and out=='out of range rejected\n',backend+' rejects changed size and out-of-range rel32 '+repr((out,err)))
    finally:
        signal.alarm(0)
        if p.poll() is None:p.kill();p.communicate()
print(f'{passed}/{passed+failed} relocated-memory gates (not a full JIT)')
sys.exit(bool(failed))
