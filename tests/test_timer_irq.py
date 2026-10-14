#!/usr/bin/env python3
"""Timer IRQ without a scheduler preserves interrupted GPRs, every time.
A software int 0x20 exercises the real IDT handler instead of relying on
random PIT timing to catch register corruption.
"""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import Gen, build_xkernel
qemu=shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip timer IRQ: QEMU unavailable');sys.exit(0)
original=Gen.emit_longmode_tail
sentinel=0x123456789abc

def probe(g,mod):
    original(g,mod)
    a=g.a
    a.fixups=[(p,'irq_probe' if lab=='hs_kernel_main' else lab,k) for p,lab,k in a.fixups]
    a.label('irq_probe')
    for reg in Gen.GPREGS:
        if reg in ('rsp','rbp'):
            continue
        a.mov_ri64(reg,sentinel)
    a.code+=b'\xcd\x20'  # int 0x20, real timer vector
    # Save all registers before comparisons or printing overwrite them.
    for reg in Gen.GPREGS:
        a.push_r(reg)
    for reg in reversed(Gen.GPREGS):
        a.pop_r('rax')
        if reg=='rbp':
            continue
        a.mov_ri64('rcx',sentinel)
        a.cmp_rr('rax','rcx')
        a.setcc_al('e');a.movzx_eax_al()
        a.push_r('rax');a.call('print_int');a.add_ri32('rsp',8)
    a.mov_ri32('rax',10);a.call('x_putc');a.call('k_halt')

with tempfile.TemporaryDirectory() as d:
    d=Path(d);source=d/'probe.hs';source.write_text('print "unused"\n')
    Gen.emit_longmode_tail=probe
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc=build_xkernel(str(source),str(d/'kernel'))
    finally:
        Gen.emit_longmode_tail=original
    if rc:raise SystemExit('FAIL timer probe build')
    p=subprocess.Popen([qemu,'-kernel',str(d/'kernel'),'-serial','file:'+str(d/'serial'),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        import time
        end=time.monotonic()+15
        output=''
        while time.monotonic()<end:
            output=(d/'serial').read_text(errors='replace') if (d/'serial').exists() else ''
            if '\n' in output:break
            time.sleep(.1)
    finally:
        p.terminate();p.wait(timeout=10)
    expected='1'*(len(Gen.GPREGS)-1)+'\n'
    if output!=expected:raise SystemExit('FAIL timer GPR preservation '+repr(output))
print('1/1 deterministic timer IRQ register-preservation gate')
