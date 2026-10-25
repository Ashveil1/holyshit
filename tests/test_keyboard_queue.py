#!/usr/bin/env python3
"""Real generated FIFO helpers in QEMU: burst, wrap, overflow, IF, readkey.
PS/2 translation/IRQ delivery is separately exercised by kernel/console tests.
"""
import contextlib,io,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import Gen,build_xkernel
qemu=shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip keyboard FIFO: QEMU unavailable');sys.exit(0)
original=Gen.emit_longmode_tail
expected=[]
def probe(g,mod):
    original(g,mod);a=g.a
    a.fixups=[(p,'queue_probe' if lab=='hs_kernel_main' else lab,k) for p,lab,k in a.fixups]
    a.label('queue_probe');a.cli()
    def number():
        a.push_r('rax');a.call('print_int');a.add_ri32('rsp',8)
        a.mov_ri32('rax',10);a.call('x_putc')
    def put(n):
        a.mov_ri32('rax',n);a.call('kbd_enqueue')
    def get(n):
        a.call('kbd_dequeue');number();expected.append(str(n)+'\n')
    get(0)
    for n in range(1,66):put(n)
    for n in range(1,32):get(n)
    for n in range(90,121):put(n)
    for n in list(range(32,64))+list(range(90,121)):get(n)
    get(0)
    a.lea_rip('rax','keydrops_');a.mov_rm('rax','rax',0);number();expected.append('2\n')
    # Exact caller IF for empty and nonempty dequeue, both disabled/enabled.
    for enabled,nonempty in [(False,False),(False,True),(True,False),(True,True)]:
        a.cli()
        if nonempty:put(65)
        if enabled:a.sti()
        a.call('kbd_dequeue')
        a.code+=bytes([0x9c]);a.pop_r('rax');a.and_ri32('rax',512)
        a.cli();number();expected.append(('512' if enabled else '0')+'\n')
    # Same translation helper IRQ1 uses: extended make, break, unknown,
    # repeated prefix and ordinary release handling. Separate FIFO isolation.
    def scan(n):
        a.mov_ri32('rax',n);a.call('kbd_scancode')
    for n in [0xE0,0x48,0xE0,0xC8,0xE0,0x50,0xE0,0xD0,
              0xE0,0x1C,0xE0,0xE0,0x48,0x1E,0x9E]:scan(n)
    for n in [1,2,1,0]:
        a.call('nav_dequeue');number();expected.append(str(n)+'\n')
    get(97);get(0)
    # Navigation overflow drops newest, retaining63events independently.
    for n in range(65):
        a.mov_ri32('rax',1);a.call('nav_enqueue')
    for n in range(63):
        a.call('nav_dequeue');number();expected.append('1\n')
    a.call('nav_dequeue');number();expected.append('0\n')
    a.lea_rip('rax','navdrops_');a.mov_rm('rax','rax',0);number();expected.append('2\n')
    for enabled,nonempty in [(False,False),(False,True),(True,False),(True,True)]:
        a.cli()
        if nonempty:
            a.mov_ri32("rax",2);a.call("nav_enqueue")
        if enabled:a.sti()
        a.call('nav_dequeue')
        a.code+=bytes([0x9c]);a.pop_r('rax');a.and_ri32('rax',512)
        a.cli();number();expected.append(('512' if enabled else '0')+'\n')
    if code_mode:
        for n in range(1,64):put(n)
    else:
        put(97);put(98)
    a.jmp('hs_kernel_main')
for ir_backend,code_mode in [(True,False),(False,False),(True,True),(False,True)]:
    expected=[]
    with tempfile.TemporaryDirectory() as temp:
        d=Path(temp);source=d/'queue.holy'
        source.write_text('def mark():\n  unsafe:\n    return as_int(alloc(1))\nbefore = mark()\ni = 1\nvalid = true\nwhile i < 64:\n  if readkey_code() != i:\n    valid = false\n  i = i + 1\nempty = readkey_code()\nafter = mark()\nprint after - before\nprint valid, empty\nprint "queue-done"\n')
        if not code_mode:
            source.write_text('print readkey()\nprint readkey()\nprint readkey()\nprint "queue-done"\n')
        Gen.emit_longmode_tail=probe
        try:
            with contextlib.redirect_stdout(io.StringIO()):rc=build_xkernel(str(source),str(d/'kernel'),ir_backend=ir_backend)
        finally:Gen.emit_longmode_tail=original
        assert not rc,'queue kernel build failed'
        p=subprocess.Popen([qemu,'-kernel',str(d/'kernel'),'-serial','file:'+str(d/'serial'),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            end=time.monotonic()+20;out=''
            while time.monotonic()<end:
                out=(d/'serial').read_text(errors='replace') if (d/'serial').exists() else ''
                if 'queue-done\n'in out:break
                time.sleep(.1)
        finally:p.terminate();p.wait(timeout=10)
        want=''.join(expected)+('16\ntrue null\nqueue-done\n'if code_mode else'a\nb\nnull\nqueue-done\n')
        assert out==want,(out,want)
print('4/4 deterministic FIFO burst/wrap/drop-newest/IF/readkey+code allocation gates (IR and AST)')
