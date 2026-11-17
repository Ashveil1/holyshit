#!/usr/bin/env python3
"""Explicit hosted IR FFI: real SysV calls; portable driver remains fail-closed."""
from pathlib import Path
import os, platform, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent
if platform.machine() not in ('x86_64', 'amd64'):
    print('skip hosted IR FFI: explicit Linux x86-64 backend')
    raise SystemExit(0)
env = dict(os.environ, HSPATH=f'{ROOT}/selfhost:{ROOT}/selfhost/be', HSROOT=str(ROOT), HS_FFI_TEXT='ทดสอบ')
passed = failed = 0
def check(ok, label, detail=''):
    global passed, failed
    passed += bool(ok); failed += not ok
    if not ok: print('FAIL', label, detail, flush=True)
with tempfile.TemporaryDirectory() as td:
    td = Path(td); driver = td/'ffi'; portable = td/'portable'
    for source, output in [('irinterp_ffi_run.holy',driver), ('irinterp_run.holy',portable)]:
        r = subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be'/source),str(output)],env=env,capture_output=True,timeout=180)
        assert r.returncode == 0 and output.exists(), r.stderr
    fixture = td/'fixture.c'; so = td/'fixture.so'
    fixture.write_text('''
#include <stdint.h>
#include <stdlib.h>
static int calls;
long long count(void) { return calls; }
long long touch(long long a, unsigned long long b) { calls++; return a+b; }
long long signed_ret(void) { return -42; }
unsigned long long wide_ret(void) { return UINT64_MAX; }
const char *null_str(void) { return 0; }
const char *unicode_str(void) { return "ทดสอบ"; }
double echo(double x) { return x; }
long long identity(long long x) { return x; }
long long mutate(char *s) { s[0] = 88; return s[0]; }
long long weighted(long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h) {return a+2*b+3*c+4*d+5*e+6*f+7*g+8*h;}
double mixed(long long a,double b,long long c,double d,long long e,double f,long long g,double h,long long i,double j,long long k,double l,long long m,double n,long long o,double p,double q,double r) {return a+2*b+3*c+4*d+5*e+6*f+7*g+8*h+9*i+10*j+11*k+12*l+13*m+14*n+15*o+16*p+17*q+18*r;}
''')
    subprocess.run(['gcc','-shared','-fPIC',str(fixture),'-o',str(so)],check=True,capture_output=True)
    def run(text, binary=driver):
        source = td/'program.holy'; source.write_text(text)
        return subprocess.run([str(binary),str(source)],env=env,capture_output=True,timeout=30)
    def parity(label,text):
        source = td/'program.holy'; source.write_text(text)
        expected = subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],env=env,capture_output=True,timeout=30)
        actual = run(text)
        check((actual.returncode,actual.stdout,actual.stderr)==(expected.returncode,expected.stdout,expected.stderr),label,repr((expected,actual)))
    parity('libc/libm scalar and UTF-8', '''extern:
  I64 puts(Str s)
  U64 strlen(Str s)
  Str getenv(Str s)
  Ptr malloc(U64 n)
  U0 free(Ptr p)
extern from "m":
  F64 sin(F64 x)
  F64 pow(F64 x, F64 y)
print "before"
puts("hello")
print strlen("ไทย")
print getenv("HS_FFI_TEXT")
print sin(0.0)
print pow(1.5, 3.0)
p = malloc(32)
print p == 0
free(p)
print "after"
''')
    base = 'extern from "fixture.so":\n'
    for name,decl,args in [
        ('signed','I64 signed_ret()','signed_ret()'),
        ('null','Str null_str()','null_str()'),
        ('unicode','Str unicode_str()','unicode_str()'),
        ('int-stack','I64 weighted(I64 a,I64 b,I64 c,I64 d,I64 e,I64 f,I64 g,I64 h)','weighted(1,2,3,4,5,6,7,8)'),
        ('mixed-stack','F64 mixed(I64 a,F64 b,I64 c,F64 d,I64 e,F64 f,I64 g,F64 h,I64 i,F64 j,I64 k,F64 l,I64 m,F64 n,I64 o,F64 p,F64 q,F64 r)','mixed(1,2.5,3,4.5,5,6.5,7,8.5,9,10.5,11,12.5,13,14.5,15,16.5,17.5,18.5)')]:
        parity(name,base+'  '+decl+'\nprint '+args+'\n')
    parity('exact Float payloads',base+'  F64 echo(F64 x)\nfor x in [0.0, -0.0, 1.2345678901234567, 1e-300, 1e300]:\n  y = echo(x)\n  print y == x\n  print y\n')
    for value in ['true','-1','"bad"','null','[]']:
        parity('conversion before side effects '+value,base+'  I64 touch(I64 a,U64 b)\n  I64 count()\ntry:\n  touch(1,'+value+')\nexcept as e:\n  print e\nprint count()\n')
    parity('signed Int boundaries',base+'  I64 identity(I64 x)\nprint identity(2305843009213693951)\nprint identity(-2305843009213693951 - 1)\n')
    parity('foreign string writes do not mutate guest string',base+'  I64 mutate(Str s)\nx = "hello"\nprint mutate(x)\nprint x\n')
    (td/'support.holy').write_text(base+'  I64 signed_ret()\ndef answer():\n  return signed_ret()\n')
    parity('module frame and relative library', 'import support\nprint support.answer()\n')
    (td/'support.holy').write_text('extern from "fixture.c":\n  I64 count()\n')
    r=run('print "must not run"\nimport support\n')
    check(r.returncode==3 and not r.stdout,'unsupported imported signature before effects',repr(r))
    r=run(base+'  I64 count()\ncount()\nbefore = len(split(read_text("/proc/self/maps"), "\\n"))\nfor i in range(200):\n  count()\nafter = len(split(read_text("/proc/self/maps"), "\\n"))\nprint before == after\n')
    check(r.returncode==0 and r.stdout==b'true\n','call adapters released after use',repr(r))
    for prefix,value in [('def f():\n  return 1\n','f'), ('','len'), ('import support\n','support')]:
        (td/'support.holy').write_text('value = 1\n')
        parity('guest callable/module conversion kind '+value,base+'  I64 touch(I64 a,U64 b)\n'+prefix+'try:\n  touch(1,'+value+')\nexcept as e:\n  print e\n')
    r=run(base+'  U64 wide_ret()\nprint wide_ret()\n')
    check(r.returncode==97 and r.stderr==b'error: Int outside the 62-bit range\n','wide return cannot silently truncate',repr(r))
    for text,label in [
        ('extern from "fixture.c":\n  I64 count()\n','C-source compiler not implicit'),
        ('extern:\n  I64 printf(Str s, ..., I64 x)\n','variadic explicit refusal')]:
        r=run('print "must not run"\n'+text)
        check(r.returncode==3 and not r.stdout and b'unsupported' in r.stderr,label,repr(r))
    r=run('print "must not run"\nextern:\n  U64 strlen(Str s)\nprint strlen("x")\n',portable)
    check(r.returncode==3 and not r.stdout,'portable default remains fail-closed',repr(r))
print(f'{passed}/{passed+failed} hosted IR FFI gates')
raise SystemExit(bool(failed))
