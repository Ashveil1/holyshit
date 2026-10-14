#!/usr/bin/env python3
"""Self-hosted CFG verifier: accept valid corpus and reject malformed modules."""
import contextlib
import copy
import glob
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp
import ir
from x64gen import build_x64
env=dict(os.environ,HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
cases=[]
for f in sorted(glob.glob(str(ROOT/'tests/*.hs'))+glob.glob(str(ROOT/'examples/*.hs'))):
    try:
        interp.reset_parse_state()
        m=ir.build_module(interp.parse_program(Path(f).read_text()))
        ir.verify_module(m)
        cases.append((Path(f).name,m))
    except Exception:
        pass
base=ir.build_module(interp.parse_program('a = 1\nprint(a + 2)\n'))
def variant(label, change):
    m=copy.deepcopy(base)
    change(m,m['funcs'][m['entry']])
    cases.append((label,m))
variant('missing entry',lambda m,f:m.update(entry='missing'))
variant('duplicate function',lambda m,f:m['order'].append(m['entry']))
variant('missing function',lambda m,f:m['order'].append('missing'))
variant('duplicate block',lambda m,f:f['blocks'].append(copy.deepcopy(f['blocks'][0])))
variant('missing block',lambda m,f:f.update(entry='missing'))
variant('no terminator',lambda m,f:f['blocks'][0].update(term=None))
variant('bad terminator',lambda m,f:f['blocks'][0].update(term={'term':'oops','line':1}))
variant('bad jump',lambda m,f:f['blocks'][0].update(term={'term':'jmp','to':'missing','line':1}))
variant('undefined return',lambda m,f:f['blocks'][0].update(term={'term':'ret','val':'%missing','line':1}))
variant('undefined bin',lambda m,f:f['blocks'][0]['instrs'].append({'op':'bin','dest':'%new','binop':'+','l':'%missing','r':'%missing','line':1}))
variant('duplicate temp',lambda m,f:f['blocks'][0]['instrs'].append(copy.deepcopy(f['blocks'][0]['instrs'][0])))
variant('bad opcode',lambda m,f:f['blocks'][0]['instrs'].append({'op':'oops','line':1}))
variant('phi entry',lambda m,f:f['blocks'][0]['instrs'].append({'op':'phi','dest':'%new','arms':[],'line':1}))
def fits62(x):
    if type(x) is int:return -(1<<61)<=x<(1<<61)
    if isinstance(x,(list,tuple)):return all(fits62(v) for v in x)
    if isinstance(x,dict):return all(fits62(v) for v in x.values())
    return True
passed=failed=native_skipped=0
with tempfile.TemporaryDirectory() as d:
    exe=str(Path(d)/'verify')
    old=os.environ.get('HSPATH')
    os.environ['HSPATH']=env['HSPATH']
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build_x64(str(ROOT/'selfhost/be/verify_run.hs'),exe)
    finally:
        if old is None:os.environ.pop('HSPATH',None)
        else:os.environ['HSPATH']=old
    if rc:raise SystemExit('FAIL build verifier')
    p=str(Path(d)/'module.json')
    for name,m in cases:
        try:
            ir.verify_module(m)
            want=None
        except interp.HSErr as e:
            want=e.msg
        Path(p).write_text(json.dumps(m))
        for backend,cmd in [('interp',[sys.executable,str(ROOT/'hs.py'),'run',str(ROOT/'selfhost/be/verify_run.hs'),'--backend','interp',p]),('x64',[exe,p])]:
            if backend=='x64' and not fits62(m):
                native_skipped+=1
                continue
            r=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30)
            text=r.stdout+r.stderr
            ok=text.strip()=='ok' if want is None else want in text and text.strip()!='ok'
            passed+=int(ok);failed+=int(not ok)
            if not ok:print('FAIL',name,backend,'want',want,'got',text[:150])
print(f'{passed}/{passed+failed} passed ({native_skipped} out-of-width module interp-only)')
sys.exit(bool(failed))
