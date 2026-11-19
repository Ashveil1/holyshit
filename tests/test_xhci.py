#!/usr/bin/env python3
"""Opt-in USB HID over xHCI on disposable QEMU devices only.

Real q35 qemu-xhci boots with QMP-injected keys and pointer deltas into
usb-kbd/usb-mouse, init refusals on wrong hardware, a real USB stall for the
terminal path, and PCI monitor cross-checks. Both kernel backends with
native/reference full-ELF identity.
"""
from pathlib import Path
import contextlib, hashlib, io, json, os, re, shutil, socket
import subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_xkernel
QEMU=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not QEMU:
    if os.environ.get('HS_REQUIRE_XHCI')=='1':raise SystemExit('FAIL required XHCI: QEMU missing')
    print('skip XHCI: QEMU unavailable');sys.exit(0)
ENV=dict(os.environ,HSPATH=':'.join(str(ROOT/p) for p in ('','kernel','selfhost','selfhost/be')),HSROOT=str(ROOT))
os.environ['HSPATH']=ENV['HSPATH']
EVIDENCE=Path(os.environ['HS_XHCI_EVIDENCE']) if os.environ.get('HS_XHCI_EVIDENCE') else None

def build(source,image,ir):
    with contextlib.redirect_stdout(io.StringIO()):
        rc=build_xkernel(str(source),str(image),ir_backend=ir)
    assert not rc,source

def native_compiler(d,ir):
    compiler=d/('compiler-ir' if ir else 'compiler-ast')
    src=ROOT/'selfhost/be'/('kernel_ir.holy' if ir else 'kernel_hex.holy')
    subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(src),str(compiler)],
                   env=ENV,capture_output=True,check=True,timeout=240)
    return compiler

def native_identity(d,source,reference,compiler,ir):
    native=d/'native.elf'
    if ir:
        subprocess.run([str(compiler),str(source),str(native)],env=ENV,
                       capture_output=True,check=True,timeout=240)
    else:
        result=subprocess.run([str(compiler),str(source)],env=ENV,
                              capture_output=True,text=True,check=True,timeout=240)
        native.write_bytes(bytes.fromhex(''.join(result.stdout.split())))
    assert native.read_bytes()==reference.read_bytes(),'native/reference full ELF mismatch'
    return native

def qmp(sock,command,args=None):
    sock.sendall((json.dumps({'execute':command,'arguments':args or {}})+'\r\n').encode())

def boot(d,image,args,want_pci=False,actions=(),firmware=None,allow_stderr=None):
    d.mkdir(parents=True,exist_ok=True);serial=d/'serial';err=d/'stderr';monitor=d/'qmp'
    cmd=[QEMU,'-machine',args[0],'-m','256M','-serial','file:'+str(serial),
         '-display','none','-nic','none','-no-reboot','-qmp','unix:'+str(monitor)+',server=on,wait=off']
    if firmware:
        code,variables=firmware
        cmd+=['-cdrom',str(image),'-boot','d',
              '-drive',f'if=pflash,format=raw,readonly=on,file={code}',
              '-drive',f'if=pflash,format=raw,file={variables}']
    else:cmd+=['-kernel',str(image)]
    cmd+=args[1:]
    with err.open('wb') as errors:
        p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=errors,env=ENV)
        try:
            sock=None;replies=None
            def call(name,arguments=None):
                qmp(sock,name,arguments)
                while True:
                    reply=json.loads(replies.readline())
                    if 'event' not in reply:break
                assert 'error' not in reply,reply
                return reply['return']
            def wait_token(token,deadline):
                out=''
                while time.monotonic()<deadline:
                    out=serial.read_text(errors='replace') if serial.exists() else ''
                    if token in out:break
                    if p.poll() is not None:raise AssertionError(f'QEMU exited: {err.read_text()}\n{out}')
                    time.sleep(.05)
                else:raise AssertionError(f'XHCI timeout waiting {token}: {err.read_text()}\n{out}')
                return out
            end=time.monotonic()+90
            if actions:
                wait_token('XHCI READY',end)
                sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor))
                replies=sock.makefile('rb');json.loads(replies.readline())
                call('qmp_capabilities')
                for monitor_command in actions:
                    call('human-monitor-command',{'command-line':monitor_command})
                    time.sleep(.25)
            end=time.monotonic()+90
            out=wait_token('XHCI DONE',end)
            assert re.search(r'XHCI DONE [0-9]+\r?\n',out),out
            # The complete footer avoids partial serial-token races.
            assert 'FAIL' not in out and re.search(r'XHCI DONE 0\r?\n',out),out
            qemu_log=err.read_text()
            if allow_stderr is None:
                assert qemu_log=='',qemu_log
            else:
                assert allow_stderr in qemu_log,(allow_stderr,qemu_log)
            if want_pci:
                if sock is None:
                    sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor))
                    replies=sock.makefile('rb');json.loads(replies.readline())
                    call('qmp_capabilities')
                pci=call('human-monitor-command',{'command-line':'info pci'})
                (d/'pci.txt').write_text(pci)
                # Same BDF/vendor/device as the guest's class-selected function.
                assert 'XHCI BDF 0 2 0 6966 13' in out,out
                assert re.search(r'Bus\s+0, device\s+2, function\s+0:',pci),pci
                assert '1b36:000d' in pci,pci
            return out
        finally:
            p.kill();p.wait(timeout=10)
            if EVIDENCE:
                target=EVIDENCE/(d.parent.name+'-'+d.name);target.mkdir(parents=True,exist_ok=True)
                for name in ('serial','stderr','pci.txt'):
                    if (d/name).exists():shutil.copyfile(d/name,target/name)

def usb(*devices):
    args=['q35','-device','qemu-xhci,id=xhci']
    for device in devices:args+=['-device',f'{device},bus=xhci.0']
    return args

def wrapper(d,name,body,ir):
    source=d/(name+'.holy');source.write_text(body+'\nwhile true:\n  pass\n')
    image=d/(name+'.elf');build(source,image,ir);return image

def negative(d,ir,name,selection,number,want,reason,args):
    body=('import kxhcicheck\nimport kpci\nimport kxhci\n'
          'kxhcicheck.discover()\n'
          f'kxhcicheck.expect("refusal", kxhci.init({selection}, {number}, {want}), false)\n'
          f'kxhcicheck.expect("reason", kxhci.error(), "{reason}")\n'
          'kxhcicheck.expect("not ready", kxhci.ready(), false)\n'
          'kxhcicheck.expect("no event", kxhci.poll(), 0)\n'
          'print "XHCI DONE", kxhcicheck.fails')
    image=wrapper(d,name,body,ir);return boot(d/name,image,args)

KEYS=('sendkey a','sendkey b','sendkey ret')
POINTER=('mouse_move 10 5','mouse_button 1','mouse_button 0')

def uefi_check(d,image):
    modules=Path(os.environ.get('HS_GRUB_EFI_DIR','/usr/lib/grub/x86_64-efi'))
    names=[os.environ['HS_OVMF_CODE']] if os.environ.get('HS_OVMF_CODE') else [
        '/usr/share/OVMF/OVMF_CODE_4M.fd','/usr/share/OVMF/OVMF_CODE.fd']
    code=next((Path(n) for n in names if Path(n).is_file()),None)
    available=code and (modules/'modinfo.sh').is_file() and all(
        shutil.which(p) for p in ('grub-mkimage','mformat','mmd','mcopy','xorriso'))
    if not available:
        if os.environ.get('HS_REQUIRE_UEFI')=='1' or os.environ.get('HS_OVMF_CODE'):
            raise AssertionError('required XHCI UEFI firmware/GRUB tools missing')
        print('skip optional XHCI UEFI boot: firmware/GRUB tools unavailable');return 0
    template=Path(os.environ.get('HS_OVMF_VARS',str(code.with_name(
        'OVMF_VARS_4M.fd' if '4M' in code.name else 'OVMF_VARS.fd'))))
    assert template.is_file(),'matching OVMF variables template missing'
    before_code=hashlib.sha256(code.read_bytes()).digest();before_vars=template.read_bytes()
    variables=d/'OVMF_VARS.fd';variables.write_bytes(before_vars)
    tree=d/'tree';(tree/'boot/grub').mkdir(parents=True)
    shutil.copyfile(image,tree/'boot/kernel.elf')
    # Existing EFI packager requires this file. Empty KRFS, not loaded by GRUB.
    (tree/'boot/ramdisk.krfs').write_bytes(b'KRFS'+bytes(4))
    (tree/'boot/grub/grub.cfg').write_text('set timeout=0\nset default=0\nmenuentry hs {\n multiboot2 /boot/kernel.elf\n boot\n}\n')
    iso=d/'xhci.iso'
    subprocess.run([str(ROOT/'scripts/package-gui-uefi.sh'),str(tree),str(iso)],
                   env=ENV,check=True,capture_output=True,timeout=60)
    out=boot(d/'uefi',iso,usb('usb-kbd','usb-mouse'),True,KEYS,(code,variables))
    assert out.count('\nok ')==25,out
    assert hashlib.sha256(code.read_bytes()).digest()==before_code,'OVMF code changed'
    assert template.read_bytes()==before_vars,'OVMF variables template changed'
    return 1


def main():
    subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=ROOT/'bootstrap',
                   env=ENV,capture_output=True,check=True,timeout=30)
    with tempfile.TemporaryDirectory(prefix='xhci-hid-') as temp:
        d=Path(temp);uefi_boots=0
        for ir in (True,False):
            mode='ir' if ir else 'ast';work=d/mode;work.mkdir()
            source=ROOT/'kernel/kxhcitest.holy';reference=work/'reference.elf';build(source,reference,ir)
            compiler=native_compiler(work,ir);image=native_identity(work,source,reference,compiler,ir)
            out=boot(work/'keyboard',image,usb('usb-kbd','usb-mouse'),True,KEYS)
            assert out.count('\nok ')==25,out
            uefi_boots+=uefi_check(work,image)
            image=wrapper(work,'mouse','import kxhcicheck\nkxhcicheck.run_mouse(6)',ir)
            out=boot(work/'mouse',image,usb('usb-kbd','usb-mouse'),True,POINTER)
            assert out.count('\nok ')==15,out
            image=wrapper(work,'stall','import kxhcicheck\nkxhcicheck.run_stall(5)',ir)
            out=boot(work/'stall',image,usb('usb-kbd'),True,allow_stderr='unknown type 9')
            assert out.count('\nok ')==11,out
            for name,selection,number,want,reason,args in [
                ('bad-index','kpci.count()',1,1,'xHCI selection invalid',usb('usb-kbd')),
                ('bad-kind','kpci.find(6966, 13)',1,9,'USB HID kind invalid',usb('usb-kbd')),
                ('no-controller','-1',1,1,'xHCI selection invalid',['pc']),
                ('wrong-class','kpci.find_class(3, 0)',1,1,'not an xHCI controller',usb('usb-kbd')),
                ('wrong-vendor','kpci.find_class(12, 3)',1,1,'xHCI vendor unsupported',
                 ['q35','-device','nec-usb-xhci,id=xhci','-device','usb-kbd,bus=xhci.0']),
                ('port-range','kpci.find(6966, 13)',31,1,'xHCI port not implemented',usb('usb-kbd')),
                ('empty-port','kpci.find(6966, 13)',3,1,'xHCI port has no device',usb('usb-kbd')),
                ('full-speed','kpci.find(6966, 13)',6,1,'USB HID speed unsupported',
                 usb('usb-kbd','usb-wacom-tablet')),
                ('wrong-device','kpci.find(6966, 13)',6,1,'USB device is not boot keyboard',
                 usb('usb-kbd','usb-mouse')),
            ]:
                negative(work,ir,name,selection,number,want,reason,args)
            print(f'ok XHCI {mode}: native full ELF, keyboard/mouse reports, stall terminal, 9 refusals',flush=True)
    print(f'2/2 XHCI gates ({26+uefi_boots} real QEMU boots, both kernel backends)')

if __name__=='__main__':
    main()
