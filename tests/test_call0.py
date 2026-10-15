#!/usr/bin/env python3
"""Unsafe no-argument C ABI invocation agrees across reference/backends."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp,ir
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL',label)
source=ROOT/'tests/jit/call0.holy'
for backend in ['interp','x64','native']:
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],capture_output=True,text=True,timeout=60)
    check(r.returncode==0 and r.stdout=='-42\n-42\nnull rejected\n',backend+' invocation '+repr((r.stdout,r.stderr[-150:])))
# The compiled hs compiler must implement this new unsafe operation too.
with tempfile.TemporaryDirectory() as d:
    exe=str(Path(d)/'compiler');target=str(Path(d)/'program')
    env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/compile.holy'),'-o',exe],env=env,capture_output=True,text=True,timeout=120)
    if r.returncode==0:
        r=subprocess.run([exe,str(source),target],env=env,capture_output=True,text=True,timeout=120)
    if r.returncode==0:
        r=subprocess.run([target],capture_output=True,text=True,timeout=20)
    check(r.returncode==0 and r.stdout=='-42\n-42\nnull rejected\n','native hs compiler entry invocation '+repr((r.stdout,r.stderr[-150:])))
# IR evaluator shares the unsafe foreign-pointer guard with interp.
import contextlib,io
interp.reset_parse_state()
m=ir.build_module(interp.parse_program(source.read_text()))
out=io.StringIO()
with contextlib.redirect_stdout(out):ir.run_module(m,str(source.parent))
check(out.getvalue()=='-42\n-42\nnull rejected\n','IR evaluator invocation')
with tempfile.TemporaryDirectory() as d:
    for text,label in [('unsafe:\n  I64 x = call0(1)\n','wrong type'),('unsafe:\n  I64 x = call0()\n','arity'),('unsafe:\n  Ptr p = alloc(8)\n  I64 x = call0(p)\n','simulated pointer')]:
        p=Path(d)/'bad.holy';p.write_text(text)
        r=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(p)],capture_output=True,text=True)
        check(r.returncode!=0 and 'call0' in r.stderr,label)
print(f'{passed}/{passed+failed} call0 gates')
sys.exit(bool(failed))
