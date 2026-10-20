#!/usr/bin/env python3
"""Native eager compiler binds libc, libm and a prebuilt C library in memory."""
from pathlib import Path
import os, subprocess, sys, tempfile
from ctypes.util import find_library
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok: print('FAIL',label,flush=True)
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);exe=d/'jit'
    built=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/jit_run.holy'),str(exe)],env=env,capture_output=True,text=True,timeout=240)
    check(built.returncode==0,'driver build '+built.stderr[-200:])
    if built.returncode:sys.exit(1)
    c=d/'fixture.c';so=d/'fixture.so'
    kinds=['I64','F64']*16
    params=', '.join(('double' if k=='F64' else 'long long')+f' p{i}' for i,k in enumerate(kinds))
    expr=' + '.join(f'p{i} * {i+1}' for i in range(len(kinds)))
    c.write_text('long labs(long x) {return 9182;}\n'+'double weighted('+params+') { return '+expr+'; }\n')
    subprocess.run(['gcc','-shared','-fPIC',str(c),'-o',str(so)],check=True,capture_output=True)
    decl=', '.join(k+f' p{i}' for i,k in enumerate(kinds))
    args=', '.join(str(i+1)+('.5' if k=='F64' else '') for i,k in enumerate(kinds))
    libm=find_library('m')
    assert libm, 'libm required for ABI fixture'
    # Reference resolves short name; native driver accepts the loader soname.
    cases=[('libc','extern:\n  I64 labs(I64 x)\nprint labs(-17)\n','17\n'),
      ('libm','extern from "'+libm+'":\n  F64 sqrt(F64 x)\nprint sqrt(81.0)\n','9.0\n'),
      ('collision','extern from "'+str(so)+'":\n  I64 labs(I64 x)\nprint labs(-17)\n','9182\n'),
      ('relative','extern from "./fixture.so":\n  I64 labs(I64 x)\nprint labs(-17)\n','9182\n'),
      ('stack','extern from "'+str(so)+'":\n  F64 weighted('+decl+')\nprint weighted('+args+')\n',str(float(sum((i+1+(.5 if k=='F64' else 0))*(i+1) for i,k in enumerate(kinds))))+'\n')]
    for label,source,expected in cases:
        path=d/(label+'.hs');path.write_text(source)
        want=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(path)],env=env,capture_output=True,text=True,timeout=30)
        if label=='libm':
            reference=d/'reference-libm.holy';reference.write_text(source.replace(libm,'m'))
            want=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(reference)],env=env,capture_output=True,text=True,timeout=30)
        # CI diagnostics: on a driver timeout, dump the hung process state
        # (/proc + gdb backtrace) before re-raising. Pure wait until then.
        _p=subprocess.Popen([str(exe),str(path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            _o,_e=_p.communicate(timeout=30)
            got=subprocess.CompletedProcess(_p.args,_p.returncode,_o,_e)
        except subprocess.TimeoutExpired:
            print('HANGDUMP begin',label,flush=True)
            try:
                for _t in os.listdir('/proc/%d/task'%_p.pid):
                    for _fn in ('wchan','syscall','stack'):
                        try: print('task',_t,_fn,open('/proc/%d/task/%s/%s'%(_p.pid,_t,_fn)).read().strip()[:400],flush=True)
                        except Exception as _x: print('task',_t,_fn,'unreadable',_x,flush=True)
            except Exception as _x: print('proc dump failed',_x,flush=True)
            print('PARTIAL stdout:',repr(_x.output),flush=True)
            print('PARTIAL stderr:',repr(_x.stderr),flush=True)
            try:
                _bt=subprocess.run(['gdb','-batch','-p',str(_p.pid),'-ex','thread apply all bt'],capture_output=True,text=True,timeout=40)
                print('GDBBT>>>',_bt.stdout[-4000:],_bt.stderr[-400:],flush=True)
            except Exception as _x: print('gdb failed',_x,flush=True)
            print('HANGDUMP end',flush=True)
            _p.kill();_p.communicate()
            raise
        check(want.returncode==0 and want.stdout==expected and (got.returncode,got.stdout,got.stderr)==(want.returncode,want.stdout,want.stderr),label+' '+repr((got.returncode,got.stdout,got.stderr[-200:])))
    for label,source,error in [
      ('conflicting-owner','extern:\n  I64 labs(I64 x)\nprint labs(-17)\nextern from "'+str(so)+'":\n  I64 labs(I64 x)\nprint "TARGET RAN"\nprint labs(-17)\n','conflicting library owners'),
      ('reserved-symbol','extern from "'+str(so)+'":\n  I64 fflush(Ptr x)\nprint "TARGET RAN"\nprint fflush(0)\n','reserved for libc'),
      ('missing-symbol','extern:\n  I64 hs_missing_symbol_1938()\nprint "TARGET RAN"\nprint hs_missing_symbol_1938()\n','unknown extern symbol'),
      ('missing-library','extern from "/no/such/hs_library_1938.so":\n  I64 missing()\nprint "TARGET RAN"\nprint missing()\n','cannot load library')]:
        path=d/(label+'.hs');path.write_text(source)
        got=subprocess.run([str(exe),str(path)],env=env,capture_output=True,text=True,timeout=30)
        check(got.returncode!=0 and error in got.stdout+got.stderr and 'TARGET RAN' not in got.stdout,label+' '+repr((got.returncode,got.stdout,got.stderr[-200:])))
print(f'{passed}/{passed+failed} eager in-process extern gates')
sys.exit(bool(failed))
