#!/usr/bin/env python3
"""Isolated native errors resume host; copied metadata survives heap destruction."""
from pathlib import Path
import json,os,signal,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
passed=0
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);driver=d/'driver'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/jit_status_probe.holy'),'-o',str(driver)] if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_status_probe.holy'),str(driver)])
    r=subprocess.run(build,env=env,capture_output=True,timeout=240)
    assert not r.returncode,r.stderr[-300:];passed+=1
    cases=[
        'print "normal"\n',
        'print "before"\nprint 1 / 0\n',
        'def f():\n  try:\n    raise "dynamic " + str(73)\n  finally:\n    print "finally"\nf()\n',
        'try:\n  raise "first"\nexcept as e:\n  print e\n  raise\nfinally:\n  print "outer finally"\n',
        'try:\n  raise "first"\nexcept as e:\n  raise "replacement"\nfinally:\n  print "cleanup"\n',
        'try:\n  print 1 / 0\nexcept as e:\n  print e\nprint "caught locally"\n',
        'def f(n):\n  if n == 0:\n    raise "recursive"\n  return f(n - 1)\nf(30)\n',
        'raise "nul\\0byte"\n',
        'raise ""\n',
    ]
    for n,body in enumerate(cases):
        source=d/'source.holy';source.write_text(body)
        ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30)
        got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=60)
        assert not got.returncode and not got.stderr,(n,got.returncode,got.stdout,got.stderr)
        before,marker,tail=got.stdout.rpartition(b'JIT OUTCOME ')
        assert marker and before==ref.stdout,(n,before,ref.stdout)
        outcome,teardown=tail.split(b'\n',1);status,error=json.loads(outcome)
        assert status==int(bool(ref.returncode)),(n,status,ref.stderr)
        if status:
            msg,line=error
            expected=('error: '+msg+(' at line '+str(line) if line else '')+'\n').encode()
            assert ref.stderr==expected,(n,ref.stderr,expected)
        else:assert error is None and not ref.stderr,(n,error,ref.stderr)
        assert teardown.startswith(b'JIT STATUS RESUMED ')and teardown.endswith(b' false\n'),teardown
        passed+=1
    for name in ['fib.holy','t_closure.holy','t_class.holy','t_json.holy','t_exceptreturn.holy','x64/gc_stress.holy']:
        ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(ROOT/'tests'/name)],env=env,capture_output=True,timeout=60)
        got=subprocess.run([str(driver),str(ROOT/'tests'/name)],env=env,capture_output=True,timeout=60)
        assert not got.returncode and not got.stderr and not ref.returncode and got.stdout.startswith(ref.stdout+b'JIT OUTCOME [0, null]\n') and got.stdout.endswith(b' false\n'),(name,got.stdout[-200:],got.stderr);passed+=1
    for body in ['if\n','extern:\n  I64 getpid()\nprint getpid()\n']:
        source=d/'rejected.holy';source.write_text(body)
        got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=60)
        assert got.returncode and b'JIT OUTCOME 'not in got.stdout and b'JIT STATUS RESUMED'not in got.stdout,(got.returncode,got.stdout,got.stderr);passed+=1
    source=d/'owned-error.holy'
    source.write_text('items = []\nfor i in range(10000):\n  append(items, str(i))\nraise "owned error " + str(len(items))\n')
    def timeout(_s,_f):raise TimeoutError('outcome heap checkpoint stalled')
    signal.signal(signal.SIGALRM,timeout)
    p=subprocess.Popen([str(driver),str(source),'--heap-checkpoints'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        signal.alarm(60)
        line=p.stdout.readline();assert line.startswith('JIT OWNED RANGES '),line
        ranges=json.loads(line[len('JIT OWNED RANGES '):]);assert len(ranges)>=3
        def mapped(address):
            return any(int(row.split('-')[0],16)<=address<int(row.split()[0].split('-')[1],16) for row in Path(f'/proc/{p.pid}/maps').read_text().splitlines())
        assert all(mapped(base) and mapped(base+size-1) for base,size in ranges);passed+=1
        p.stdin.write('\n');p.stdin.flush();assert p.stdout.readline()=='JIT HEAP UNMAPPED\n'
        assert not any(mapped(base) or mapped(base+size-1) for base,size in ranges);passed+=1
        out,err=p.communicate('\n',timeout=20)
        assert not p.returncode and not err and out.startswith('JIT OUTCOME [1, ["owned error 10000", 4]]\n')and out.endswith(' false\n'),(out,err);passed+=1
    finally:
        signal.alarm(0)
        if p.poll()is None:p.kill();p.communicate()
mode='Python-built native driver' if '--python-bootstrap'in sys.argv else 'seed-built native driver'
print(f'{passed}/{passed} isolated native outcome/unwind/copy gates ({mode}; no shared exceptions or tiering)')
