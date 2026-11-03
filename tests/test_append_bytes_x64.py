#!/usr/bin/env python3
"""append_bytes: exact appended bytes, catchable validation failures,
validation before open (existing bytes and missing paths preserved)."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
with tempfile.TemporaryDirectory() as d:
    binpath=str(Path(d)/'in.bin')
    Path(binpath).write_bytes(b'\x00\x80A\xffhi')
    emptypath=str(Path(d)/'empty.bin')
    Path(emptypath).write_bytes(b'')
    q=lambda s: repr(s).replace("'",'"')
    exprs=['[]','[0, 1, 127, 128, 255]','[256]','[-1]','[true]','["x"]','1','null',
           'read_bytes('+q(binpath)+')','read_bytes('+q(emptypath)+')']
    for seed in (b'AB', None):
        for expr in exprs:
            expected=None
            for backend in ['interp','x64','native']:
                target=str(Path(d)/f'append-{backend}.bin')
                Path(target).unlink(missing_ok=True)
                if seed is not None:
                    Path(target).write_bytes(seed)
                source=Path(d)/'test.holy'
                source.write_text('try:\n  append_bytes('+repr(target).replace("'",'"')+', '+expr+')\n  print "ok"\nexcept as e:\n  print "caught"\n')
                r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],capture_output=True,text=True)
                got=(r.stdout,r.returncode,Path(target).read_bytes() if Path(target).exists() else None)
                if backend=='interp':expected=got
                else:
                    ok=got==expected
                    passed+=int(ok);failed+=int(not ok)
                    if not ok:print('FAIL',seed,expr,got,expected,r.stderr[-150:])
    # append after write_bytes preserves the prefix; an empty append to a
    # missing path still creates the file (append_text convention, 0644)
    prog=Path(d)/'seq.holy'
    prog.write_text(
        'write_bytes('+q(str(Path(d)/"seq.bin"))+', [65, 66])\n'
        'append_bytes('+q(str(Path(d)/"seq.bin"))+', read_bytes('+q(binpath)+'))\n'
        'append_bytes('+q(str(Path(d)/"seq.bin"))+', [67])\n'
        'append_bytes('+q(str(Path(d)/"new.bin"))+', [])\n'
        'print byte_len(read_bytes('+q(str(Path(d)/"new.bin"))+'))\n')
    expected=None
    for backend in ['interp','x64','native']:
        for p in ('seq.bin','new.bin'):
            (Path(d)/p).unlink(missing_ok=True)
        r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(prog),'--backend',backend],capture_output=True,text=True)
        got=(r.stdout,r.returncode,
             (Path(d)/'seq.bin').read_bytes() if (Path(d)/'seq.bin').exists() else None,
             (Path(d)/'new.bin').read_bytes() if (Path(d)/'new.bin').exists() else None)
        if backend=='interp':expected=got
        else:
            ok=got==expected
            passed+=int(ok);failed+=int(not ok)
            if not ok:print('FAIL seq',backend,got,expected,r.stderr[-150:])
print(f'{passed}/{passed+failed} passed')
sys.exit(bool(failed))
