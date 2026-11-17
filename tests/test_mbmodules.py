#!/usr/bin/env python3
"""Bounded Multiboot2 module parsing under both kernel backends."""
import contextlib, io, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip MB2 module kernel pins: QEMU unavailable'); sys.exit(0)
for ir_backend in (True, False):
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp); image = d / 'kernel'; serial = d / 'serial'
        with contextlib.redirect_stdout(io.StringIO()):
            rc = build_xkernel(str(ROOT / 'kernel/kmbmodtest.holy'), str(image), ir_backend=ir_backend)
        assert not rc
        p = subprocess.Popen([qemu, '-kernel', str(image), '-m', '256M', '-nic', 'none',
                              '-display', 'none', '-serial', 'file:' + str(serial)], stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                out = serial.read_text(errors='replace') if serial.exists() else ''
                if 'mbmods-done\n' in out or p.poll() is not None: break
                time.sleep(.05)
            assert 'mbmods-done\n' in out and '\nfails 0\n' in out, out
            assert out.count('ok ') == 33, out
        finally:
            p.kill(); p.wait()
    print('ok MB2 module boundary/malformed pins', 'ir' if ir_backend else 'ast')
print('2/2 MB2 module kernel gates')
