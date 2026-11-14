#!/usr/bin/env python3
"""Boot the ksurface demo through GRUB and check guest pixels across two
flushes: the base scene, then a small dirty rect after a key press. The
second screendump proves the partial flush changed only the dirty region."""
from pathlib import Path
import os,shutil,socket,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
grub=shutil.which('grub-mkrescue')
if not qemu or not grub or not shutil.which('xorriso'):
    print('skip ksurface boot (QEMU/GRUB/xorriso unavailable; full CI installs all)');sys.exit(0)
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel'),HSROOT=str(ROOT))
def monitor_command(monitor,line):
    sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor))
    try:
        sock.recv(4096);sock.sendall((line+'\n').encode());time.sleep(.2)
    finally:
        sock.close()
def screendump(monitor,path,deadline_seconds=5):
    monitor_command(monitor,'screendump '+str(path))
    deadline=time.monotonic()+deadline_seconds
    while time.monotonic()<deadline and (not path.exists() or path.stat().st_size<640*480*3):time.sleep(.1)
    with path.open('rb') as f:
        assert f.readline().strip()==b'P6';dims=f.readline()
        while dims.startswith(b'#'):dims=f.readline()
        assert dims.strip()==b'640 480';assert f.readline().strip()==b'255';pixels=f.read()
    assert len(pixels)==640*480*3
    return pixels
def pixel(pixels,x,y):return tuple(pixels[(y*640+x)*3:(y*640+x)*3+3])
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);tree=d/'iso';(tree/'boot/grub').mkdir(parents=True)
    source=ROOT/'kernel/ksurface_demo.holy';image=tree/'boot/kernel.elf'
    subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,check=True,capture_output=True,timeout=90)
    # Native hs kernel linker must produce the complete same image.
    driver=d/'compiler';native=d/'native.elf'
    local=dict(env,HSPATH=env['HSPATH']+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
    subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)],env=local,check=True,capture_output=True,timeout=240)
    subprocess.run([str(driver),str(source),str(native)],env=local,check=True,capture_output=True,timeout=90)
    assert native.read_bytes()==image.read_bytes(),'native kernel complete image differs'
    (tree/'boot/grub/grub.cfg').write_text('set timeout=0\nset default=0\ninsmod all_video\nset gfxmode=640x480x32\nset gfxpayload=keep\nterminal_output gfxterm\nmenuentry hs {\n  multiboot2 /boot/kernel.elf\n  boot\n}\n')
    iso=d/'hs.iso';command=[grub]
    if os.environ.get('HS_TEST_GRUB_DIR'):command+=['-d',os.environ.get('HS_TEST_GRUB_DIR')]
    subprocess.run(command+['-o',str(iso),str(tree)],check=True,capture_output=True,timeout=60)
    serial=d/'serial';monitor=d/'monitor'
    p=subprocess.Popen([qemu,'-cdrom',str(iso),'-boot','d','-m','256M','-serial','file:'+str(serial),'-display','none','-monitor','unix:'+str(monitor)+',server=on,wait=off'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if serial.exists() and 'SURFACE READY 640 480 4 307200' in serial.read_text(errors='replace'):break
            if p.poll() is not None:raise AssertionError('QEMU exited before surface ready')
            time.sleep(.1)
        text=serial.read_text(errors='replace') if serial.exists() else ''
        assert 'SURFACE READY 640 480 4 307200' in text,'no surface ready serial marker: '+text[-400:]
        first=screendump(monitor,d/'one.ppm')
        # Base scene: background and the panel pixel the second flush will cover.
        assert pixel(first,0,0)==(22,50,79),pixel(first,0,0)
        assert pixel(first,450,320)==(232,237,242),pixel(first,450,320)
        monitor_command(monitor,'sendkey a')
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if 'SURFACE UPDATED 3072' in serial.read_text(errors='replace'):break
            if p.poll() is not None:raise AssertionError('QEMU exited before surface update')
            time.sleep(.1)
        assert 'SURFACE UPDATED 3072' in serial.read_text(errors='replace'),'no partial flush serial marker'
        second=screendump(monitor,d/'two.ppm')
        # Dirty rect landed; untouched pixels kept their bytes.
        assert pixel(second,450,320)==(255,136,0),pixel(second,450,320)
        assert pixel(second,0,0)==(22,50,79),pixel(second,0,0)
        assert pixel(second,10,10)==(22,50,79),pixel(second,10,10)
        assert pixel(second,399,300)==(232,237,242),pixel(second,399,300)
        if os.environ.get('HS_TEST_SCREENSHOT'):
            shutil.copyfile(d/'two.ppm',os.environ['HS_TEST_SCREENSHOT'])
        print('4/4 ksurface gates (native image, GRUB boot, full flush pixels, partial flush pixels)')
    finally:
        p.kill();p.wait()
