#!/usr/bin/env python3
"""Ring-3 1x..4x text, legacy compatibility, clipping and full pixel oracle."""
import contextlib, io, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip window paint: QEMU unavailable'); sys.exit(0)


def expected():
    pixels = [0x16324f] * (64 * 64)
    def rect(x, y, w, h, color):
        for yy in range(max(0, y), min(64, y + h)):
            for xx in range(max(0, x), min(64, x + w)):
                pixels[yy * 64 + xx] = color
    def text(x, y, value, color, scale):
        forms = {'H':[17,17,17,31,17,17,17], 'I':[31,4,4,4,4,4,31],
                 'A':[14,17,17,31,17,17,17], '?':[14,17,1,2,4,0,4]}
        left = x
        for ch in value:
            if ch == '\n':
                x = left; y += 8*scale; continue
            for row,bits in enumerate(forms.get(ch.upper(),forms['?'])):
                for col in range(5):
                    if bits & (1<<(4-col)):
                        for dy in range(scale):
                            for dx in range(scale):
                                px=x+col*scale+dx; py=y+row*scale+dy
                                if 0<=px<58 and 0<=py<54:
                                    pixels[(8+py)*64+3+px]=color
            x += 6*scale
    rect(3,2,58,6,0x555a66);rect(3,8,58,54,0x112233)
    for args in [(0,0,'h',0xffffff,1),(8,0,'A',0xff8800,2),
                 (24,0,'I',0x22bb66,3),(40,0,'@',0x4466ff,4),
                 (-3,30,'A\ni',0xffffff,2),(48,42,'HI',0xff8800,3),
                 (20,30,'Hi',0x22bb66,1)]:text(*args)
    cursor=['XX.....','X.X....','X..X...','X...X..','X....X.','X.XXX..','XX.....']
    white=['.......','.X.....','.XX....','.XXX...','.XXXX..','.X.....','.......']
    for yy in range(7):
        for xx in range(7):
            if cursor[yy][xx]=='X':pixels[(56+yy)*64+55+xx]=0
            if white[yy][xx]=='X':pixels[(56+yy)*64+55+xx]=0xffffff
    return pixels


def build(d, ir_backend):
    user = d / 'uuscale'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_x64(str(ROOT / 'kernel/uuscale.holy'), str(user))
    assert not rc, 'uuscale build failed'
    stage = d / 'stage'
    shutil.copytree(ROOT / 'kernel/ramdisk', stage)
    (stage / 'bin').mkdir(exist_ok=True)
    shutil.copy(user, stage / 'bin/uuscale')
    ramdisk = d / 'present.krfs'
    subprocess.run([sys.executable, str(ROOT / 'scripts/mkramdisk.py'),
                    str(stage), str(ramdisk)], check=True, capture_output=True)
    kern = d / 'kernel'
    with contextlib.redirect_stdout(io.StringIO()):
        rc = build_xkernel(str(ROOT / 'kernel/kwinscaletest.holy'), str(kern),
                           ir_backend=ir_backend)
    assert not rc, 'kwinscaletest build failed'
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
                if 'winscale-done\n' in out or p.poll() is not None:
                    break
                time.sleep(.05)
            assert 'winscale-done\n' in out, (backend, out[-1500:])
            assert '\nfails 0\n' in out, (backend, out[:4500], out[-1500:])
            tokens = out.split()
            for marker, value in [('scale-badptr', -22), ('scale-unmapped', -14),
                                  ('scale-badlen', -22), ('scale-style', -22), ('scale-legacy',0), ('scale-present', 4096)]:
                assert f'{marker} {value}' in ' '.join(tokens), (backend, marker, out[-1500:])
            results = [int(tokens[i+1]) for i,t in enumerate(tokens[:-1]) if t == 'scale-result']
            assert results == [0,0,0,0,0,0], results
            got = list(map(int, out.split('scale-pixels-begin\n',1)[1].split('scale-pixels-end',1)[0].split()))
            want = expected()
            assert len(got) == 4096, (backend, len(got))
            bad = [(i%64,i//64,a,b) for i,(a,b) in enumerate(zip(got,want)) if a != b]
            assert not bad, (backend,bad[:20])
            assert out.count('\nok ') + out.startswith('ok ') == 54, out[:3000]
            if os.environ.get('HS_TEST_SCALE_IMAGE'):
                rgb = bytes(ch for color in got for ch in (color>>16&255,color>>8&255,color&255))
                Path(os.environ['HS_TEST_SCALE_IMAGE']).write_bytes(b'P6\n64 64\n255\n'+rgb)
        finally:
            p.kill()
            p.wait()
    print(f'ok winscale scale/span/permission/cleanup pins + 4096 text pixels ({backend})')
print('2/2 window-scaled-text gates (IR and AST)')
