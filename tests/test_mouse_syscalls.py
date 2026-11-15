#!/usr/bin/env python3
"""Pointer-event syscalls: ring-0 decode pins plus ring-3 SYS_MOUSE_READ
delivery of real QEMU-injected PS/2 mouse moves/buttons over QMP.

uumouse.elf runs in ring 3 on the staged ramdisk and must decode exactly the
injected sequence through the syscall surface; the ring-0 harness
(kmousetest.holy) pins kinput.decode and the empty-FIFO contract."""
import contextlib, io, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip mouse syscalls: QEMU unavailable'); sys.exit(0)

EVENTS = [((10, 5), None), ((-7, -3), None), (None, 1), ((2, 0), None), (None, 0)]
# decoded (buttons, dx, dy) the guest must print, PS/2 dy screen-negated
EXPECTED = [(0, 10, -5), (0, -7, 3), (1, 0, 0), (1, 2, 0), (0, 0, 0)]


def build(d, ir_backend):
    uu = d / 'uumouse.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel' / 'uumouse.holy'), str(uu))
    assert rc == 0, 'uumouse build failed'
    shd = d / 'stage'
    shutil.copytree(ROOT / 'kernel' / 'ramdisk', shd)
    os.makedirs(shd / 'bin', exist_ok=True)
    shutil.copy(uu, shd / 'bin' / 'uumouse')
    srd = d / 'mouse.krfs'
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'mkramdisk.py'),
                        str(shd), str(srd)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    kern = d / 'kmouse.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel' / 'kmousetest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert rc == 0, 'kmousetest build failed'
    return kern, srd


def inject(sock):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(5)
    s.connect(sock)
    s.recv(4096)
    s.sendall(b'{"execute":"qmp_capabilities"}\r\n')
    s.recv(4096)
    for move, button in EVENTS:
        if move is not None:
            cmd = 'mouse_move %d %d' % move
        else:
            cmd = 'mouse_button %d' % button
        s.sendall(json.dumps({'execute': 'human-monitor-command',
                              'arguments': {'command-line': cmd}}).encode() + b'\r\n')
        s.recv(4096)
        time.sleep(.15)
    s.close()


def run(kern, srd, d, seconds=90):
    sock = str(d / 'qmp.sock')
    serial = d / 'serial'
    args = [qemu, '-kernel', str(kern), '-serial', 'file:' + str(serial),
            '-display', 'none', '-m', '256M', '-nic', 'none',
            '-initrd', str(srd), '-qmp', 'unix:' + sock + ',server=on,wait=off']
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        out = ''
        injected = False
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            out = serial.read_text(errors='replace') if serial.exists() else ''
            if not injected and 'mouse-sys-ready\n' in out:
                inject(sock)
                injected = True
            if injected and 'mousesys-done\n' in out:
                break
            time.sleep(.1)
        return out
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


for ir_backend in (True, False):
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        kern, srd = build(d, ir_backend)
        out = run(kern, srd, d)
        assert 'mousesys-done\n' in out, out[-1200:]
        assert '\nfails 0\n' in out, out[-1200:]
        # ring3 print emits each argument as its own write, so the serial
        # stream is a token soup: regroup into 4-token (mse b dx dy) events.
        toks = out.split()
        got = [' '.join(toks[i:i + 4]) for i in range(len(toks) - 3)
               if toks[i] == 'mse']
        want = ['mse %d %d %d' % ev for ev in EXPECTED]
        assert got == want, (got, want, out[-1200:])
        assert 'uumouse events 5' in ' '.join(out.split()), out[-1200:]
        assert out.count('\nok ') + out.startswith('ok ') >= 23, out

print('2/2 pointer-event syscall gates: decode pins + ring-3 injected delivery (IR and AST)')
