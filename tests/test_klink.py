#!/usr/bin/env python3
"""hs multiboot linker must reproduce Python kernel ELF from real payloads."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import Gen, build_xkernel, build_x64
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'selfhost'))
os.environ['HSPATH']=env['HSPATH']
passed=failed=0
with tempfile.TemporaryDirectory() as d:
    d=Path(d)
    driver=d/'link.hs'
    driver.write_text('import klink\nx = json_load(argv()[0])\ny = klink.link(x["payload"], x["stack_patch"])\nwrite_bytes(argv()[1], y)\n')
    # write_bytes lands in a separate PR, so use hex output until it is merged.
    driver.write_text('import klink\nx = json_load(argv()[0])\ny = klink.link(x["payload"], x["stack_patch"])\nH = "0123456789abcdef"\nout = []\nfor b in y:\n  append(out, H[b >> 4] + H[b & 15])\nprint join("", out)\n')
    with contextlib.redirect_stdout(io.StringIO()):
        rc=build_x64(str(driver),str(d/'link'))
    if rc: raise SystemExit('FAIL kernel linker build')
    files=sys.argv[1:] or ['kernel/kheaptest.hs','kernel/kring3.hs','kernel/ksyscall.hs','kernel/kpreempt.hs','kernel/kjsontest.hs','kernel/kushtest.hs']
    for name in files:
        capture={}
        original=Gen.build_image
        def wrapped(g,mod):
            a=original(g,mod)
            capture.update(payload={'code':list(a.code),'data':list(a.data),'labels':a.labels.copy(),'data_labels':a.data_labels.copy(),'fixups':a.fixups.copy()},stack_patch=g._stack_patch_pos)
            return a
        Gen.build_image=wrapped
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                rc=build_xkernel(str(ROOT/name),str(d/'want'),ir_backend=False)
        finally:
            Gen.build_image=original
        if rc: raise SystemExit('FAIL reference build '+name)
        fixture=d/'payload.json';fixture.write_text(json.dumps(capture))
        want=(d/'want').read_bytes()
        for mode,cmd in [('interp',[sys.executable,str(ROOT/'hs.py'),'run',str(driver),'--backend','interp',str(fixture)]),('x64',[str(d/'link'),str(fixture)])]:
            r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120)
            try: got=bytes.fromhex(''.join(r.stdout.split()))
            except ValueError:got=b''
            ok=r.returncode==0 and got==want
            passed+=int(ok);failed+=int(not ok)
            if not ok:
                diff=next(((i,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b),None)
                print('FAIL kernel link',name,mode,len(got),len(want),diff,r.stderr[-250:])
print(f'{passed}/{passed+failed} kernel linker image gates')
sys.exit(bool(failed) or not passed)
