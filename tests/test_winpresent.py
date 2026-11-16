#!/usr/bin/env python3
"""Explicit present and automatic close/exit repaint on kernel-bound targets.

Checks padded RGB24 guards and three complete RGB32 snapshots after real
ring-3 present, close, and normal exit. Observer only reads target bytes.
"""
import contextlib, io, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window paint: QEMU unavailable'); sys.exit(0)


def expected(stage):
    pixels = [0x16324f] * (64 * 48)
    def rect(x, y, w, h, color):
        for yy in range(max(0, y), min(48, y + h)):
            for xx in range(max(0, x), min(64, x + w)):
                pixels[yy * 64 + xx] = color
    windows = [(4, 4, 28, 28, 0x112233,
                [(-3, -2, 12, 10, 0xff8800), (12, 5, 20, 20, 0x22bb66)]),
               (22, 14, 26, 25, 0x445566,
                [(3, 3, 14, 10, 0x9966dd), (20, 15, 20, 20, 0xffcc44)])]
    windows = windows if stage == 1 else windows[:1] if stage == 2 else []
    for x, y, w, h, color, fills in windows:
        rect(x, y, w, 6, 0x555a66)
        rect(x, y + 6, w, h - 6, color)
        for rx, ry, rw, rh, color in fills:
            for yy in range(max(0, ry), min(h - 6, ry + rh)):
                for xx in range(max(0, rx), min(w, rx + rw)):
                    pixels[(y + 6 + yy) * 64 + x + xx] = color
    # Literal cursor bitmap, independent of kernel masks/shift helpers.
    cursor = ['XX.....', 'X.X....', 'X..X...', 'X...X..',
              'X....X.', 'X.XXX..', 'XX.....']
    white = ['.......', '.X.....', '.XX....', '.XXX...',
             '.XXXX..', '.X.....', '.......']
    for yy in range(7):
        for xx in range(7):
            if cursor[yy][xx] == 'X':
                pixels[(40 + yy) * 64 + 55 + xx] = 0
            if white[yy][xx] == 'X':
                pixels[(40 + yy) * 64 + 55 + xx] = 0xffffff
    return pixels


def build(d, ir_backend):
    user = d / 'uupresent'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel/uupresent.holy'), str(user))
    assert not rc, 'uupresent build failed'
    stage = d / 'stage'
    shutil.copytree(ROOT / 'kernel/ramdisk', stage)
    (stage / 'bin').mkdir(exist_ok=True)
    shutil.copy(user, stage / 'bin/uupresent')
    ramdisk = d / 'present.krfs'
    subprocess.run([sys.executable, str(ROOT / 'scripts/mkramdisk.py'),
                    str(stage), str(ramdisk)], check=True, capture_output=True)
    kern = d / 'kernel'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel/kwinprtest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert not rc, 'kwinprtest build failed'
    return kern, ramdisk


for ir_backend in (True, False):
    backend = 'ir' if ir_backend else 'ast'
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        kern, ramdisk = build(d, ir_backend)
        serial = d / 'serial'
        p = subprocess.Popen([qemu, '-kernel', str(kern), '-initrd', str(ramdisk),
                              '-serial', 'file:' + str(serial), '-m', '256M',
                              '-display', 'none', '-nic', 'none'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 45
            out = ''
            while time.monotonic() < deadline:
                out = serial.read_text(errors='replace') if serial.exists() else ''
                if 'winpresent-done\n' in out or p.poll() is not None:
                    break
                time.sleep(.05)
            assert 'winpresent-done\n' in out, (backend, out[-1500:])
            assert '\nfails 0\n' in out, (backend, out[:4500], out[-1500:])
            tokens = out.split()
            assert 'present-result 3072' in ' '.join(tokens), out[-1500:]
            assert 'close-result 0' in ' '.join(tokens), out[-1500:]
            parts = out.split('present-pixels-begin ')[1:]
            assert len(parts) == 3, (backend, len(parts))
            for stage, part in enumerate(parts, 1):
                label, payload = part.split('\n', 1)
                assert int(label) == stage
                got = list(map(int, payload.split('present-pixels-end', 1)[0].split()))
                want = expected(stage)
                assert len(got) == len(want) == 3072, (backend, stage, len(got))
                bad = [(i % 64, i // 64, a, b) for i, (a, b) in enumerate(zip(got, want)) if a != b]
                assert not bad, (backend, stage, bad[:20])
                if os.environ.get('HS_TEST_PRESENT_IMAGES'):
                    rgb = bytes(channel for color in got for channel in
                                (color >> 16 & 255, color >> 8 & 255, color & 255))
                    Path(os.environ['HS_TEST_PRESENT_IMAGES'] + str(stage) + '.ppm').write_bytes(b'P6\n64 48\n255\n' + rgb)
            assert out.count('\nok ') + out.startswith('ok ') == 46, out[-1500:]
        finally:
            p.kill()
            p.wait()
    print(f'ok winpresent RGB24/32 policy pins + 9216 present/close/exit pixels ({backend})')
print('2/2 window-present gates (IR and AST)')
