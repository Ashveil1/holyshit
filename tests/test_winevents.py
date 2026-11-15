#!/usr/bin/env python3
"""Window event routing: ring-0 routing pins plus ring-3 SYS_WIN_EVENT_READ
delivery of compositor-routed, window-relative events from real
QEMU-injected PS/2 mouse moves/buttons over QMP.

uuwin.elf runs in ring 3 on the staged ramdisk and must receive exactly the
non-chrome injected sequence, window-relative, through the syscall surface;
the ring-0 harness (kwinetest.holy) pins the routing policy (title/desktop
chrome is not routed, drags are not routed) and the queue contract."""
import contextlib, io, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window events: QEMU unavailable'); sys.exit(0)

# QMP deltas are screen-negated in y (+dy is up); cursor targets below are
# in screen coords. Window starts at (20,10,40,30), title rows 10..15.
EVENTS = [((25, -15), None), ((10, 4), None), (None, 1), ((5, -2), None),
          (None, 0), ((10, -20), None), (None, 1), (None, 0)]
# routed (buttons, rx, ry): motion into the body, motion over the title,
# post-drag motion, body press, release. The title press and the drag
# itself are chrome and must NOT arrive.
EXPECTED = [(0, 5, 5), (0, 15, 1), (0, 26, 21), (1, 26, 21), (0, 26, 21)]


def build(d, ir_backend):
    uu = d / 'uuwin.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel' / 'uuwin.holy'), str(uu))
    assert rc == 0, 'uuwin build failed'
    shd = d / 'stage'
    shutil.copytree(ROOT / 'kernel' / 'ramdisk', shd)
    os.makedirs(shd / 'bin', exist_ok=True)
    shutil.copy(uu, shd / 'bin' / 'uuwin')
    srd = d / 'win.krfs'
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'mkramdisk.py'),
                        str(shd), str(srd)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    kern = d / 'kwine.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel' / 'kwinetest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert rc == 0, 'kwinetest build failed'
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
            if not injected and 'winroute-ready\n' in out:
                inject(sock)
                injected = True
            if injected and 'winroute-done\n' in out:
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
        assert 'winroute-done\n' in out, f'no winroute-done ({backend}): {out[-1200:]}'
        assert '\nfails 0\n' in out, f'ring-0 pins failed ({backend}): {out[-1200:]}'
        # ring3 print emits each argument as its own write, so the serial
        # stream is a token soup: regroup into 4-token (wev b rx ry) events.
        toks = out.split()
        got = [' '.join(toks[i:i + 4]) for i in range(len(toks) - 3)
               if toks[i] == 'wev']
        want = ['wev %d %d %d' % ev for ev in EXPECTED]
        assert got == want, (backend, got, want, out[-1200:])
        assert 'uuwin events 5' in ' '.join(out.split()), out[-1200:]
        assert out.count('\nok ') + out.startswith('ok ') >= 30, out
    print(f'ok winevents routing pins + ring-3 injected delivery ({backend})')

print('2/2 window-event routing gates: routing pins + ring-3 injected delivery (IR and AST)')
