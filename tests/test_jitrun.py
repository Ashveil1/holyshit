#!/usr/bin/env python3
"""Experimental in-process eager JIT, native hs compiler and generated code."""
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
    exe=str(Path(d)/'jit')
    r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_run.hs'),exe],env=env,capture_output=True,text=True,timeout=240)
    check(r.returncode==0,'native JIT driver build '+r.stderr[-200:])
    if r.returncode:sys.exit(1)
    for name in ['fib.hs','t_closure.hs','t_lambda.hs','floatlit.hs','t_json.hs','t_class.hs','t_exceptreturn.hs','t_raise.hs','err_divfloat.hs','x64/gc_stress.hs']:
        source=str(ROOT/'tests'/name)
        want=subprocess.run([sys.executable,str(ROOT/'interp.py'),source],env=env,capture_output=True,timeout=60)
        got=subprocess.run([exe,source],env=env,capture_output=True,timeout=60)
        check((got.stdout,got.stderr,got.returncode)==(want.stdout,want.stderr,want.returncode),name+' '+repr((got.stdout[-100:],got.stderr[-150:],got.returncode)))
    source=Path(d)/'arguments.hs'
    source.write_text('print argv()\nprint env("HS_JIT_CHECK")\n')
    local=dict(env,HS_JIT_CHECK='works')
    r=subprocess.run([exe,str(source),'hello world','$5'],env=local,capture_output=True,text=True,timeout=60)
    check(r.returncode==0 and r.stdout=='[hello world, $5]\nworks\n','arguments/environment '+repr((r.stdout,r.stderr,r.returncode)))
    source.write_text('print 2305843009213693951 + 1\n')
    r=subprocess.run([exe,str(source)],env=env,capture_output=True,text=True,timeout=60)
    check(r.returncode==97 and '62-bit' in r.stderr,'documented tagged-Int limit, no silent wrap/fallback')
    source.write_text('extern:\n  I64 getpid()\nprint getpid()\n')
    r=subprocess.run([exe,str(source)],env=env,capture_output=True,text=True,timeout=60)
    check(r.returncode!=0 and 'extern symbols are not supported' in r.stdout+r.stderr,'reject unbound external symbols')
print(f'{passed}/{passed+failed} eager in-process JIT gates (no tiering)')
sys.exit(bool(failed))
