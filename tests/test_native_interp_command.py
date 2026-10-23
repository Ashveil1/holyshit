#!/usr/bin/env python3
"""Python-free interpreter command: args, imports, errors and cleanup."""
from pathlib import Path
import os
import platform
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
if platform.machine() not in ('x86_64','amd64'):
    print('skip command: pinned bootstrap seed is x86-64')
    sys.exit(0)
passed=0
with tempfile.TemporaryDirectory(prefix='hs interp source space ') as d:
 d=Path(d);bindir=d/'bin';bindir.mkdir()
 for name in ['dirname','sha256sum','mktemp','rm']:
    (bindir/name).symlink_to(shutil.which(name))
 source=d/'source file.holy'
 (d/'helper.holy').write_text('value = 7\n')
 env=dict(os.environ,PATH=str(bindir),HS_INTERP_COMMAND='works',TMPDIR=str(d))
 def run(text,args=()):
    source.write_text(text)
    r=subprocess.run(['/bin/sh',str(ROOT/'scripts/run-interp-native.sh'),str(source)]+list(args),cwd=d,env=env,capture_output=True,text=True,timeout=240)
    assert not list(d.glob('holyshit-interp.*'))
    return r
 r=run('import helper\nprint helper.value\nprint argv()\nprint env("HS_INTERP_COMMAND")\n',['hello world','$5'])
 assert r.returncode==0 and r.stdout=='7\n[hello world, $5]\nworks\n',(r.stdout,r.stderr)
 passed+=1
 r=run('print "before"\nprint 1 / 0\n')
 assert r.returncode==1 and r.stdout=='before\n' and 'division by zero' in r.stderr,(r.stdout,r.stderr)
 passed+=1
 r=run('print "must not run"\nunsafe:\n  Ptr p = alloc(8)\n')
 assert r.returncode==3 and not r.stdout and 'irinterp: unsupported' in r.stderr,(r.returncode,r.stdout,r.stderr)
 passed+=1
 r=run('def broken(:\n')
 assert r.returncode==1 and not r.stdout,(r.stdout,r.stderr)
 passed+=1
 r=subprocess.run(['/bin/sh',str(ROOT/'scripts/run-interp-native.sh')],env=env,capture_output=True,text=True)
 assert r.returncode==2 and 'usage:' in r.stderr
 passed+=1
print(f'{passed}/{passed} Python-free interpreter command gates')
