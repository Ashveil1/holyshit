#!/usr/bin/env python3
"""Focused window keyboard delivery: ring-0 policy pins and real QMP input.

A ring-3 app creates two windows. Each stage clicks a different body and
sends ASCII/navigation keys into its blocking SYS_WIN_KEY_READ. The exact
window/key sequence, cleanup, overflow, no-focus and hover rules are pinned.
"""
import contextlib, io, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window keys: QEMU unavailable'); sys.exit(0)


def build(d, ir_backend):
    uu = d / 'uukeys.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel' / 'uukeys.holy'), str(uu))
    assert rc == 0, 'uukeys build failed'
    shd = d / 'stage'
    shutil.copytree(ROOT / 'kernel' / 'ramdisk', shd)
    os.makedirs(shd / 'bin', exist_ok=True)
    shutil.copy(uu, shd / 'bin' / 'uukeys')
    srd = d / 'wink.krfs'
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'mkramdisk.py'),
                        str(shd), str(srd)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    kern = d / 'kwink.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel' / 'kwinktest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert rc == 0, 'kwinktest build failed'
    return kern, srd


def inject(sock, commands):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(5)
        s.connect(sock)
        stream = s.makefile('rwb', buffering=0)
        json.loads(stream.readline())
        def execute(name, arguments=None):
            request = {'execute': name}
            if arguments is not None:
                request['arguments'] = arguments
            stream.write(json.dumps(request).encode() + b'\r\n')
            while True:
                reply = json.loads(stream.readline())
                assert 'error' not in reply, reply
                if 'return' in reply:
                    return reply['return']
        execute('qmp_capabilities')
        for cmd in commands:
            reply = execute('human-monitor-command', {'command-line': cmd})
            assert not reply, (cmd, reply)
            time.sleep(.2)


def run(kern, srd, d, seconds=45):
    sock = str(d / 'qmp.sock')
    serial = d / 'serial'
    args = [qemu, '-kernel', str(kern), '-serial', 'file:' + str(serial),
            '-display', 'none', '-m', '256M', '-nic', 'none',
            '-initrd', str(srd), '-qmp', 'unix:' + sock + ',server=on,wait=off']
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        stage = 0
        end = time.monotonic() + seconds
        out = ''
        while time.monotonic() < end:
            out = serial.read_text(errors='replace') if serial.exists() else ''
            if 'winkey-done\n' in out:
                break
            if stage == 0 and 'key-stage1' in out:
                # Screen (10,15): body of window 1. Focus then type.
                inject(sock, ['mouse_move 10 -15', 'mouse_button 1',
                              'mouse_button 0', 'sendkey a', 'sendkey up',
                              'sendkey ret'])
                stage = 1
            if stage == 1 and 'key-stage2' in out:
                # Screen (40,15): body of window 2. New focus gets b/Down.
                inject(sock, ['mouse_move 30 0', 'mouse_button 1',
                              'mouse_button 0', 'sendkey b', 'sendkey down'])
                stage = 2
            if p.poll() is not None:
                break
            time.sleep(.05)
        return out
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


for ir_backend in (True, False):
    backend = 'ir' if ir_backend else 'ast'
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        kern, srd = build(d, ir_backend)
        out = run(kern, srd, d)
        assert 'winkey-done\n' in out, (backend, out[-2500:])
        assert '\nfails 0\n' in out, (backend, out[-2500:])
        toks = out.split()
        got = [tuple(map(int, toks[i + 1:i + 3])) for i in range(len(toks) - 2)
               if toks[i] == 'wkey']
        want = [(1, 97), (1, 128), (1, 10), (2, 98), (2, 129)]
        assert got == want, (backend, got, want, out[-2500:])
        assert 'uukeys counts 3 2' in ' '.join(toks), out[-2500:]
        assert out.count('\nok ') + out.startswith('ok ') >= 46, out
    print(f'ok winkeys focus/queue/cleanup pins + ring-3 keyboard delivery ({backend})')
print('2/2 focused-window keyboard gates (IR and AST)')
