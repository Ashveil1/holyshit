#!/usr/bin/env python3
"""Real USB-stick boot path: raw GPT/ESP image as usb-storage, OVMF boots it.

No El Torito anywhere: the image build-gui-usb.sh ships is the same bytes a
user dd's to a USB stick, attached here as a QEMU USB mass-storage device on
qemu-xhci. OVMF's own XHCI + USB mass-storage + FAT/GPT stack finds the ESP,
runs BOOTX64.EFI, GRUB loads the kernel and the desktop comes up. The OVMF
boot-entry line naming the USB harddrive is asserted as boot-path evidence.
IR and AST backends; the IR leg exercises the user-facing packaging script
and proves its kernel/ramdisk bytes match the reference builds. The image,
firmware ROM and variables template must be byte-identical after the boot.
This is firmware-emulated USB boot, not real HP controller support.
"""
import contextlib, hashlib, io, json, os, re, shutil, socket, struct, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gui_session import qemu, BG
from test_uefi_desktop import firmware_paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64, build_xkernel
ENV = dict(os.environ, HSPATH=':'.join(str(ROOT/p) for p in ('', 'kernel', 'selfhost', 'selfhost/be')), HSROOT=str(ROOT))
EVIDENCE = Path(os.environ['HS_USB_BOOT_EVIDENCE']) if os.environ.get('HS_USB_BOOT_EVIDENCE') else None

GRUB_CFG = ('set timeout=0\nset default=0\ninsmod all_video\n'
    'set gfxmode=640x480x32\nset gfxpayload=keep\nterminal_output gfxterm\n'
    'menuentry hs {\n multiboot2 /boot/kernel.elf\n module2 /boot/ramdisk.krfs\n boot\n}\n')


def esp_offset(image):
    # First GPT entry's starting LBA, read straight from the header.
    data = Path(image).read_bytes()
    assert data[512:520] == b'EFI PART', 'not a GPT image'
    entries_lba, count, size = struct.unpack_from('<QII', data, 512 + 72)
    first = struct.unpack_from('<Q', data, entries_lba * 512 + 32)[0]
    return first * 512


def mcopy_out(image, offset, remote, local):
    subprocess.run(['mcopy', '-o', '-i', f'{image}@@{offset}', '::' + remote, str(local)],
                   env=ENV, check=True, capture_output=True, timeout=60)


def boot(d, ir_backend):
    tree = d/'tree'; (tree/'boot/grub').mkdir(parents=True)
    user = d/'uunote'; kernel = tree/'boot/kernel.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        assert build_x64(str(ROOT/'kernel/uudesk.holy'), str(user)) == 0
        assert build_xkernel(str(ROOT/'kernel/kgui.holy'), str(kernel), ir_backend=ir_backend) == 0
    if ir_backend:
        # The real packaging entry point, not a lookalike.
        subprocess.run([str(ROOT/'scripts/build-gui-usb.sh'), str(d/'usb.img'), 'desktop'],
                       env=ENV, check=True, capture_output=True, timeout=300)
        before = (d/'usb.img').read_bytes()
        again = subprocess.run([str(ROOT/'scripts/build-gui-usb.sh'), str(d/'usb.img')],
                               env=ENV, capture_output=True, timeout=10)
        assert again.returncode != 0 and (d/'usb.img').read_bytes() == before, 'USB image output overwritten'
        # Extract the shipped files to prove script output equals reviewed builds.
        offset = esp_offset(d/'usb.img')
        mcopy_out(d/'usb.img', offset, '/boot/kernel.elf', d/'kernel.img.elf')
        assert (d/'kernel.img.elf').read_bytes() == kernel.read_bytes(), 'packaged kernel differs'
        mcopy_out(d/'usb.img', offset, '/boot/ramdisk.krfs', d/'ramdisk.img.krfs')
        data = (d/'ramdisk.img.krfs').read_bytes(); assert data[:4] == b'KRFS'
        off = 8; got_user = None
        for _ in range(struct.unpack_from('<I', data, 4)[0]):
            kind, n = struct.unpack_from('<II', data, off); off += 8
            path = data[off:off+n]; off += (n+3)&~3
            n = struct.unpack_from('<I', data, off)[0]; off += 4
            payload = data[off:off+n]; off += (n+3)&~3
            if kind == 0 and path == b'bin/uunote': got_user = payload
        assert got_user == user.read_bytes(), 'native user differs'
        return d/'usb.img'
    stage = d/'stage'; (stage/'bin').mkdir(parents=True)
    shutil.copyfile(user, stage/'bin/uunote')
    subprocess.run([sys.executable, str(ROOT/'scripts/mkramdisk.py'), str(stage),
                    str(tree/'boot/ramdisk.krfs')], check=True, capture_output=True)
    (tree/'boot/grub/grub.cfg').write_text(GRUB_CFG)
    subprocess.run([str(ROOT/'scripts/package-gui-usb.sh'), str(tree), str(d/'usb.img')],
                   env=ENV, check=True, capture_output=True, timeout=120)
    return d/'usb.img'


def run(d, image, firmware, variables):
    serial = d/'serial'; qmp = d/'qmp'; serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    template = variables.read_bytes(); scratch = d/'OVMF_VARS.fd'; scratch.write_bytes(template)
    before = hashlib.sha256(Path(image).read_bytes()).digest()
    rom_before = hashlib.sha256(firmware.read_bytes()).digest()
    p = subprocess.Popen([qemu, '-machine', 'q35', '-m', '256M', '-nic', 'none',
        '-display', 'none', '-serial', 'file:'+str(serial),
        '-qmp', 'unix:'+str(qmp)+',server=on,wait=off',
        '-device', 'qemu-xhci,id=xhci', '-device', 'usb-storage,drive=usbdisk',
        '-drive', 'id=usbdisk,if=none,format=raw,file='+str(image),
        '-drive', 'if=pflash,format=raw,readonly=on,file='+str(firmware),
        '-drive', 'if=pflash,format=raw,file='+str(scratch)], stderr=err)
    s = None
    def out(): return serial.read_text(errors='replace') if serial.exists() else ''
    def wait_for(test, label, seconds=60):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            if test(): return
            assert p.poll() is None, ('QEMU exited', out())
            time.sleep(.03)
        raise AssertionError((label, out()[-3000:]))
    try:
        wait_for(lambda: 'DESKTOP READY' in out(), 'desktop ready over USB boot')
        text = out()
        assert 'GUI KERNEL READY 640 480' in text, text
        # The firmware must name the USB mass-storage device as the boot entry:
        # that is the evidence the kernel arrived over the real USB boot path.
        assert 'USB HARDDRIVE' in text and 'starting Boot' in text, text
        module = re.search(r'GUI MODULE\s+(\d+)\s+(\d+)', text); assert module, text
        start, end = map(int, module.groups())
        assert 4096 <= start < end <= 0xA0000 or 0x100000 <= start < end <= 0x40000000, (start, end)
        s = socket.socket(socket.AF_UNIX); s.settimeout(10); s.connect(str(qmp))
        f = s.makefile('rwb', buffering=0); json.loads(f.readline())
        def cmd(name, args=None):
            req = {'execute': name}
            if args is not None: req['arguments'] = args
            f.write(json.dumps(req).encode()+b'\r\n')
            while True:
                reply = json.loads(f.readline())
                assert 'error' not in reply, reply
                if 'return' in reply: return reply['return']
        cmd('qmp_capabilities')
        target = d/'launcher.ppm'
        assert not cmd('human-monitor-command', {'command-line': 'screendump '+str(target)})
        with target.open('rb') as img:
            assert img.readline().strip() == b'P6'
            dims = img.readline()
            while dims.startswith(b'#'): dims = img.readline()
            assert dims.strip() == b'640 480'; assert img.readline().strip() == b'255'
            rgb = img.read(); assert len(rgb) == 640*480*3
        def pixel(x, y): return rgb[(y*640+x)*3:(y*640+x)*3+3]
        # Initial desktop paints: launcher background at the edges and an
        # open note field in the middle, not just a serial banner.
        for x, y in [(10, 10), (320, 460), (600, 470)]:
            assert pixel(x, y) == BG, ('launcher pixel', x, y)
        assert pixel(100, 210) == b'\xff\xff\xff', 'note field pixel'
        print('ok USB image boot: OVMF -> ESP -> GRUB -> desktop over usb-storage')
    finally:
        if s: s.close()
        p.kill(); p.wait(timeout=10)
        err.close()
        if EVIDENCE:
            target_dir = EVIDENCE/d.name; target_dir.mkdir(parents=True, exist_ok=True)
            for name in ('serial', 'qemu.stderr', 'launcher.ppm'):
                if (d/name).exists(): shutil.copyfile(d/name, target_dir/name)
    assert hashlib.sha256(Path(image).read_bytes()).digest() == before, 'boot wrote the USB image'
    assert hashlib.sha256(firmware.read_bytes()).digest() == rom_before, 'firmware ROM changed'
    assert variables.read_bytes() == template, 'firmware variables template changed'


def one(ir_backend, firmware, variables):
    with tempfile.TemporaryDirectory(prefix='usb-boot-'+('ir-' if ir_backend else 'ast-')) as temp:
        d = Path(temp)
        image = boot(d, ir_backend)
        run(d, image, firmware, variables)
    print('ok USB boot', 'ir' if ir_backend else 'ast')


if __name__ == '__main__':
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only')+1]
        assert only in ('ir', 'ast'), only
    if not qemu or not shutil.which('grub-mkimage') or not shutil.which('mformat'):
        if os.environ.get('HS_REQUIRE_GUI') == '1':
            raise SystemExit('FAIL required USB boot: QEMU/GRUB/mtools unavailable')
        print('skip USB boot: optional QEMU/GRUB/mtools unavailable'); sys.exit(0)
    firmware, variables = firmware_paths()
    if only in (None, 'ir'): one(True, firmware, variables)
    if only in (None, 'ast'): one(False, firmware, variables)
    print('USB boot gates passed; same image bytes a dd to a stick would ship')
