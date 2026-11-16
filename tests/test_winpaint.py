#!/usr/bin/env python3
"""Ring-3 body fills: policy/heap pins plus every composited RGB pixel.

The app uses production create/fill dispatch. A test-only exit observer
flushes its live scene to a mock RGB32 framebuffer before normal exit
cleanup. An independent Python raster oracle checks all 3072 RGB pixels.
"""
import contextlib, io, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window paint: QEMU unavailable'); sys.exit(0)


def expected():
    pixels = [0] * (64 * 48)
    def rect(x, y, w, h, color):
        for yy in range(max(0, y), min(48, y + h)):
            for xx in range(max(0, x), min(64, x + w)):
                pixels[yy * 64 + xx] = color
    windows = [(4, 4, 28, 28, 0x112233,
                [(-3, -2, 12, 10, 0xff8800), (12, 5, 20, 20, 0x22bb66)]),
               (22, 14, 26, 25, 0x445566,
                [(3, 3, 14, 10, 0x9966dd), (20, 15, 20, 20, 0xffcc44)])]
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
    user = d / 'uupaint'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel/uupaint.holy'), str(user))
    assert not rc, 'uupaint build failed'
    stage = d / 'stage'
    shutil.copytree(ROOT / 'kernel/ramdisk', stage)
    (stage / 'bin').mkdir(exist_ok=True)
    shutil.copy(user, stage / 'bin/uupaint')
    ramdisk = d / 'paint.krfs'
    subprocess.run([sys.executable, str(ROOT / 'scripts/mkramdisk.py'),
                    str(stage), str(ramdisk)], check=True, capture_output=True)
    kern = d / 'kernel'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel/kwinptest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert not rc, 'kwinptest build failed'
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
                if 'winpaint-done\n' in out or p.poll() is not None:
                    break
                time.sleep(.05)
            assert 'winpaint-done\n' in out, (backend, out[-1500:])
            assert '\nfails 0\n' in out, (backend, out[:4500], out[-1500:])
            tokens = out.split()
            fills = [int(tokens[i + 1]) for i, t in enumerate(tokens[:-1]) if t == 'paint-fill']
            assert fills == [0, 0, 0, 0], (backend, fills)
            assert 'paint-bad -22' in ' '.join(tokens), out[-1500:]
            assert 'paint-color -22' in ' '.join(tokens), out[-1500:]
            payload = out.split('paint-pixels-begin\n', 1)[1].split('paint-pixels-end\n', 1)[0]
            got = list(map(int, payload.split()))
            want = expected()
            assert len(got) == len(want) == 3072, (backend, len(got))
            bad = [(i % 64, i // 64, a, b) for i, (a, b) in enumerate(zip(got, want)) if a != b]
            assert not bad, (backend, bad[:20])
            assert out.count('\nok ') + out.startswith('ok ') == 59, out[:4500]
            if os.environ.get('HS_TEST_PAINT_IMAGE'):
                rgb = bytes(channel for color in got for channel in
                            (color >> 16 & 255, color >> 8 & 255, color & 255))
                Path(os.environ['HS_TEST_PAINT_IMAGE']).write_bytes(b'P6\n64 48\n255\n' + rgb)
        finally:
            p.kill()
            p.wait()
    print(f'ok winpaint policy/heap pins + 3072 ring-3 composed pixels ({backend})')
print('2/2 window-paint gates (IR and AST)')
