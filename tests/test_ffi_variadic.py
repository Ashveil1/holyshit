#!/usr/bin/env python3
"""Typed C variadic declarations across reference, IR, gcc, x64 and hs."""
from pathlib import Path
import contextlib,io,json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp,ir
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok: print('FAIL',label,flush=True)
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);c=d/'var.c';so=d/'var.so'
    kinds=['I64','F64']*12+['Str','Ptr','U64']
    types={'I64':'long long','F64':'double','Str':'char *','Ptr':'void *','U64':'unsigned long long'}
    lines=['#include <stdarg.h>','#include <stdint.h>','double weighted(long long marker, ...) {','va_list ap; va_start(ap, marker); double total=marker;']
    expected=7.0
    for i,k in enumerate(kinds):
        lines.append(types[k]+f' p{i}=va_arg(ap, {types[k]});')
        if k=='Str':term=f'p{i}[0]';v=65
        elif k=='Ptr':term=f'(intptr_t)p{i}';v=0
        else:term=f'p{i}';v=i+1+(.5 if k=='F64' else 0)
        lines.append(f'total += {term} * {i+1};');expected+=v*(i+1)
    lines+=['va_end(ap);return total;}']
    c.write_text('\n'.join(lines))
    subprocess.run(['gcc','-shared','-fPIC',str(c),'-o',str(so)],check=True,capture_output=True)
    decl=', '.join(k+f' p{i}' for i,k in enumerate(kinds))
    args=', '.join('"A"' if k=='Str' else '0' if k=='Ptr' else str(i+1)+('.5' if k=='F64' else '') for i,k in enumerate(kinds))
    text='extern from "'+str(so)+'":\n  F64 weighted(I64 marker, ..., '+decl+')\nprint weighted(7, '+args+')\n'
    source=d/'var.holy';source.write_text(text)
    interp.reset_parse_state();prog=interp.parse_program(text)
    output=io.StringIO()
    with contextlib.redirect_stdout(output):ir.run_module(ir.build_module(prog),str(d))
    check(output.getvalue()==str(expected)+'\n','IR execution independent result '+repr(output.getvalue()))
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'out';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)],env=env,capture_output=True,text=True,timeout=90)
            if r.returncode==0:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=20)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=90)
        check(r.returncode==0 and r.stdout==str(expected)+'\n',backend+' '+repr((r.returncode,r.stdout,r.stderr[-150:])))
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'fmt',str(source)],capture_output=True,text=True)
    check(r.returncode==0 and '..., F64' not in r.stdout and '..., I64 p0' in r.stdout,'formatter preserves typed boundary')
    # A type failure must occur before any printf side effect.
    bad=d/"bad.holy"
    bad.write_text('extern:\n  I64 printf(Str format, ..., I64 value)\ntry:\n  printf("TARGET RAN %lld\\n", true)\nexcept:\n  print "caught"\n')
    for backend in ["interp","native","x64"]:
        r=subprocess.run([sys.executable,str(ROOT/"hs.py"),"run",str(bad),"--backend",backend],env=env,capture_output=True,text=True,timeout=90)
        check(r.returncode==0 and r.stdout=="caught\n",backend+" reject variadic Bool before C")
    for decl in ['I64 bad(..., I64 x)','I64 bad(I64 x, ...)','I64 bad(I64 x, ..., I64 y, ..., I64 z)']:
        text='extern:\n  '+decl+'\n'
        try:interp.parse_program(text);ok=False
        except interp.HSErr:ok=True
        check(ok,'reject invalid marker '+decl)
print(f'{passed}/{passed+failed} typed variadic FFI gates')
sys.exit(bool(failed))
