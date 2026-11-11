#!/usr/bin/env python3
"""PS/2 mouse: deterministic packet decode + FIFO probe, and real IRQ12
delivery injected through QEMU's monitor (mouse_move/mouse_button)."""
import contextlib, io, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import Gen, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip mouse packet: QEMU unavailable'); sys.exit(0)
original = Gen.emit_longmode_tail
expected = []


def number(a):
    a.push_r('rax'); a.call('print_int'); a.add_ri32('rsp', 8)
    a.mov_ri32('rax', 10); a.call('x_putc')


def build(d, probe, ir_backend):
    source = d / 'mouse.holy'
    source.write_text('print "unused"\n')
    Gen.emit_longmode_tail = probe
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = build_xkernel(str(source), str(d / 'kernel'), ir_backend=ir_backend)
    finally:
        Gen.emit_longmode_tail = original
    assert not rc, 'mouse kernel build failed'
    return d / 'kernel'


def run_serial(kernel, d, seconds, ready=None, inject=None):
    sock = str(d / 'qmp.sock')
    args = [qemu, '-kernel', str(kernel), '-serial', 'file:' + str(d / 'serial'),
            '-display', 'none', '-monitor', 'none', '-nic', 'none']
    if inject:
        args += ['-qmp', 'unix:' + sock + ',server=on,wait=off']
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        end = time.monotonic() + seconds
        out = ''
        injected = False
        while time.monotonic() < end:
            out = (d / 'serial').read_text(errors='replace') if (d / 'serial').exists() else ''
            if inject is None:
                if 'mouse-done\n' in out:
                    break
            else:
                if not injected and ready in out:
                    inject(sock)
                    injected = True
                if injected and out.count('\n') >= ready.count('\n') + len(inject.expected):
                    break
            time.sleep(.05)
    finally:
        p.terminate(); p.wait(timeout=10)
    return out


# --- part 1: deterministic decode/FIFO probe (no real IRQs) ---
def decode_probe(g, mod):
    original(g, mod); a = g.a
    a.fixups = [(p, 'mouse_probe' if lab == 'hs_kernel_main' else lab, k)
                for p, lab, k in a.fixups]
    a.label('mouse_probe'); a.cli()

    def byte(n):
        a.mov_ri32('rax', n); a.call('ms_byte')

    def put(n):
        a.mov_ri32('rax', n); a.call('ms_enqueue')

    def get(n):
        a.call('ms_dequeue'); number(a); expected.append(str(n) + '\n')

    # Complete packets decode to status | dx<<8 | dy<<16.
    byte(0x08); byte(1); byte(2); get(0x08 | (1 << 8) | (2 << 16))
    byte(0x1B); byte(0xF6); byte(0x05); get(0x1B | (0xF6 << 8) | (0x05 << 16))
    # Partial packet produces no event until the third byte lands.
    byte(0x09); byte(3)
    get(0)
    byte(4); get(0x09 | (3 << 8) | (4 << 16))
    # Resync: bytes without the leader bit are dropped; the stream realigns.
    byte(1); byte(2)
    byte(0x0B); byte(5); byte(6); get(0x0B | (5 << 8) | (6 << 16))
    # Burst/wrap/overflow: 65 raw events into a 63-usable FIFO, drop newest.
    for n in range(1, 66):
        put(n)
    for n in range(1, 64):
        get(n)
    get(0)
    a.lea_rip('rax', 'msdrops_'); a.mov_rm('rax', 'rax', 0)
    number(a); expected.append('2\n')
    # Wrap: drain, refill, order preserved.
    for n in range(70, 100):
        put(n)
    for n in range(70, 100):
        get(n)
    get(0)
    # Exact caller IF for empty and nonempty dequeue, both disabled/enabled.
    for enabled, nonempty in [(False, False), (False, True), (True, False), (True, True)]:
        a.cli()
        if nonempty:
            put(0x2A)
        if enabled:
            a.sti()
        a.call('ms_dequeue')
        a.code += bytes([0x9c]); a.pop_r('rax'); a.and_ri32('rax', 512)
        a.cli(); number(a); expected.append(('512' if enabled else '0') + '\n')
    get(0)
    for ch in 'mouse-done\n':
        a.mov_ri32('rax', ord(ch)); a.call('x_putc')
    expected.append('mouse-done\n')
    a.label('mshalt'); a.hlt(); a.jmp('mshalt')


for ir_backend in (True, False):
    expected = []
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        kernel = build(d, decode_probe, ir_backend)
        out = run_serial(kernel, d, 20)
        want = ''.join(expected)
        assert out == want, (out, want)

# --- part 2: real IRQ12 delivery via QEMU input injection ---
def irq_probe(g, mod):
    original(g, mod); a = g.a
    a.fixups = [(p, 'mouse_irq_main' if lab == 'hs_kernel_main' else lab, k)
                for p, lab, k in a.fixups]
    a.label('mouse_irq_main')  # IF already set by emit_longmode_tail
    for ch in 'mouse-ready\n':
        a.mov_ri32('rax', ord(ch)); a.call('x_putc')
    a.label('mspoll')
    a.call('ms_dequeue')
    a.test_rr('rax', 'rax')
    a.jcc('e', 'mspoll')
    number(a)
    a.jmp('mspoll')


def qmp_inject(sock):
    events = [((10, 5), None), ((-7, -3), None), (None, 1), ((2, 0), None), (None, 0)]
    buttons = 0
    qmp_inject.expected = []
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(5)
    s.connect(sock)
    s.recv(4096)
    s.sendall(b'{"execute":"qmp_capabilities"}\r\n')
    s.recv(4096)

    def hmp(cmd):
        s.sendall(json.dumps({'execute': 'human-monitor-command',
                              'arguments': {'command-line': cmd}}).encode() + b'\r\n')
        s.recv(4096)

    for move, button in events:
        if move is not None:
            dx, dy = move
            hmp('mouse_move %d %d' % (dx, dy))
        else:
            buttons = button
            hmp('mouse_button %d' % button)
            dx = dy = 0
        # PS/2 dy is screen-negated (positive screen-down = negative dy).
        pdy = -dy
        status = 0x08 | buttons
        if dx < 0:
            status |= 0x10
        if pdy < 0:
            status |= 0x20
        qmp_inject.expected.append(str(status | (dx & 0xFF) << 8 | (pdy & 0xFF) << 16) + '\n')
        time.sleep(.15)
    s.close()


for ir_backend in (True, False):
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        kernel = build(d, irq_probe, ir_backend)
        out = run_serial(kernel, d, 30, ready='mouse-ready\n', inject=qmp_inject)
        got = out.split('mouse-ready\n', 1)[-1]
        want = ''.join(qmp_inject.expected)
        assert got == want, (got, want)

print('4/4 mouse packet decode, resync, burst/wrap/drop-newest, IF gates + real IRQ12 injection (IR and AST)')
