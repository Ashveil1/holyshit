#!/usr/bin/env python3
"""Unpacked assembler sections produce the same linked image, without pack()."""
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import interp,ir,irx64,x64
passed=failed=0
for name in ['fib.hs','t_class.hs','t_closure.hs','t_json.hs','t_exceptreturn.hs']:
    source=ROOT/'tests'/name
    interp.reset_parse_state();m=ir.build_module(interp.parse_program(source.read_text()))
    expected=irx64.GenIR(m,str(source.parent)).build_ir_image()
    g=irx64.GenIR(m,str(source.parent))
    with patch.object(x64,'pack',side_effect=AssertionError('sections must not pack ELF')):
        sections=g.build_ir_sections()
    lo=x64.layout(len(sections['code']),len(sections['data']))
    image=x64.pack(g.a.resolve(lo['text_vaddr'],lo['data_vaddr']),sections['data'],sections['entry'],lo)
    ok=image==expected;passed+=int(ok);failed+=int(not ok)
    if not ok:print('FAIL section relink',name)

# Unresolved extern sections require explicit opt-in; packing stays unchanged.
interp.reset_parse_state()
m=ir.build_module(interp.parse_program('extern:\n  I64 getpid()\nprint getpid()\n'))
try:
    irx64.GenIR(m,str(ROOT)).build_ir_sections()
except interp.HSErr as e:
    assert 'extern symbols are not supported' in str(e)
else:
    raise AssertionError('default sections accepted unresolved externs')
g=irx64.GenIR(m,str(ROOT))
s=g.build_ir_extern_sections()
assert 'getpid' in g.ffi_syms and 'ffi_got_' in g.a.data_labels
assert bytes(s['data'][g.a.data_labels['ffi_got_']:]) == bytes(8*len(g.ffi_syms))

print(f'{passed}/{passed+failed} JIT section image-equality gates; extern opt-in checked')
sys.exit(bool(failed))
