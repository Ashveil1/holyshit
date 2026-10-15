#!/usr/bin/env python3
"""write_bytes: exact output, catchable validation failures, no partial writes."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
with tempfile.TemporaryDirectory() as d:
    for ix,expr in enumerate(['[]','[0, 1, 127, 128, 255]','[256]','[-1]','[true]','["x"]','1','null']):
        expected=None
        for backend in ['interp','x64']:
            target=str(Path(d)/f'bytes-{backend}.bin')
            source=Path(d)/'test.holy'
            source.write_text('try:\n  write_bytes('+repr(target).replace("'",'"')+', '+expr+')\n  print "ok"\nexcept as e:\n  print "caught"\n')
            r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],capture_output=True,text=True)
            got=(r.stdout,r.returncode,Path(target).read_bytes() if Path(target).exists() else None)
            if backend=='interp':expected=got
            else:
                ok=got==expected
                passed+=int(ok);failed+=int(not ok)
                if not ok:print('FAIL',expr,got,expected,r.stderr[-150:])
print(f'{passed}/{passed+failed} passed')
sys.exit(bool(failed))
