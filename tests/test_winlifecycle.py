#!/usr/bin/env python3
"""Window lifecycle syscalls: ring-0 SYS_WIN_CREATE/SYS_WIN_CLOSE pins plus
a ring-3 app that creates its own compositor window and drains real
QEMU-injected PS/2 traffic routed to it, over QMP.

uuapp.elf runs in ring 3 on the staged ramdisk: it creates the window,
announces the id, then blocks in SYS_WIN_EVENT_READ (the kernel holds a
ring-0 interrupt window open and pumps the FIFO during the wait). On exit
the kernel must auto-close the app's window (kwinetest.holy pins that)."""
import contextlib, io, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window lifecycle: QEMU unavailable'); sys.exit(0)

# QMP deltas are screen-negated in y. The app creates its window at
# (30,5,30,25): motion to (35,20) lands in the body, then press+release.
EVENTS = [((35, -20), None), (None, 1), (None, 0)]
EXPECTED = [(0, 5, 15), (1, 5, 15), (0, 5, 15)]


def build(d, ir_backend):
    uu = d / 'uuapp.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel' / 'uuapp.holy'), str(uu))
    assert rc == 0, 'uuapp build failed'
    shd = d / 'stage'
    shutil.copytree(ROOT / 'kernel' / 'ramdisk', shd)
    os.makedirs(shd / 'bin', exist_ok=True)
    shutil.copy(uu, shd / 'bin' / 'uuapp')
    srd = d / 'winc.krfs'
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'mkramdisk.py'),
                        str(shd), str(srd)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    kern = d / 'kwinc.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel' / 'kwinctest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert rc == 0, 'kwinctest build failed'
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
        ready = injected = False
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            out = serial.read_text(errors='replace') if serial.exists() else ''
            if not ready and 'winc-ready\n' in out:
                ready = True
            # the app announces its window id as the 'wid' token, then
            # blocks in the read; inject straight into that wait
            if ready and not injected and 'wid' in out.split():
                inject(sock)
                injected = True
            if injected and 'winc-done\n' in out:
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
    backend = 'ir' if ir_backend else 'ast'
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        kern, srd = build(d, ir_backend)
        out = run(kern, srd, d)
        assert 'winc-done\n' in out, f'no winc-done ({backend}): {out[-1200:]}'
        assert '\nfails 0\n' in out, f'ring-0 pins failed ({backend}): {out[-1200:]}'
        # ring3 print emits each argument as its own write, so the serial
        # stream is a token soup: regroup into 4-token (wev b rx ry) events.
        toks = out.split()
        got = [' '.join(toks[i:i + 4]) for i in range(len(toks) - 3)
               if toks[i] == 'wev']
        want = ['wev %d %d %d' % ev for ev in EXPECTED]
        assert got == want, (backend, got, want, out[-1200:])
        assert 'uuapp events 3' in ' '.join(out.split()), out[-1200:]
        assert out.count('\nok ') + out.startswith('ok ') >= 29, out
    print(f'ok winlifecycle create/route/close pins + ring-3 app delivery ({backend})')

print('2/2 window-lifecycle gates: create/close pins + ring-3 app delivery (IR and AST)')
