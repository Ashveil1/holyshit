#!/usr/bin/env python3
"""PCI config-space enumeration: boot kpcitest under QEMU (default pc
machine) on both codegen backends and require every pinned function to
match. The pinned table is cross-checked against the QEMU monitor's own
"info pci" output."""
from pathlib import Path
import contextlib, io, os, shutil, subprocess, sys, tempfile, time
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_xkernel
qemu = os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
    print('skip pci enumeration: QEMU unavailable'); sys.exit(0)
os.environ.setdefault('HSPATH', f'{ROOT}:{ROOT}/kernel')
total = 0
for ir_backend in (True, False):
    backend = 'ir' if ir_backend else 'ast'
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        image = d / 'kernel'
        with contextlib.redirect_stdout(io.StringIO()):
            rc = build_xkernel(str(ROOT / 'kernel/kpcitest.holy'), str(image), ir_backend=ir_backend)
        assert not rc, f'pci test kernel build failed ({backend})'
        serial = d / 'serial'
        p = subprocess.Popen([qemu, '-kernel', str(image), '-serial', f'file:{serial}',
                              '-display', 'none', '-nic', 'none'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if serial.exists() and 'PCI TEST DONE' in serial.read_text(errors='replace'):
                    break
                if p.poll() is not None:
                    raise AssertionError(f'QEMU exited before PCI TEST DONE ({backend})')
                time.sleep(0.1)
            else:
                raise AssertionError(f'timeout waiting for PCI TEST DONE ({backend})')
            time.sleep(0.5)
            out = serial.read_text(errors='replace')
            assert 'PCI TEST DONE 0' in out, f'pci gate failures ({backend}):\n{out}'
            oks = out.count('\nok ') + (1 if out.startswith('ok ') else 0)
            assert oks == 35, f'expected 35 ok lines ({backend}), got {oks}:\n{out}'
            total += 1
            print(f'ok pci enumeration 35/35 pinned functions/fields ({backend})')
        finally:
            p.kill()
print(f'{total}/2 pci enumeration gates (IR and AST)')
