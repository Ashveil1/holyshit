#!/usr/bin/env python3
"""Boot assembler in hs must match every Asm32 instruction and fixup."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64 import Asm32, CC
from x64gen import build_x64
asm = Asm32()
lines = ['import asm32', 'a = asm32.Asm32()']
count = 0
def emit(op, *args):
    global count
    getattr(asm, op)(*args)
    lines.append('a.'+op+'('+', '.join(json.dumps(x) for x in args)+')')
    count += 1
for op in ['cli','hlt','nop','rdmsr','wrmsr']:
    emit(op)
for d in range(8):
    for s in range(8):
        for op in ['mov_rr','mov_cr','mov_rcr','xor_rr']:
            emit(op,d,s)
    for imm in [0,1,127,255,65535,2**31,2**32-1]:
        for op in ['mov_ri32','or_ri32','add_ri32']:
            emit(op,d,imm)
    for imm in [-128,-1,0,127,255]:
        emit('add_ri8',d,imm)
    emit('dec_r',d)
    emit('mov_ri32_abs',d,'target')
    emit('mov_mr_abs','target',d)
    emit('mov_rm_abs',d,'target')
for sel in [0,8,0x28,65535]:
    emit('ltr',sel)
    emit('jmp_far',sel,'target')
    emit('jmp_far_abs',sel,0x12345678)
emit('lgdt_abs','target')
emit('jmp','target')
for cc in CC:
    emit('jcc',cc,'target')
emit('label','target')
emit('nop')
# The reference rel32 packs unsigned, so preserve its forward-fixup contract.
lines += ['print json_str(a.resolve(1048576))']
want = list(asm.resolve(1048576))
env = dict(os.environ,HSPATH=str(ROOT/'selfhost'))
passed = 0
with tempfile.TemporaryDirectory() as d:
    source = Path(d)/'boot.holy'; source.write_text('\n'.join(lines)+'\n')
    old = os.environ.get('HSPATH'); os.environ['HSPATH'] = env['HSPATH']
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = build_x64(str(source),str(Path(d)/'boot'))
    finally:
        if old is None: os.environ.pop('HSPATH',None)
        else: os.environ['HSPATH'] = old
    if rc: raise SystemExit('FAIL boot assembler build')
    for cmd in [[sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend','interp'],[str(Path(d)/'boot')]]:
        r = subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120)
        ok = r.returncode == 0 and json.loads(r.stdout) == want
        passed += int(ok)
        if not ok:
            got=json.loads(r.stdout) if r.stdout else []
            bad=[(i,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b]
            print('FAIL',cmd,r.stderr[-200:],len(got),bad[:8])
print(f'{passed}/2 boot assembler gates ({count} instructions; {len(want)} bytes)')
sys.exit(passed != 2)
