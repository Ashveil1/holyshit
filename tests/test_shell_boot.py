#!/usr/bin/env python3
"""Shell-first boot (B22a): the default image comes up straight into sh>.

Arch-style text mode: no boot menu, no desktop, the machine boots to the
ring3 shell (uush) with the boot framebuffer as its console. Keyboard input
is typed over QMP sendkeys, command output is asserted on the serial byte
log, and the screendump proves the framebuffer console rendered the session
(the serial line stays byte-oriented; the screen is what a person sees).
`exit` respawns the shell getty-style, asserted by a second shell start.

IR and AST kernel backends. The IR leg exercises the user-facing packaging
script with NO app argument - proving `shell` is now the default app - and
that its kernel/ramdisk bytes match the reference builds. Boot media: BIOS
El Torito ISO and OVMF usb-storage, the same image a user dd's to a stick.
This is firmware-emulated boot, not real hardware support.
"""
import ast, contextlib, hashlib, io, json, os, re, shutil, socket, struct, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gui_session import qemu
from test_uefi_desktop import firmware_paths
from test_usb_boot import esp_offset, mcopy_out, GRUB_CFG
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
ENV = dict(os.environ, HSPATH=':'.join(str(ROOT/p) for p in ('', 'kernel', 'selfhost', 'selfhost/be')), HSROOT=str(ROOT))
EVIDENCE = Path(os.environ['HS_SHELL_BOOT_EVIDENCE']) if os.environ.get('HS_SHELL_BOOT_EVIDENCE') else None

BG = bytes.fromhex('101418')
SESSION = [('help', 'commands: help echo'),
           ('ls /', 'motd'),
           ('cat /motd', 'second line here'),
           ('write /n b22 shell', None),
           ('cat /n', 'b22 shell'),
           ('rm /n', None),
           ('cat /n', 'no such file'),
           ('exit', 'shell exit 0')]


def build(d, ir_backend):
    kernel = d/'kernel.elf'; uush = d/'uush.elf'; hi = d/'hi.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        assert build_xkernel(str(ROOT/'kernel/kshell.holy'), str(kernel), ir_backend=ir_backend) == 0
        assert build_x64(str(ROOT/'kernel/uush.holy'), str(uush)) == 0
        assert build_x64(str(ROOT/'kernel/uuhi.holy'), str(hi)) == 0
    return kernel, uush, hi


def package_usb(d, ir_backend, kernel, uush, hi):
    if ir_backend:
        # No app argument: the packaging default must BE the shell.
        subprocess.run([str(ROOT/'scripts/build-gui-usb.sh'), str(d/'usb.img')],
                       env=ENV, check=True, capture_output=True, timeout=300)
        before = (d/'usb.img').read_bytes()
        again = subprocess.run([str(ROOT/'scripts/build-gui-usb.sh'), str(d/'usb.img')],
                               env=ENV, capture_output=True, timeout=10)
        assert again.returncode != 0 and (d/'usb.img').read_bytes() == before, 'USB image output overwritten'
        offset = esp_offset(d/'usb.img')
        mcopy_out(d/'usb.img', offset, '/boot/kernel.elf', d/'kernel.img.elf')
        assert (d/'kernel.img.elf').read_bytes() == kernel.read_bytes(), 'packaged kernel differs'
        mcopy_out(d/'usb.img', offset, '/boot/ramdisk.krfs', d/'ramdisk.img.krfs')
        data = (d/'ramdisk.img.krfs').read_bytes(); assert data[:4] == b'KRFS'
        off = 8; got = {}
        for _ in range(struct.unpack_from('<I', data, 4)[0]):
            kind, n = struct.unpack_from('<II', data, off); off += 8
            path = data[off:off+n]; off += (n+3)&~3
            n = struct.unpack_from('<I', data, off)[0]; off += 4
            payload = data[off:off+n]; off += (n+3)&~3
            if kind == 0: got[path] = payload
        assert got.get(b'bin/uush') == uush.read_bytes(), 'packaged shell differs'
        assert got.get(b'bin/hi') == hi.read_bytes(), 'packaged exec target differs'
        assert b'motd' in got and b'etc/config' in got, 'ramdisk base missing'
        return d/'usb.img'
    tree = d/'tree'; stage = d/'stage'; (tree/'boot/grub').mkdir(parents=True); (stage/'bin').mkdir(parents=True)
    for f in (ROOT/'kernel/ramdisk').rglob('*'):
        if f.is_file():
            dest = stage/f.relative_to(ROOT/'kernel/ramdisk')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)
    shutil.copyfile(uush, stage/'bin/uush'); shutil.copyfile(hi, stage/'bin/hi')
    subprocess.run([sys.executable, str(ROOT/'scripts/mkramdisk.py'), str(stage),
                    str(tree/'boot/ramdisk.krfs')], check=True, capture_output=True)
    shutil.copyfile(kernel, tree/'boot/kernel.elf')
    (tree/'boot/grub/grub.cfg').write_text(GRUB_CFG)
    subprocess.run([str(ROOT/'scripts/package-gui-usb.sh'), str(tree), str(d/'usb.img')],
                   env=ENV, check=True, capture_output=True, timeout=120)
    return d/'usb.img'


def package_iso(d, kernel, uush, hi):
    # BIOS El Torito leg: same tree shape the script ships, built locally so
    # both firmware paths gate the identical reference bytes.
    tree = d/'isotree'; stage = d/'isostage'; (tree/'boot/grub').mkdir(parents=True); (stage/'bin').mkdir(parents=True)
    for f in (ROOT/'kernel/ramdisk').rglob('*'):
        if f.is_file():
            dest = stage/f.relative_to(ROOT/'kernel/ramdisk')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)
    shutil.copyfile(uush, stage/'bin/uush'); shutil.copyfile(hi, stage/'bin/hi')
    subprocess.run([sys.executable, str(ROOT/'scripts/mkramdisk.py'), str(stage),
                    str(tree/'boot/ramdisk.krfs')], check=True, capture_output=True)
    shutil.copyfile(kernel, tree/'boot/kernel.elf')
    (tree/'boot/grub/grub.cfg').write_text(GRUB_CFG)
    cmd = ['grub-mkrescue', '-o', str(d/'shell.iso'), str(tree)]
    if os.environ.get('HS_TEST_GRUB_DIR'):
        cmd[1:1] = ['-d', os.environ['HS_TEST_GRUB_DIR']]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    return d/'shell.iso'


KEYMAP = {' ': 'spc', '/': 'slash', '\x08': 'backspace'}


def session(d, args):
    serial = d/'serial'; qmp = d/'qmp'; serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    p = subprocess.Popen([qemu, '-m', '256M', '-nic', 'none', '-display', 'none',
        '-serial', 'file:'+str(serial), '-qmp', 'unix:'+str(qmp)+',server=on,wait=off'] + args,
        stderr=err)
    def out(): return serial.read_text(errors='replace') if serial.exists() else ''
    def wait_for(test, label, seconds=60):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            if test(): return
            assert p.poll() is None, ('QEMU exited', out()[-2000:])
            time.sleep(.05)
        raise AssertionError((label, out()[-2000:]))
    try:
        wait_for(lambda: 'sh> ' in out(), 'shell prompt')
        time.sleep(2)  # TCG: let the guest settle before typing
        s = socket.socket(socket.AF_UNIX); s.settimeout(10); s.connect(str(qmp))
        f = s.makefile('rwb', buffering=0); json.loads(f.readline())
        def cmd(name, cargs=None):
            req = {'execute': name}
            if cargs is not None: req['arguments'] = cargs
            f.write(json.dumps(req).encode()+b'\r\n')
            while True:
                r = json.loads(f.readline()); assert 'error' not in r, r
                if 'return' in r: return r['return']
        cmd('qmp_capabilities')
        def h(c):
            r = cmd('human-monitor-command', {'command-line': c})
            assert not r, (c, r)
        for line, expect in SESSION:
            n = out().count('sh> ')
            for ch in line:
                h('sendkey '+KEYMAP.get(ch, ch)); time.sleep(0.6)
            h('sendkey ret')
            if expect is not None:
                wait_for(lambda: expect in out(), 'output of '+line, 40)
            else:
                wait_for(lambda: out().count('sh> ') > n, 'prompt after '+line, 40)
            time.sleep(0.5)
        # exit respawns the shell: a second start banner and a fresh prompt
        wait_for(lambda: out().count('shell start') >= 2, 'shell respawn', 40)
        wait_for(lambda: out().count('sh> ') > n, 'prompt after respawn', 40)
        text = out()
        assert 'EXC ' not in text, text[-2000:]
        target = d/'screen.ppm'
        h('screendump '+str(target))
        with target.open('rb') as im:
            assert im.readline().strip() == b'P6'
            dims = im.readline()
            while dims.startswith(b'#'): dims = im.readline()
            assert dims.strip() == b'640 480'; assert im.readline().strip() == b'255'
            rgb = im.read(); assert len(rgb) == 640*480*3
        non_bg = sum(1 for i in range(0, len(rgb), 3) if rgb[i:i+3] != BG)
        assert non_bg > 2000, f'framebuffer console looks empty ({non_bg} px)'
        # Exact glyph pixels of the fresh prompt, on one of the retained
        # rows. An arbitrary nonempty screen cannot satisfy this oracle.
        font = (ROOT/'std/font.holy').read_text()
        chars = ast.literal_eval(re.search(r'^characters = (.+)$', font, re.M)[1])
        rows = ast.literal_eval(re.search(r'^rows = (.+)$', font, re.M)[1])
        want = bytearray(BG * (36 * 16))
        for col, char in enumerate('SH>'):
            for yy, bits in enumerate(rows[chars.index(char)]):
                for xx in range(5):
                    if bits & (1 << (4-xx)):
                        for dy in range(2):
                            for dx in range(2):
                                off = ((yy*2+dy)*36 + col*12+xx*2+dx)*3
                                want[off:off+3] = bytes.fromhex('dde3ea')
        def crop(y):
            return b''.join(rgb[((y+dy)*640+8)*3:((y+dy)*640+44)*3] for dy in range(16))
        assert any(crop(8+row*16) == want for row in range(17)), 'fresh prompt glyph pixels missing'

        return text, non_bg
    finally:
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill()
        err.close()


def save_evidence(d, label):
    if EVIDENCE:
        dest = EVIDENCE/label
        dest.mkdir(parents=True, exist_ok=True)
        for name in ('screen.ppm', 'serial', 'qemu.stderr'):
            shutil.copyfile(d/name, dest/name)


def main():
    fails = []
    def check(label, fn):
        try:
            fn(); print('ok', label)
        except Exception as e:
            print('FAIL', label, repr(e)[:500]); fails.append(label)
    fw, vars_ = firmware_paths()
    for ir in (True, False):
        backend = 'ir' if ir else 'ast'
        with tempfile.TemporaryDirectory(prefix='hs-shell-boot-') as td:
            d = Path(td)
            kernel, uush, hi = build(d, ir)
            def leg_usb():
                image = package_usb(d, ir, kernel, uush, hi)
                scratch = d/'OVMF_VARS.fd'; scratch.write_bytes(Path(vars_).read_bytes())
                text, px = session(d, ['-machine', 'q35',
                    '-device', 'qemu-xhci,id=xhci', '-device', 'usb-storage,drive=usbdisk',
                    '-drive', 'id=usbdisk,if=none,format=raw,file='+str(image),
                    '-drive', 'if=pflash,format=raw,readonly=on,file='+str(fw),
                    '-drive', 'if=pflash,format=raw,file='+str(scratch)])
                assert 'shell start' in text and px > 2000
                save_evidence(d, backend+'-usb')
            def leg_iso():
                iso = package_iso(d, kernel, uush, hi)
                text, px = session(d, ['-cdrom', str(iso)])
                assert 'shell start' in text and px > 2000
                save_evidence(d, backend+'-bios')
            check(f'{backend} usb-storage boot to shell', leg_usb)
            check(f'{backend} bios iso boot to shell', leg_iso)
    print('fails', len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
