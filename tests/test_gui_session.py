#!/usr/bin/env python3
"""Actual GRUB module2 -> ring3 scratchpad: input, glyphs, focus, drag, exit.

Both Python kernel backends boot. IR kernel and user images must also match
native hs compilation, including all linked bytes. The packaged ISO script
is exercised separately by the IR case. No real disk or network is attached.
"""
import contextlib, io, json, os, re, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu or not shutil.which('grub-mkrescue') or not shutil.which('xorriso'):
    if os.environ.get('HS_REQUIRE_GUI') == '1':
        raise SystemExit('FAIL required GUI session: QEMU/GRUB/xorriso unavailable')
    print('skip GUI session: optional QEMU/GRUB/xorriso unavailable'); sys.exit(0)
env = dict(os.environ, HSROOT=str(ROOT), HSPATH=':'.join(map(str,
    [ROOT, ROOT/'kernel', ROOT/'selfhost', ROOT/'selfhost/be'])))
EVIDENCE = os.environ.get('HS_GUI_EVIDENCE')
BG = bytes.fromhex('16324f'); INK = bytes.fromhex('16324f')
WHITE = b'\xff\xff\xff'; CARET = bytes.fromhex('386fa4')
FORMS = {'H':[17,17,17,31,17,17,17], 'I':[31,4,4,4,4,4,31],
         'A':[14,17,17,31,17,17,17]}


def boot(d, ir_backend, desktop=False):
    tree = d/'tree'; (tree/'boot/grub').mkdir(parents=True)
    user = d/'uunote'; kernel = tree/'boot/kernel.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        assert build_x64(str(ROOT/('kernel/uudesk.holy' if desktop else 'kernel/uunote.holy')), str(user)) == 0
        assert build_xkernel(str(ROOT/'kernel/kgui.holy'), str(kernel), ir_backend=ir_backend) == 0
    if ir_backend:
        # Test the actual user-facing packaging entry point, not a lookalike.
        subprocess.run([str(ROOT/'scripts/build-gui-iso.sh'), str(d/'gui.iso')]+(['desktop'] if desktop else []),
                       env=env, check=True, capture_output=True, timeout=300)
        before = (d/'gui.iso').read_bytes()
        again = subprocess.run([str(ROOT/'scripts/build-gui-iso.sh'), str(d/'gui.iso')],
                               env=env, capture_output=True, timeout=10)
        assert again.returncode != 0 and (d/'gui.iso').read_bytes() == before, 'ISO output overwritten'
        # Extract the shipped files to prove script output equals reviewed builds.
        for path, expected in [('kernel.elf', kernel), ('ramdisk.krfs', None)]:
            subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(d/'gui.iso'),
                            '-extract', '/boot/'+path, str(d/path)],
                           env=env, check=True, capture_output=True, timeout=30)
            if expected: assert (d/path).read_bytes() == expected.read_bytes(), 'native kernel differs'
        import struct
        data = (d/'ramdisk.krfs').read_bytes(); assert data[:4] == b'KRFS'
        off = 8; got_user = None
        for _ in range(struct.unpack_from('<I', data, 4)[0]):
            kind, n = struct.unpack_from('<II', data, off); off += 8
            path = data[off:off+n]; off += (n+3)&~3
            n = struct.unpack_from('<I', data, off)[0]; off += 4
            payload = data[off:off+n]; off += (n+3)&~3
            if kind == 0 and path == b'bin/uunote': got_user = payload
        assert got_user == user.read_bytes(), 'native user differs'
        return d/'gui.iso'
    stage = d/'stage'; (stage/'bin').mkdir(parents=True)
    shutil.copyfile(user, stage/'bin/uunote')
    subprocess.run([sys.executable, str(ROOT/'scripts/mkramdisk.py'), str(stage),
                    str(tree/'boot/ramdisk.krfs')], check=True, capture_output=True)
    (tree/'boot/grub/grub.cfg').write_text('set timeout=0\nset default=0\ninsmod all_video\n'
        'set gfxmode=640x480x32\nset gfxpayload=keep\nterminal_output gfxterm\n'
        'menuentry hs {\n multiboot2 /boot/kernel.elf\n module2 /boot/ramdisk.krfs\n boot\n}\n')
    cmd = ['grub-mkrescue']
    if os.environ.get('HS_TEST_GRUB_DIR'): cmd += ['-d', os.environ['HS_TEST_GRUB_DIR']]
    subprocess.run(cmd+['-o', str(d/'gui.iso'), str(tree)], env=env, check=True, capture_output=True)
    return d/'gui.iso'


def run(d, iso):
    serial = d/'serial'; qmp = d/'qmp'
    serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    p = subprocess.Popen([qemu, '-cdrom', str(iso), '-boot', 'd', '-m', '256M',
        '-nic', 'none', '-display', 'none', '-serial', 'file:'+str(serial),
        '-qmp', 'unix:'+str(qmp)+',server=on,wait=off'], stdout=subprocess.DEVNULL, stderr=err)
    s = None
    def output(): return serial.read_text(errors='replace') if serial.exists() else ''
    def wait_for(predicate, label, seconds=45):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            if predicate(): return
            assert p.poll() is None, ('QEMU exited', output())
            time.sleep(.03)
        raise AssertionError((label, output()[-2500:]))
    try:
        wait_for(lambda:'GUI APP READY' in output(), 'initial GUI boot')
        assert 'GUI KERNEL READY 640 480' in output(), output()
        s = socket.socket(socket.AF_UNIX); s.settimeout(10); s.connect(str(qmp))
        f = s.makefile('rwb', buffering=0); json.loads(f.readline())
        def execute(name, args=None):
            req = {'execute':name}
            if args is not None: req['arguments'] = args
            f.write(json.dumps(req).encode()+b'\r\n')
            while True:
                reply = json.loads(f.readline())
                assert 'error' not in reply, reply
                if 'return' in reply: return reply['return']
        execute('qmp_capabilities')
        def hmp(cmd):
            result = execute('human-monitor-command', {'command-line':cmd})
            assert not result, (cmd, result)
        def snap(name):
            target = d/(name+'.ppm'); hmp('screendump '+str(target))
            with target.open('rb') as img:
                assert img.readline().strip() == b'P6'
                dims = img.readline()
                while dims.startswith(b'#'): dims = img.readline()
                assert dims.strip() == b'640 480'; assert img.readline().strip() == b'255'
                rgb = img.read(); assert len(rgb) == 640*480*3
            return rgb
        def pixel(img, x, y): return img[(y*640+x)*3:(y*640+x)*3+3]
        def crop(img, x, y, w, h):
            return b''.join(img[((y+dy)*640+x)*3:((y+dy)*640+x+w)*3] for dy in range(h))
        def edit_count(): return len(re.findall(r'GUI\s+EDIT\s+(\d+)', output()))
        def key(name, changed=True):
            before = edit_count(); start = time.monotonic(); hmp('sendkey '+name)
            if changed:
                wait_for(lambda:edit_count() == before+1, 'edit '+name, 10)
                latencies.append(time.monotonic()-start)
            else: time.sleep(.3)
        def click():
            hmp('mouse_button 1'); time.sleep(.1); hmp('mouse_button 0'); time.sleep(.2)
        def input_pixels(img, text, x=80, y=100):
            want = bytearray(WHITE*(444*24))
            for index, ch in enumerate(text):
                for row, bits in enumerate(FORMS[ch]):
                    for col in range(5):
                        if bits & (1<<(4-col)):
                            at = ((8+row)*444+4+index*6+col)*3; want[at:at+3] = INK
            for row in range(7):
                for col in range(5):
                    at = ((8+row)*444+4+len(text)*6+col)*3; want[at:at+3] = CARET
            assert crop(img,x+16,y+90,444,24) == want, ('input RGB mismatch',text[:5],len(text))
        latencies = []
        initial = snap('initial'); input_pixels(initial,'')
        assert pixel(initial,80,100) == bytes.fromhex('555a66')
        # Body click focuses without covering the input strip.
        hmp('mouse_move 110 -160'); click()
        key('h'); key('i')
        typed = snap('typed'); input_pixels(typed,'HI')
        assert pixel(typed,80,100) == bytes.fromhex('2a6fdb')
        key('backspace'); key('a'); input_pixels(snap('edited'),'HA')
        key('ret'); input_pixels(snap('cleared'),'')
        # Display cap is real, not only documented: the 61st byte is ignored.
        for _ in range(60): key('a')
        before = edit_count(); key('a', False); key('up', False)
        assert edit_count() == before
        full = snap('full'); input_pixels(full,'A'*60)
        # Drag from (110,103) to (140,123), with no key event needed to redraw.
        hmp('mouse_move 0 57'); time.sleep(.2); hmp('mouse_button 1'); time.sleep(.2)
        hmp('mouse_move 30 -20'); time.sleep(.2); hmp('mouse_button 0')
        def dragged(): return pixel(snap('dragged'),110,120) == bytes.fromhex('2a6fdb')
        wait_for(dragged, 'pointer-driven drag repaint', 10)
        def body_preserved(img):
            # Ignore the software cursor's old body position and its new
            # title position (which overlaps the body's first four rows).
            for yy in range(174):
                for xx in range(480):
                    if 30 <= xx < 37 and (54 <= yy < 61 or yy < 4): continue
                    if pixel(full,80+xx,106+yy) != pixel(img,110+xx,126+yy): return False
            return True
        wait_for(lambda:body_preserved(snap('dragged')), 'complete moved body repaint', 10)
        dragged_image = snap('dragged'); input_pixels(dragged_image,'A'*60,110,120)
        assert pixel(dragged_image,80,100) == BG, 'old window location not cleared'
        # Desktop click drops input; returning focus restores it.
        hmp('mouse_move -130 113'); click(); key('b',False)
        assert edit_count() == before
        hmp('mouse_move 120 -150'); click(); key('backspace')
        input_pixels(snap('refocused'),'A'*59,110,120)
        key('down',False)
        wait_for(lambda:'GUI SESSION STOPPED' in output(), 'ring3 exit cleanup', 10)
        assert re.search(r'GUI SESSION STOPPED\s+0\s+0\s+0\s+0', output()), output()
        closed = snap('closed')
        # Only the 7x7 software cursor may remain on the desktop.
        for y in range(480):
            for x in range(640):
                if 130 <= x < 137 and 160 <= y < 167: continue
                assert pixel(closed,x,y) == BG, ('stale exit pixel',x,y)
        print('GUI max edit-to-present seconds', round(max(latencies),3))
    finally:
        if s: s.close()
        p.terminate()
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
        err.close()
        if EVIDENCE:
            dest = Path(EVIDENCE)/d.name; dest.mkdir(parents=True,exist_ok=True)
            for path in d.iterdir():
                if path.suffix == '.ppm' or path.name in ('serial','qemu.stderr'):
                    shutil.copyfile(path,dest/path.name)


if __name__ == '__main__':
    if '--prepare' in sys.argv:
        d = Path(sys.argv[sys.argv.index('--prepare')+1]); d.mkdir(parents=True, exist_ok=True)
        boot(d, '--ast' not in sys.argv)
        print('prepared native-verified IR ISO' if '--ast' not in sys.argv else 'prepared AST ISO')
    elif '--run-prepared' in sys.argv:
        d = Path(sys.argv[sys.argv.index('--run-prepared')+1]); run(d,d/'gui.iso')
        print('ok prepared GUI session')
    else:
        for ir_backend in (True,False):
            with tempfile.TemporaryDirectory(prefix='gui-'+('ir-' if ir_backend else 'ast-')) as temp:
                d = Path(temp); run(d,boot(d,ir_backend))
            print('ok GRUB module2/ring3 keyboard, focus, drag, glyph RGB, cap and exit', 'ir' if ir_backend else 'ast')
        print('2/2 interactive GUI session gates; IR native kernel/user bytes verified')
