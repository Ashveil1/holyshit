#!/usr/bin/env python3
"""Bounded multiline note editing: canaries, wrap, newline, erase and cap."""
import contextlib, io, os, platform, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_x64, build_x64_ast
runner=[]
if platform.machine() not in ('x86_64','amd64'):
    qemu=shutil.which('qemu-x86_64')
    if not qemu:
        print('skip hosted x86 note buffer test: qemu-x86_64 unavailable');sys.exit(0)
    runner=[qemu]
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    for name,build in [('ir',build_x64),('ast',build_x64_ast)]:
        image=d/name
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build(str(ROOT/'kernel/unotebuftest.holy'),str(image))
        assert not rc
        r=subprocess.run(runner+[str(image)],capture_output=True,text=True,timeout=20)
        assert r.returncode==0 and '\nfails 0\n' in r.stdout and 'notebuf-done\n' in r.stdout,(name,r)
        assert r.stdout.count('ok ')==32,r.stdout
        print('ok bounded note buffers',name)
print('2/2 multiline note buffer gates')
