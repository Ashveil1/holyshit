#!/usr/bin/env python3
"""Opt-in NVMe on disposable QEMU images, never host devices.

Real q35 PCIe DMA reads, >LBA28/>LBA32 sparse namespace, injected EIO and
throttled timeout. Both kernel backends, native complete ELF parity, PCI
monitor cross-check and before/after allocated-extent disk verification.
"""
from pathlib import Path
import contextlib, errno, hashlib, io, json, os, re, shutil, socket
import subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_xkernel
QEMU=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not QEMU:
    if os.environ.get('HS_REQUIRE_NVME')=='1':raise SystemExit('FAIL required NVMe: QEMU missing')
    print('skip NVMe: QEMU unavailable');sys.exit(0)
ENV=dict(os.environ,HSPATH=':'.join(str(ROOT/p) for p in ('','kernel','selfhost','selfhost/be')),HSROOT=str(ROOT))
os.environ['HSPATH']=ENV['HSPATH']
EVIDENCE=Path(os.environ['HS_NVME_EVIDENCE']) if os.environ.get('HS_NVME_EVIDENCE') else None
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

def boot(d,image,args,want_pci=False,firmware=None,allow_stderr=()):
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
                if re.search(r'NVME DONE [0-9]+\r?\n',out):break
                if p.poll() is not None:raise AssertionError(f'QEMU exited: {err.read_text()}\n{out}')
                time.sleep(.05)
            else:raise AssertionError(f'NVMe timeout: {err.read_text()}\n{out}')
            assert 'FAIL' not in out and re.search(r'NVME DONE 0\r?\n',out),out
            noise=err.read_text()
            for line in allow_stderr:noise=noise.replace(line,'')
            assert noise=='',noise
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
                        guest=re.search(r'NVME BDF (\d+) (\d+) (\d+) (\d+) (\d+)',out)
                        assert guest,out
                        bus,dev,fn,vendor,device=map(int,guest.groups())
                        assert (vendor,device)==(6966,16),(vendor,device)
                        assert re.search(rf'Bus\s+{bus}, device\s+{dev}, function\s+{fn}:',pci),pci
                        assert '1b36:0010' in pci,pci
            return out
        finally:
            p.kill();p.wait(timeout=10)
            if EVIDENCE:
                target=EVIDENCE/(d.parent.name+'-'+d.name);target.mkdir(parents=True,exist_ok=True)
                for name in ('serial','stderr','pci.txt'):
                    if (d/name).exists():shutil.copyfile(d/name,target/name)

def drive(path,extra=''):
    return ['-drive',f'id=nvm0,if=none,format=raw,file={path}'+extra,
            '-device','nvme,drive=nvm0,serial=hsnvme']

def wrapper(d,name,body,ir):
    source=d/(name+'.holy');source.write_text(body+'\nwhile true:\n  pass\n')
    image=d/(name+'.elf');build(source,image,ir);return image

def negative(d,ir,name,selection,reason,args,issued=0):
    body=('import knvmecheck\nimport kpci\nimport knvme\n'
          'knvmecheck.discover()\n'
          f'knvmecheck.expect("refusal", knvme.init({selection}), false)\n'
          f'knvmecheck.expect("reason", knvme.error(), "{reason}")\n'
          'knvmecheck.expect("not ready", knvme.ready(), false)\n'
          f'knvmecheck.expect("no command", knvme.commands(), {issued})\n'
          'knvmecheck.expect("no data", knvme.byte_at(0), -1)\n'
          'knvmecheck.expect("no read", knvme.read(0, 1), false)\n'
          'print "NVME DONE", knvmecheck.fails')
    image=wrapper(d,name,body,ir);return boot(d/name,image,args)

def fault(d,ir,name,args,throttled=False):
    # A full token bucket lets the first disk read overdraw and succeed; a
    # throttled drive only fails the read after the burst is drained. NVMe
    # IDENTIFY is controller-local, so unlike ATA/AHCI it never touches media.
    burst=('knvmecheck.expect("burst drain", knvme.read(0, 1), true)\n' if throttled else '')
    reads=6 if throttled else 5
    body=('import knvmecheck\nimport knvme\n'
          'idx = knvmecheck.discover()\n'
          'knvmecheck.expect("init", knvme.init(idx), true)\n'
          'knvmecheck.guard_set()\n'
          + burst +
          'knvmecheck.expect("failed read", knvme.read(13, 1), false)\n'
          'knvmecheck.expect("reason", knvme.error(), "NVMe read failed")\n'
          'knvmecheck.expect("not ready", knvme.ready(), false)\n'
          'knvmecheck.expect("no capacity", knvme.sectors(), 0)\n'
          'knvmecheck.expect("no data", knvme.byte_at(0), -1)\n'
          'before = knvme.commands()\n'
          f'knvmecheck.expect("identifies, queues and reads only", before, {reads})\n'
          'knvmecheck.expect("no retry", knvme.read(0, 1), false)\n'
          'knvmecheck.expect("no reinit", knvme.init(idx), false)\n'
          'knvmecheck.expect("no new command", knvme.commands(), before)\n'
          'knvmecheck.expect("DMA guards", knvmecheck.guards(), true)\n'
          'print "NVME DONE", knvmecheck.fails')
    noise=('qemu-system-x86_64: aio failed: Input/output error\n',) if 'blkdebug' in args[-3] else ()
    image=wrapper(d,name,body,ir);return boot(d/name,image,args,True,allow_stderr=noise)

def uefi_check(d,image,disk):
    modules=Path(os.environ.get('HS_GRUB_EFI_DIR','/usr/lib/grub/x86_64-efi'))
    names=[os.environ['HS_OVMF_CODE']] if os.environ.get('HS_OVMF_CODE') else [
        '/usr/share/OVMF/OVMF_CODE_4M.fd','/usr/share/OVMF/OVMF_CODE.fd']
    code=next((Path(n) for n in names if Path(n).is_file()),None)
    available=code and (modules/'modinfo.sh').is_file() and all(
        shutil.which(p) for p in ('grub-mkimage','mformat','mmd','mcopy','xorriso'))
    if not available:
        if os.environ.get('HS_REQUIRE_UEFI')=='1' or os.environ.get('HS_OVMF_CODE'):
            raise AssertionError('required NVMe UEFI firmware/GRUB tools missing')
        print('skip optional NVMe UEFI boot: firmware/GRUB tools unavailable');return 0
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
    iso=d/'nvme.iso'
    subprocess.run([str(ROOT/'scripts/package-gui-uefi.sh'),str(tree),str(iso)],
                   env=ENV,check=True,capture_output=True,timeout=60)
    out=boot(d/'uefi',iso,['q35']+drive(disk),True,(code,variables))
    assert out.count('\nok ')==30,out
    assert hashlib.sha256(code.read_bytes()).digest()==before_code,'OVMF code changed'
    assert template.read_bytes()==before_vars,'OVMF variables template changed'
    return 1

def main():
    subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=ROOT/'bootstrap',
                   env=ENV,capture_output=True,check=True,timeout=30)
    with tempfile.TemporaryDirectory(prefix='nvme-readonly-') as temp:
        d=Path(temp);disk=d/'nvm.img';disk_image(disk,65536);before=disk_state(disk)
        sparse=d/'large.img';large=4295032832;disk_image(sparse,large);large_before=disk_state(sparse)
        # blkdebug sits below raw; a selected byte-sector read returns EIO.
        injection=d/'error.conf';injection.write_text('[inject-error]\nevent = "read_aio"\nerrno = "5"\nsector = "13"\nonce = "on"\nimmediately = "on"\n')
        uefi_boots=0
        for ir in (True,False):
            mode='ir' if ir else 'ast';work=d/mode;work.mkdir()
            source=ROOT/'kernel/knvmetest.holy';reference=work/'reference.elf';build(source,reference,ir)
            compiler=native_compiler(work,ir);image=native_identity(work,source,reference,compiler,ir)
            out=boot(work/'normal',image,['q35']+drive(disk),True)
            assert out.count('\nok ')==30,out
            uefi_boots+=uefi_check(work,image,disk)
            image=wrapper(work,'large',f'import knvmecheck\nknvmecheck.run(0, {large})',ir)
            out=boot(work/'large',image,['q35']+drive(sparse),True)
            assert out.count('\nok ')==28,out
            for name,selection,reason,args,issued in [
                ('no-controller','kpci.find_class(1, 8)','NVMe selection invalid',['pc'],0),
                ('bad-index','kpci.count()','NVMe selection invalid',['q35'],0),
                ('wrong-class','kpci.find_class(3, 0)','not an NVMe controller',['q35'],0),
                ('sector-size','kpci.find_class(1, 8)','NVMe sector size unsupported',
                 ['q35','-drive',f'id=nvm1,if=none,format=raw,file={disk}',
                  '-device','nvme,drive=nvm1,serial=hsnvme4k,logical_block_size=4096,physical_block_size=4096'],2),
            ]:
                negative(work,ir,name,selection,reason,args,issued)
            fault(work,ir,'io-error',['q35']+drive('blkdebug:'+str(injection)+':'+str(disk)))
            fault(work,ir,'timeout',['q35']+drive(disk,extra=',throttling.bps-read=1'),True)
            assert disk_state(disk)==before,'NVMe test changed dense disk bytes, extents or mtime'
            after=disk_state(sparse)
            assert after==large_before,('NVMe changed sparse disk state',large_before,after)
            print(f'ok NVMe {mode}: native full ELF, high LBA, 4 refusals, EIO, timeout, immutable disks',flush=True)
        if EVIDENCE:
            (EVIDENCE/'disks.json').write_text(json.dumps({'dense':before,'sparse':large_before},indent=2))
    print(f'2/2 NVMe read-only gates ({16+uefi_boots} real QEMU boots, both kernel backends)')

if __name__=='__main__':main()
