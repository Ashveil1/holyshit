#!/usr/bin/env python3
"""Executable-memory groundwork: RW -> RX, native generated code, release."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def timed_out(_signal, _frame):
    raise TimeoutError("jit memory fixture did not reach its checkpoint")
signal.signal(signal.SIGALRM,timed_out)
def check(ok, label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok: print('FAIL',label,flush=True)
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT),PYTHONUNBUFFERED='1')
with tempfile.TemporaryDirectory() as d:
    for backend in ['interp','x64','native-hs','native-gcc']:
        print('checking',backend,flush=True)
        if backend=='interp':
            command=[sys.executable,str(ROOT/'interp.py'),str(ROOT/'tests/jit/memory.holy')]
        else:
            exe=str(Path(d)/'memory')
            build=([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'tests/jit/memory.holy'),exe] if backend=='native-hs' else [sys.executable,str(ROOT/'hs.py'),'build' if backend=='native-gcc' else 'xbuild',str(ROOT/'tests/jit/memory.holy'),'-o',exe])
            result=subprocess.run(build,env=env,capture_output=True,text=True,timeout=120)
            check(result.returncode==0,'build memory fixture '+result.stderr[-200:])
            if result.returncode: continue
            command=(["stdbuf","-oL",exe] if backend=="native-gcc" else [exe])
        p=subprocess.Popen(command,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            signal.alarm(30)
            pointer=int(p.stdout.readline());size=int(p.stdout.readline())
            maps=Path(f'/proc/{p.pid}/maps').read_text().splitlines()
            region=next(line for line in maps if int(line.split('-')[0],16)<=pointer<int(line.split()[0].split('-')[1],16))
            check(region.split()[1]=='r-xp' and size==4096,backend+' RX, never RWX published mapping')
            p.stdin.write('\n');p.stdin.flush()
            sorted_line=p.stdout.readline();released_line=p.stdout.readline()
            maps=Path(f'/proc/{p.pid}/maps').read_text().splitlines()
            check(not any(int(line.split('-')[0],16)<=pointer<int(line.split()[0].split('-')[1],16) for line in maps),backend+' mapping unmapped after release')
            out,err=p.communicate('\n',timeout=20)
            out=sorted_line+released_line+out
            check(p.returncode==0 and out=='10 20 30\n0 false\ndouble release rejected\n',backend+' generated comparator and release '+repr((out,err)))
        finally:
            signal.alarm(0)
            if p.poll() is None: p.kill();p.communicate()
    # Validation has identical observable behavior and does not allocate code.
    source=Path(d)/'invalid.holy'
    source.write_text('import jitmem\nfor value in [[], [256], [-1], [true], [false], [1.0], ["a"], "abc", null]:\n  try:\n    jitmem.publish(value)\n    print "BAD"\n  except:\n    print "rejected"\n')
    for backend in ['interp','x64']:
        r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=60)
        check(r.returncode==0 and r.stdout=='rejected\n'*9,backend+' rejects invalid byte buffers '+repr((r.stdout,r.stderr)))
print(f'{passed}/{passed+failed} executable-memory gates (not a full JIT)')
sys.exit(bool(failed))
