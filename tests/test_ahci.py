#!/usr/bin/env python3
"""Opt-in AHCI on disposable QEMU SATA images, never host devices.

Real q35/ICH9 DMA reads, nonzero port, >LBA28/>LBA32 sparse disk, task-file
error and throttled timeout. Both kernel backends, native complete ELF parity,
PCI monitor cross-check and before/after allocated-extent disk verification.
"""
from pathlib import Path
import contextlib, errno, hashlib, io, json, os, re, shutil, socket
import subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_xkernel
QEMU=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not QEMU:
    if os.environ.get('HS_REQUIRE_AHCI')=='1':raise SystemExit('FAIL required AHCI: QEMU missing')
    print('skip AHCI: QEMU unavailable');sys.exit(0)
ENV=dict(os.environ,HSPATH=':'.join(str(ROOT/p) for p in ('','kernel','selfhost','selfhost/be')),HSROOT=str(ROOT))
os.environ['HSPATH']=ENV['HSPATH']
EVIDENCE=Path(os.environ['HS_AHCI_EVIDENCE']) if os.environ.get('HS_AHCI_EVIDENCE') else None
BASES={low:bytes((low*17+i*7+(i//251)*31)&255 for i in range(512)) for low in range(256)}

def sector(lba):
    data=bytearray(BASES[lba&255]);data[:6]=lba.to_bytes(6,'little');return data

def disk_image(path,count):
    with path.open('wb') as f:
        f.truncate(count*512)
        if count==65536:
            for lba in range(count):f.write(sector(lba))
        else:
            # Sparse raw disk. Six-byte per-sector identity prevents a driver
            # that drops high LBA bits from passing with a periodic pattern.
            ranges=[(0,1),(4,8),(13,2),(32767,3),(count-8,8),
                    (268435455,3),(4294967295,3)]
            for start,n in ranges:
                f.seek(start*512)
                for lba in range(start,start+n):f.write(sector(lba))
        f.flush();os.fsync(f.fileno())

def disk_state(path):
    """Audit every allocated byte plus every hole boundary, even at 2TiB.

    Extent/mtime/size identity also rejects same-byte and zero-to-hole writes.
    Unlike hashing only selected sectors, this covers the entire sparse image.
    """
    stat=path.stat();extents=[];h=hashlib.sha256()
    with path.open('rb',buffering=0) as f:
        pos=0
        while pos<stat.st_size:
            try:start=os.lseek(f.fileno(),pos,os.SEEK_DATA)
            except OSError as e:
                if e.errno==errno.ENXIO:break
                raise
            stop=min(os.lseek(f.fileno(),start,os.SEEK_HOLE),stat.st_size)
            extents.append((start,stop));h.update(f'{start}:{stop}:'.encode())
            f.seek(start);left=stop-start
            while left:
                data=f.read(min(left,1024*1024));assert data
                h.update(data);left-=len(data)
            pos=stop
    return {'size':stat.st_size,'blocks':stat.st_blocks,'mtime_ns':stat.st_mtime_ns,
            'extents':extents,'sha256':h.hexdigest()}

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
    # The local QMP file object is used for complete newline-delimited replies.

def boot(d,image,args,want_pci=False,firmware=None):
    d.mkdir();serial=d/'serial';err=d/'stderr';monitor=d/'qmp'
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
            end=time.monotonic()+60
            while time.monotonic()<end:
                out=serial.read_text(errors='replace') if serial.exists() else ''
                # The complete footer avoids partial serial-token races.
                if re.search(r'AHCI DONE [0-9]+\r?\n',out):break
                if p.poll() is not None:raise AssertionError(f'QEMU exited: {err.read_text()}\n{out}')
                time.sleep(.05)
            else:raise AssertionError(f'AHCI timeout: {err.read_text()}\n{out}')
            assert 'FAIL' not in out and re.search(r'AHCI DONE 0\r?\n',out),out
            assert err.read_text()=='',err.read_text()
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(5);sock.connect(str(monitor))
                with sock.makefile('rb') as replies:
                    json.loads(replies.readline())
                    def call(name,arguments=None):
                        qmp(sock,name,arguments)
                        while True:
                            reply=json.loads(replies.readline())
                            if 'event' not in reply:break
                        assert 'error' not in reply,reply
                        return reply['return']
                    call('qmp_capabilities')
                    pci=call('human-monitor-command',{'command-line':'info pci'})
                    (d/'pci.txt').write_text(pci)
                    if want_pci:
                        # Same BDF/vendor/device as the guest's class-selected function.
                        assert 'AHCI BDF 0 31 2 32902 10530' in out,out
                        assert re.search(r'Bus\s+0, device\s+31, function\s+2:',pci),pci
                        assert '8086:2922' in pci,pci
            return out
        finally:
            p.kill();p.wait(timeout=10)
            if EVIDENCE:
                target=EVIDENCE/(d.parent.name+'-'+d.name);target.mkdir(parents=True,exist_ok=True)
                for name in ('serial','stderr','pci.txt'):
                    if (d/name).exists():shutil.copyfile(d/name,target/name)

def drive(path,port=0,extra=''):
    return ['-drive',f'id=sata0,if=none,format=raw,file={path}'+extra,
            '-device',f'ide-hd,drive=sata0,bus=ide.{port}']

def wrapper(d,name,body,ir):
    source=d/(name+'.holy');source.write_text(body+'\nwhile true:\n  pass\n')
    image=d/(name+'.elf');build(source,image,ir);return image

def negative(d,ir,name,selection,number,reason,args):
    body=('import kahcicheck\nimport kpci\nimport kahci\n'
          'kahcicheck.discover()\n'
          f'kahcicheck.expect("refusal", kahci.init({selection}, {number}), false)\n'
          f'kahcicheck.expect("reason", kahci.error(), "{reason}")\n'
          'kahcicheck.expect("not ready", kahci.ready(), false)\n'
          'kahcicheck.expect("no command", kahci.commands(), 0)\n'
          'kahcicheck.expect("no data", kahci.byte_at(0), -1)\n'
          'kahcicheck.expect("no read", kahci.read(0, 1), false)\n'
          'print "AHCI DONE", kahcicheck.fails')
    image=wrapper(d,name,body,ir);return boot(d/name,image,args)

def fault(d,ir,name,args,reason):
    body=('import kahcicheck\nimport kahci\n'
          'idx = kahcicheck.discover()\n'
          'kahcicheck.expect("init", kahci.init(idx, 0), true)\n'
          'kahcicheck.guard_set()\n'
          'kahcicheck.expect("failed read", kahci.read(13, 1), false)\n'
          f'kahcicheck.expect("reason", kahci.error(), "{reason}")\n'
          'kahcicheck.expect("not ready", kahci.ready(), false)\n'
          'kahcicheck.expect("bus master disabled", kahci.config(4) & 4, 0)\n'
          'kahcicheck.expect("no capacity", kahci.sectors(), 0)\n'
          'kahcicheck.expect("no data", kahci.byte_at(0), -1)\n'
          'before = kahci.commands()\n'
          'kahcicheck.expect("identify and failed read only", before, 2)\n'
          'kahcicheck.expect("no retry", kahci.read(0, 1), false)\n'
          'kahcicheck.expect("no reinit", kahci.init(idx, 0), false)\n'
          'kahcicheck.expect("no new command", kahci.commands(), before)\n'
          'kahcicheck.expect("DMA guards", kahcicheck.guards(), true)\n'
          'print "AHCI DONE", kahcicheck.fails')
    image=wrapper(d,name,body,ir);return boot(d/name,image,args,True)

def uefi_check(d,image,disk):
    modules=Path(os.environ.get('HS_GRUB_EFI_DIR','/usr/lib/grub/x86_64-efi'))
    names=[os.environ['HS_OVMF_CODE']] if os.environ.get('HS_OVMF_CODE') else [
        '/usr/share/OVMF/OVMF_CODE_4M.fd','/usr/share/OVMF/OVMF_CODE.fd']
    code=next((Path(n) for n in names if Path(n).is_file()),None)
    available=code and (modules/'modinfo.sh').is_file() and all(
        shutil.which(p) for p in ('grub-mkimage','mformat','mmd','mcopy','xorriso'))
    if not available:
        if os.environ.get('HS_REQUIRE_UEFI')=='1' or os.environ.get('HS_OVMF_CODE'):
            raise AssertionError('required AHCI UEFI firmware/GRUB tools missing')
        print('skip optional AHCI UEFI boot: firmware/GRUB tools unavailable');return 0
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
    iso=d/'ahci.iso'
    subprocess.run([str(ROOT/'scripts/package-gui-uefi.sh'),str(tree),str(iso)],
                   env=ENV,check=True,capture_output=True,timeout=60)
    out=boot(d/'uefi',iso,['q35']+drive(disk),True,(code,variables))
    assert out.count('\nok ')==31,out
    assert hashlib.sha256(code.read_bytes()).digest()==before_code,'OVMF code changed'
    assert template.read_bytes()==before_vars,'OVMF variables template changed'
    return 1

def main():
    subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=ROOT/'bootstrap',
                   env=ENV,capture_output=True,check=True,timeout=30)
    with tempfile.TemporaryDirectory(prefix='ahci-readonly-') as temp:
        d=Path(temp);disk=d/'sata.img';disk_image(disk,65536);before=disk_state(disk)
        sparse=d/'large.img';large=4295032832;disk_image(sparse,large);large_before=disk_state(sparse)
        empty=d/'empty.iso';empty.write_bytes(bytes(2048*32))
        # blkdebug sits below raw; a selected byte-sector read returns EIO.
        injection=d/'error.conf';injection.write_text('[inject-error]\nevent = "read_aio"\nerrno = "5"\nsector = "13"\nonce = "on"\nimmediately = "on"\n')
        uefi_boots=0
        for ir in (True,False):
            mode='ir' if ir else 'ast';work=d/mode;work.mkdir()
            source=ROOT/'kernel/kahcitest.holy';reference=work/'reference.elf';build(source,reference,ir)
            compiler=native_compiler(work,ir);image=native_identity(work,source,reference,compiler,ir)
            out=boot(work/'normal',image,['q35']+drive(disk),True)
            assert out.count('\nok ')==31,out
            uefi_boots+=uefi_check(work,image,disk)
            for port in (4,):
                image=wrapper(work,'port4',f'import kahcicheck\nkahcicheck.run({port}, 65536)',ir)
                boot(work/'port4',image,['q35']+drive(disk,port),True)
            image=wrapper(work,'large',f'import kahcicheck\nkahcicheck.run(0, {large})',ir)
            out=boot(work/'large',image,['q35']+drive(sparse),True)
            assert out.count('\nok ')==29,out
            for name,selection,number,reason,args in [
                ('no-controller','kpci.find_class(1, 6)',0,'AHCI selection invalid',['pc']),
                ('bad-index','kpci.count()',0,'AHCI selection invalid',['q35']),
                ('wrong-class','kpci.find_class(3, 0)',0,'not an AHCI controller',['q35']),
                ('negative-port','kpci.find_class(1, 6)',-1,'AHCI selection invalid',['q35']),
                ('out-of-range-port','kpci.find_class(1, 6)',32,'AHCI selection invalid',['q35']),
                ('unimplemented','kpci.find_class(1, 6)',31,'AHCI port not implemented',['q35']),
                ('empty-port','kpci.find_class(1, 6)',0,'AHCI port not active',['q35']),
                ('atapi','kpci.find_class(1, 6)',0,'AHCI device is not SATA disk',
                 ['q35','-drive',f'id=cd0,if=none,format=raw,file={empty},media=cdrom',
                  '-device','ide-cd,drive=cd0,bus=ide.0']),
            ]:
                negative(work,ir,name,selection,number,reason,args)
            fault(work,ir,'io-error',['q35']+drive('blkdebug:'+str(injection)+':'+str(disk)),
                  'AHCI command error')
            fault(work,ir,'timeout',['q35']+drive(disk,extra=',throttling.bps-read=1'),
                  'AHCI command timeout')
            assert disk_state(disk)==before,'AHCI test changed dense disk bytes, extents or mtime'
            after=disk_state(sparse)
            assert after==large_before,('AHCI changed sparse disk state',large_before,after)
            print(f'ok AHCI {mode}: native full ELF, SATA port0/4, high LBA, 8 refusals, EIO, timeout, immutable disks',flush=True)
        if EVIDENCE:
            (EVIDENCE/'disks.json').write_text(json.dumps({'dense':before,'sparse':large_before},indent=2))
    print(f'2/2 AHCI read-only gates ({26+uefi_boots} real QEMU boots, both kernel backends)')

if __name__=='__main__':main()
