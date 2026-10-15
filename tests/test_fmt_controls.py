#!/usr/bin/env python3
"""Formatter must not invent unsupported escapes that change string bytes."""
from pathlib import Path
import os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT));import fmt,interp
# Include every ASCII control byte. Existing escapes cover newline/CR/tab/NUL.
chars=''.join(chr(i) for i in range(32))+chr(127)+'"\\'
def literal(s):
    return '"'+s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t').replace('\0','\\0')+'"'
src='s = '+literal(chars)+'\nprint s\nprint f"<{s}>"\n'
interp.reset_parse_state();once=fmt.fmt_program(interp.parse_program(src,raw=True))
interp.reset_parse_state();twice=fmt.fmt_program(interp.parse_program(once,raw=True))
assert once==twice,'Python formatter not idempotent'
assert once==src,'Python formatter changed canonical control byte spelling'
env=dict(os.environ,HSPATH=str(ROOT/'selfhost'),HSROOT=str(ROOT));passed=2;failed=0
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'controls.holy';source.write_text(src)
    before=subprocess.run([sys.executable,str(ROOT/'interp.py'),str(source)],capture_output=True,check=True).stdout
    for backend in ['interp','x64','native-hs']:
        if backend=='interp':cmd=[sys.executable,str(ROOT/'interp.py'),str(ROOT/'selfhost/fmt.holy'),str(source)]
        else:
            exe=d/('formatter-'+backend)
            if backend=='x64':cmd=[sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/fmt.holy'),'-o',str(exe)]
            else:cmd=[str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/fmt.holy'),str(exe)]
            r=subprocess.run(cmd,env=env,capture_output=True,timeout=90);assert not r.returncode,r.stderr
            cmd=[str(exe),str(source)]
        r=subprocess.run(cmd,env=env,capture_output=True,timeout=60)
        ok=not r.returncode and r.stdout==once.encode();passed+=ok;failed+=not ok
        if not ok:print('FAIL selfhost formatting',backend,repr(r.stdout),repr(r.stderr))
    output=d/'formatted.holy';output.write_text(once)
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(output),str(exe)],env=env,capture_output=True,timeout=90)
            if not r.returncode:r=subprocess.run([str(exe)],capture_output=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(output),'--backend',backend],env=env,capture_output=True,timeout=90)
        # gcc has a pre-existing C-string embedded-NUL limit. Verify unchanged
        # behavior there, not a new cross-backend embedded-NUL promise.
        expected=before
        if backend=='native':
            original=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend','native'],env=env,capture_output=True,timeout=90)
            assert not original.returncode,original.stderr
            expected=original.stdout
        ok=not r.returncode and r.stdout==expected;passed+=ok;failed+=not ok
        if not ok:print('FAIL formatted execution',backend,r.returncode,repr(r.stdout),repr(r.stderr))
print(f'{passed}/{passed+failed} formatter control-byte gates (all ASCII controls, literal + interpolation)')
sys.exit(bool(failed))
