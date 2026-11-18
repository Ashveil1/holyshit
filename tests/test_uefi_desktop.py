#!/usr/bin/env python3
"""Real x86-64 UEFI GRUB -> Multiboot2 -> ring3 desktop, no host effects.

OVMF code is read-only; variables use a disposable copy of a blank template.
No physical storage or host firmware variables are accessed. PS/2 emulated input is not USB/HID or real HP support.
"""
import hashlib, os, re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_gui_session import boot
from test_desktop_session import run
ROOT=Path(__file__).resolve().parent.parent

def firmware_paths():
    if os.environ.get('HS_OVMF_CODE'):
        path=Path(os.environ['HS_OVMF_CODE'])
        if not path.is_file():raise SystemExit('FAIL configured HS_OVMF_CODE missing')
        variables=Path(os.environ.get('HS_OVMF_VARS',str(path.with_name('OVMF_VARS_4M.fd' if '4M' in path.name else 'OVMF_VARS.fd'))))
        if not variables.is_file():raise SystemExit('FAIL matching OVMF variables template missing')
        return path,variables
    for name in ['/usr/share/OVMF/OVMF_CODE_4M.fd','/usr/share/OVMF/OVMF_CODE.fd',
                 '/usr/share/edk2/ovmf/OVMF_CODE.fd']:
        path=Path(name);variables=path.with_name('OVMF_VARS_4M.fd' if '4M' in path.name else 'OVMF_VARS.fd')
        if path.is_file() and variables.is_file():return path,variables
    if os.environ.get('HS_REQUIRE_UEFI')=='1':raise SystemExit('FAIL required UEFI test: OVMF firmware missing')
    print('skip UEFI desktop: OVMF unavailable');sys.exit(0)

def check(d,firmware,variables):
    catalog=subprocess.run(['xorriso','-indev',str(d/'gui.iso'),'-report_el_torito','plain'],capture_output=True,text=True,check=True)
    assert re.search(r'El Torito boot img\s*:\s+1\s+UEFI\s+y',catalog.stdout+catalog.stderr),catalog
    before=hashlib.sha256(firmware.read_bytes()).digest()
    template=variables.read_bytes();scratch=d/'OVMF_VARS.fd';scratch.write_bytes(template)
    disk=d/'untouched.img';data=b'NOT A KVOL DISK'+bytes(1024*1024-15);disk.write_bytes(data)
    run(d,disk,firmware,scratch)
    out=(d/'serial').read_text(errors='replace')
    assert 'GUI KERNEL READY 640 480' in out and 'GUI VOLUME' not in out,out
    module=re.search(r'GUI MODULE\s+(\d+)\s+(\d+)',out);assert module,out
    start,end=map(int,module.groups())
    # Allocation placement can change with GRUB/OVMF versions. The parser
    # and PMM endpoint checks enforce kernel disjointness in either case.
    assert 4096<=start<end<=0xA0000 or 0x100000<=start<end<=0x40000000,(start,end)
    assert disk.read_bytes()==data,'UEFI default desktop wrote attached disk'
    assert hashlib.sha256(firmware.read_bytes()).digest()==before,'firmware ROM changed'
    assert variables.read_bytes()==template,'firmware variables template changed'
    print('ok UEFI GRUB low module, framebuffer, full desktop edit/drag/reopen/exit, no disk/firmware writes')

if __name__=='__main__':
    firmware,variables=firmware_paths()
    if '--run-prepared' in sys.argv:
        check(Path(sys.argv[sys.argv.index('--run-prepared')+1]),firmware,variables)
    else:
        for ir in (True,False):
            with tempfile.TemporaryDirectory(prefix='uefi-desktop-'+('ir-' if ir else 'ast-')) as temp:
                d=Path(temp);boot(d,ir,desktop=True,uefi=True);check(d,firmware,variables)
            print('ok UEFI desktop', 'ir' if ir else 'ast')
        print('2/2 UEFI desktop gates; actual native packaging and full ELF identity checked')
