#!/usr/bin/env python3
"""Ring-3 byte text, hostile span rejection, body clipping and full pixel oracle."""
import contextlib, io, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window paint: QEMU unavailable'); sys.exit(0)


def expected():
    pixels = [0x16324f] * (64 * 48)
    def rect(x, y, w, h, color):
        for yy in range(max(0, y), min(48, y + h)):
            for xx in range(max(0, x), min(64, x + w)):
                pixels[yy * 64 + xx] = color
    def text(x, y, value, color):
        forms = {'H': [17,17,17,31,17,17,17], 'I': [31,4,4,4,4,4,31],
                 'A': [14,17,17,31,17,17,17], '?': [14,17,1,2,4,0,4], ' ': [0]*7}
        left = x
        for ch in value:
            if ch == '\n':
                x = left; y += 8; continue
            for row, bits in enumerate(forms.get(ch.upper(), forms['?'])):
                for col in range(5):
                    if bits & (1 << (4-col)) and 0 <= x+col < 38 and 0 <= y+row < 29:
                        pixels[(10+y+row)*64+4+x+col] = color
            x += 6
    rect(4, 4, 38, 6, 0x555a66)
    rect(4, 10, 38, 29, 0x112233)
    text(2, 2, 'Hi A\nI?', 0xffffff)
    text(-2, 20, 'A@', 0xff8800)
    text(32, 25, 'HI', 0x22bb66)
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
    user = d / 'uutext'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel/uutext.holy'), str(user))
    assert not rc, 'uutext build failed'
    stage = d / 'stage'
    shutil.copytree(ROOT / 'kernel/ramdisk', stage)
    (stage / 'bin').mkdir(exist_ok=True)
    shutil.copy(user, stage / 'bin/uutext')
    ramdisk = d / 'present.krfs'
    subprocess.run([sys.executable, str(ROOT / 'scripts/mkramdisk.py'),
                    str(stage), str(ramdisk)], check=True, capture_output=True)
    kern = d / 'kernel'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel/kwinttest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert not rc, 'kwinttest build failed'
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
                if 'wintext-done\n' in out or p.poll() is not None:
                    break
                time.sleep(.05)
            assert 'wintext-done\n' in out, (backend, out[-1500:])
            assert '\nfails 0\n' in out, (backend, out[:4500], out[-1500:])
            tokens = out.split()
            for marker, value in [('text-badptr', -14), ('text-unmapped', -14),
                                  ('text-badlen', -22), ('text-color', -22), ('text-present', 3072)]:
                assert f'{marker} {value}' in ' '.join(tokens), (backend, marker, out[-1500:])
            results = [int(tokens[i+1]) for i,t in enumerate(tokens[:-1]) if t == 'text-result']
            assert results == [0,0,0], results
            got = list(map(int, out.split('text-pixels-begin\n',1)[1].split('text-pixels-end',1)[0].split()))
            want = expected()
            assert len(got) == 3072, (backend, len(got))
            bad = [(i%64,i//64,a,b) for i,(a,b) in enumerate(zip(got,want)) if a != b]
            assert not bad, (backend,bad[:20])
            assert out.count('\nok ') + out.startswith('ok ') == 38, out[:3000]
            if os.environ.get('HS_TEST_TEXT_IMAGE'):
                rgb = bytes(ch for color in got for ch in (color>>16&255,color>>8&255,color&255))
                Path(os.environ['HS_TEST_TEXT_IMAGE']).write_bytes(b'P6\n64 48\n255\n'+rgb)
        finally:
            p.kill()
            p.wait()
    print(f'ok wintext span/permission/cleanup pins + 3072 text pixels ({backend})')
print('2/2 window-text gates (IR and AST)')
