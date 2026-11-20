#!/usr/bin/env python3
"""USB HID desktop: QMP input arrives over xHCI only, PS/2 drop-drained.

Boots the kguiusb entry (kguisession + kusbin, exclusive usb_only routing)
on q35 with qemu-xhci usb-kbd/usb-mouse. QMP sendkey/mouse events reach
every emulated device, so each key producing exactly one routed edit and
each drag landing once proves both directions: USB reports route into the
desktop input queue and the PS/2 duplicates are drop-drained. Visible
proof: typing in a note and dragging a window, checked in screendump
pixels. BIOS and UEFI, IR and AST backends, native packaging identity.
"""
import contextlib, hashlib, io, json, os, re, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gui_session import qemu, BG, INK, WHITE, CARET, FORMS
FORMS['B'] = [30, 17, 17, 30, 17, 17, 30]
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
ENV = dict(os.environ, HSPATH=':'.join(str(ROOT/p) for p in ('', 'kernel', 'selfhost', 'selfhost/be')), HSROOT=str(ROOT))
USB = ['-machine', 'q35', '-device', 'qemu-xhci,id=xhci',
       '-device', 'usb-kbd,bus=xhci.0', '-device', 'usb-mouse,bus=xhci.0']

def boot(d, ir_backend, uefi=False):
    tree = d/'tree'; (tree/'boot/grub').mkdir(parents=True)
    user = d/'uunote'; kernel = tree/'boot/kernel.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        assert build_x64(str(ROOT/'kernel/uudesk.holy'), str(user)) == 0
        assert build_xkernel(str(ROOT/'kernel/kguiusb.holy'), str(kernel), ir_backend=ir_backend) == 0
    if ir_backend:
        # The real packaging entry point with the USB desktop app mode.
        subprocess.run([str(ROOT/'scripts/build-gui-iso.sh'), str(d/'gui.iso'), 'desktop-usb'] + (['uefi'] if uefi else []),
                       env=ENV, check=True, capture_output=True, timeout=300)
        for path, expected in [('kernel.elf', kernel)]:
            subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(d/'gui.iso'),
                            '-extract', '/boot/'+path, str(d/path)], check=True, capture_output=True)
            assert (d/path).read_bytes() == expected.read_bytes(), 'packaged kernel != reference build'
        return d/'gui.iso'
    stage = d/'stage'; (stage/'bin').mkdir(parents=True)
    shutil.copyfile(user, stage/'bin/uunote')
    subprocess.run([sys.executable, str(ROOT/'scripts/mkramdisk.py'), str(stage),
                    str(tree/'boot/ramdisk.krfs')], check=True, capture_output=True)
    (tree/'boot/grub/grub.cfg').write_text('set timeout=0\nset default=0\ninsmod all_video\n'
        'set gfxmode=640x480x32\nset gfxpayload=keep\nterminal_output gfxterm\n'
        'menuentry hs {\n multiboot2 /boot/kernel.elf\n module2 /boot/ramdisk.krfs\n boot\n}\n')
    if uefi:
        subprocess.run([str(ROOT/'scripts/package-gui-uefi.sh'), str(tree), str(d/'gui.iso')],
                       env=ENV, check=True, capture_output=True, timeout=60)
        return d/'gui.iso'
    cmd = ['grub-mkrescue']
    if os.environ.get('HS_TEST_GRUB_DIR'): cmd += ['-d', os.environ['HS_TEST_GRUB_DIR']]
    subprocess.run(cmd+['-o', str(d/'gui.iso'), str(tree)], env=ENV, check=True, capture_output=True)
    return d/'gui.iso'

def run(d, iso, firmware=None, firmware_vars=None):
    serial = d/'serial'; qmp = d/'qmp'; serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    args = [qemu, '-cdrom', str(iso), '-boot', 'd', '-m', '256M', '-nic', 'none',
            '-display', 'none', '-serial', 'file:'+str(serial), '-qmp', 'unix:'+str(qmp)+',server=on,wait=off'] + USB
    if firmware_vars:
        args += ['-drive', 'if=pflash,format=raw,readonly=on,file='+str(firmware),
                 '-drive', 'if=pflash,format=raw,file='+str(firmware_vars)]
    p = subprocess.Popen(args, stderr=err)
    s = None
    def out(): return serial.read_text(errors='replace') if serial.exists() else ''
    def wait_for(test, label, seconds=15):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            if test(): return
            assert p.poll() is None, out()
            time.sleep(.03)
        raise AssertionError((label, out()[-3000:]))
    try:
        wait_for(lambda: 'DESKTOP READY' in out(), 'desktop ready', 60)
        s = socket.socket(socket.AF_UNIX); s.settimeout(10); s.connect(str(qmp)); f = s.makefile('rwb', buffering=0)
        json.loads(f.readline())
        def cmd(name, args=None):
            req = {'execute': name}
            if args is not None: req['arguments'] = args
            f.write(json.dumps(req).encode()+b'\r\n')
            while True:
                r = json.loads(f.readline()); assert 'error' not in r, r
                if 'return' in r: return r['return']
        cmd('qmp_capabilities')
        def h(c): assert not cmd('human-monitor-command', {'command-line': c})
        cursor = [0, 0]
        def move(x, y):
            h('mouse_move '+str(x-cursor[0])+' '+str(cursor[1]-y)); cursor[:] = [x, y]; time.sleep(.15)
        def click(x, y):
            move(x, y); h('mouse_button 1'); time.sleep(.1); h('mouse_button 0'); time.sleep(.15)
        def count(): return len(re.findall(r'DESKTOP\s+(EDIT|OPEN|CLOSE)\s+', out()))
        def key(k, changed=True):
            before = count(); h('sendkey '+k)
            if changed: wait_for(lambda: count() == before+1, 'key '+k)
            else: time.sleep(.2)
        def snap(name):
            path = d/(name+'.ppm'); h('screendump '+str(path))
            with path.open('rb') as im:
                assert im.readline().strip() == b'P6'; dims = im.readline()
                while dims.startswith(b'#'): dims = im.readline()
                assert dims.strip() == b'640 480'; assert im.readline().strip() == b'255'
                data = im.read(); assert len(data) == 640*480*3
            return data
        def pixel(im, x, y): return im[(y*640+x)*3:(y*640+x)*3+3]
        def field(im, text, x, y):
            want = bytearray(WHITE*(416*56))
            row_index = 0; column = 0
            caret_pos = None
            for offset, ch in enumerate(text):
                if ch != '\n' and column == 32:
                    row_index += 1; column = 0
                if offset == len(text): caret_pos = (row_index, column)
                if ch == '\n':
                    row_index += 1; column = 0; continue
                for row, bits in enumerate(FORMS[ch]):
                    for col in range(5):
                        if bits & (1 << (4-col)):
                            for dy in range(2):
                                for dx in range(2):
                                    at = ((8+row_index*16+row*2+dy)*416+4+column*12+col*2+dx)*3
                                    want[at:at+3] = INK
                column += 1
            if caret_pos is None: caret_pos = (row_index, column)
            for row in range(14):
                for col in range(10):
                    at = ((8+caret_pos[0]*16+row)*416+4+caret_pos[1]*12+col)*3; want[at:at+3] = CARET
            got = b''.join(im[((y+60+dy)*640+x+12)*3:((y+60+dy)*640+x+428)*3] for dy in range(56))
            assert got == want, ('field mismatch', text[:5], len(text), x, y)
        def field_wait(name, text, x, y):
            # Serial EDIT/CLOSE lines precede the redraw they describe, so a
            # snap taken right after key() can race the framebuffer. Re-snap
            # until the field matches (or wait_for times out with the serial).
            def ok():
                try: field(snap(name), text, x, y); return True
                except AssertionError: return False
            wait_for(ok, 'field '+repr(text)+' at '+str(x)+','+str(y))
        initial = snap('initial'); field(initial, '', 24, 132); field(initial, '', 176, 308)
        # Typing: one DESKTOP EDIT per sendkey proves USB routed + PS/2 dropped.
        # QMP sendkey reaches the guest instantly while usb-mouse reports
        # trickle out on QEMU's pointer timer, so a key sent right after a
        # click can overtake the click's press report. Wait for the click's
        # visible effect (raised title) before typing, as moved() does for
        # the drag.
        def raised(x, y, label):
            wait_for(lambda: pixel(snap('raise'), x, y) == bytes.fromhex('2a6fdb'), label)
        click(48, 170); raised(28, 136, 'note1 raised'); key('h'); key('i')
        click(200, 346); raised(180, 312, 'note2 raised'); key('b')
        field_wait('both', 'HI', 24, 132); field_wait('both2', 'B', 176, 308)
        click(48, 170); raised(28, 136, 'note1 raised again'); key('backspace'); key('a')
        field_wait('edited', 'HA', 24, 132)
        # Drag note2 over note1 by its title: raise + move lands once.
        move(192, 311); h('mouse_button 1'); time.sleep(.15); move(196, 175); h('mouse_button 0')
        def moved():
            im = snap('overlap')
            return pixel(im, 180, 172) == bytes.fromhex('2a6fdb') and pixel(im, 176, 450) == BG
        wait_for(moved, 'note2 drag/raise')
        field_wait('overlap2', 'B', 180, 172)
        # Close both notes, then exit the session from the launcher.
        click(550, 200); key('esc'); field_wait('one-note', 'HA', 24, 132)
        click(48, 170); raised(28, 136, 'note1 raised after close'); key('esc')
        def cleared():
            im = snap('launcher-only')
            return all(pixel(im, x, y) == BG for x, y in [(24, 132), (100, 210), (176, 308), (400, 410)])
        wait_for(cleared, 'launcher only after closing notes')
        click(60, 50); key('esc', False)
        wait_for(lambda: re.search(r'GUI SESSION STOPPED\s+0\s+0\s+0\s+0', out()), 'complete session exit')
    finally:
        if s: s.close()
        p.terminate()
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
        err.close()
        if os.environ.get('HS_GUI_EVIDENCE'):
            dest = Path(os.environ['HS_GUI_EVIDENCE'])/d.name; dest.mkdir(parents=True, exist_ok=True)
            for path in d.iterdir():
                if path.suffix == '.ppm' or path.name in ('serial', 'qemu.stderr'): shutil.copyfile(path, dest/path.name)

def firmware_paths():
    if os.environ.get('HS_OVMF_CODE'):
        path = Path(os.environ['HS_OVMF_CODE'])
        if not path.is_file(): raise SystemExit('FAIL configured HS_OVMF_CODE missing')
        variables = Path(os.environ.get('HS_OVMF_VARS', str(path.with_name('OVMF_VARS_4M.fd' if '4M' in path.name else 'OVMF_VARS.fd'))))
        if not variables.is_file(): raise SystemExit('FAIL matching OVMF variables template missing')
        return path, variables
    if os.environ.get('HS_REQUIRE_UEFI') == '1': raise SystemExit('FAIL required UEFI test: OVMF firmware missing')
    return None, None

if __name__ == '__main__':
    backends = (True, False)
    if '--backend' in sys.argv:
        backends = (sys.argv[sys.argv.index('--backend')+1] == 'ir',)
    firmware, variables = firmware_paths()
    for ir_backend in backends:
        with tempfile.TemporaryDirectory(prefix='usbdesk-'+('ir-' if ir_backend else 'ast-')) as temp:
            d = Path(temp); iso = boot(d, ir_backend); run(d, iso)
        print('ok USB desktop xHCI-only input (type/drag/close/exit)', 'ir' if ir_backend else 'ast')
        if firmware:
            template = variables.read_bytes()
            with tempfile.TemporaryDirectory(prefix='usbdesk-uefi-'+('ir-' if ir_backend else 'ast-')) as temp:
                d = Path(temp); iso = boot(d, ir_backend, uefi=True)
                scratch = d/'OVMF_VARS.fd'; scratch.write_bytes(template)
                run(d, iso, firmware, scratch)
                assert variables.read_bytes() == template, 'firmware variables template changed'
            print('ok USB desktop UEFI xHCI-only input', 'ir' if ir_backend else 'ast')
    print(str(len(backends))+'/'+str(len(backends))+' USB desktop gates; native IR packaging identity checked')
