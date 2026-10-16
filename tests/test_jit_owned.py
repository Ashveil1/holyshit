#!/usr/bin/env python3
"""Observe owned target arenas/bitmaps/table absent after normal return."""
from pathlib import Path
import json,os,signal,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
def alarm(_s,_f):raise TimeoutError('heap checkpoint stalled')
signal.signal(signal.SIGALRM,alarm)
passed=0
with tempfile.TemporaryDirectory() as tmp:
    driver=Path(tmp)/'driver'
    command=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/jit_return_probe.holy'),'-o',str(driver)] if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_return_probe.holy'),str(driver)])
    r=subprocess.run(command,env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-250:];passed+=1
    for name in ['fib.holy','x64/gc_stress.holy']:
        p=subprocess.Popen([str(driver),str(ROOT/'tests'/name),'--release-heap-checkpoints'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            signal.alarm(60);lines=[]
            while True:
                line=p.stdout.readline();assert line,('checkpoint EOF',p.poll(),p.stderr.read());lines.append(line)
                if line.startswith('JIT OWNED RANGES '):break
            ranges=json.loads(line[len('JIT OWNED RANGES '):]);assert len(ranges)>=3 and len(ranges)%2==1
            def mapped(address):
                return any(int(line.split('-')[0],16)<=address<int(line.split()[0].split('-')[1],16) for line in Path(f'/proc/{p.pid}/maps').read_text().splitlines())
            assert all(mapped(base) and mapped(base+size-1) for base,size in ranges);passed+=1
            p.stdin.write('\n');p.stdin.flush();assert p.stdout.readline()=='JIT HEAP UNMAPPED\n'
            assert not any(mapped(base) or mapped(base+size-1) for base,size in ranges);passed+=1
            out,err=p.communicate('\n',timeout=20);assert not p.returncode and not err and out.endswith('JIT IMAGE RELEASED false\n'),(out,err);passed+=1
        finally:
            signal.alarm(0)
            if p.poll() is None:p.kill();p.communicate()
    r=subprocess.run([str(driver),str(ROOT/'tests/t_json.holy'),'--release-heap'],env=env,capture_output=True,timeout=60)
    ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(ROOT/'tests/t_json.holy')],env=env,capture_output=True,timeout=20)
    assert not r.returncode and r.stdout.startswith(ref.stdout) and b'JIT HEAP RELEASED'in r.stdout;passed+=1
print(f'{passed}/{passed} target heap ownership/unmap gates (normal return only; no shared runtime)')
