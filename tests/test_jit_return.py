#!/usr/bin/env python3
"""A native module returns normally; no shared runtime or tiers claimed."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=0
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp);driver=d/'driver'
    if '--python-bootstrap' in sys.argv:
        build=[sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/jit_return_probe.holy'),'-o',str(driver)]
    else:
        build=[str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_return_probe.holy'),str(driver)]
    r=subprocess.run(build,env=env,capture_output=True,timeout=240)
    assert not r.returncode,r.stderr[-300:];passed+=1
    suffix=b'0\nJIT RETURNED\nJIT IMAGE RELEASED false\n'
    for name in ['fib.holy','t_closure.holy','t_lambda.holy','floatlit.holy','t_json.holy','t_class.holy','t_exceptreturn.holy','x64/gc_stress.holy']:
        source=ROOT/'tests'/name
        want=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=60)
        got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=60)
        assert want.returncode==got.returncode==0 and got.stderr==want.stderr and got.stdout==want.stdout+suffix,(name,got.returncode,got.stdout[-200:],got.stderr[-200:]);passed+=1
    source=d/'input.holy';source.write_text('print argv()\nprint env("HS_RETURN_CHECK")\n')
    r=subprocess.run([str(driver),str(source)],env=dict(env,HS_RETURN_CHECK='present'),capture_output=True,timeout=60)
    assert not r.returncode and r.stdout==b'[]\npresent\n'+suffix,(r.stdout,r.stderr);passed+=1
    source.write_text('print "before"\nprint 1 / 0\n')
    ref=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=20)
    got=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=60)
    assert (got.returncode,got.stdout,got.stderr)==(ref.returncode,ref.stdout,ref.stderr),(got.stdout,got.stderr);assert b'JIT RETURNED'not in got.stdout;passed+=1
    source.write_text('extern:\n  I64 getpid()\nprint getpid()\n')
    r=subprocess.run([str(driver),str(source)],env=env,capture_output=True,timeout=60)
    assert r.returncode and b'extern symbols are not supported'in r.stderr and b'JIT RETURNED'not in r.stdout,r.stderr;passed+=1
mode='Python-built native driver' if '--python-bootstrap'in sys.argv else 'seed-built native driver'
print(f'{passed}/{passed} one-shot module-return gates ({mode}; not shared ABI or tiering)')
