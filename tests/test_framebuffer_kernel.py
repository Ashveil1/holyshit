#!/usr/bin/env python3
"""Boot actual hs framebuffer through GRUB and check guest screenshot pixels."""
from pathlib import Path
import os,shutil,socket,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
grub=shutil.which('grub-mkrescue')
if not qemu or not grub or not shutil.which('xorriso'):
    print('skip framebuffer boot (QEMU/GRUB/xorriso unavailable; full CI installs all)');sys.exit(0)
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);tree=d/'iso';(tree/'boot/grub').mkdir(parents=True)
    source=ROOT/'kernel/kframebuffer_demo.hs';image=tree/'boot/kernel.elf'
    subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,check=True,capture_output=True,timeout=90)
    # Native hs kernel linker must produce the complete same image.
    driver=d/'compiler';native=d/'native.elf'
    local=dict(env,HSPATH=env['HSPATH']+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
    subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.hs'),str(driver)],env=local,check=True,capture_output=True,timeout=240)
    subprocess.run([str(driver),str(source),str(native)],env=local,check=True,capture_output=True,timeout=90)
    assert native.read_bytes()==image.read_bytes(),'native kernel complete image differs'
    (tree/'boot/grub/grub.cfg').write_text('set timeout=0\nset default=0\ninsmod all_video\nset gfxmode=640x480x32\nset gfxpayload=keep\nterminal_output gfxterm\nmenuentry hs {\n  multiboot2 /boot/kernel.elf\n  boot\n}\n')
    iso=d/'hs.iso';command=[grub]
    if os.environ.get('HS_TEST_GRUB_DIR'):command+=['-d',os.environ['HS_TEST_GRUB_DIR']]
    subprocess.run(command+['-o',str(iso),str(tree)],check=True,capture_output=True,timeout=60)
    serial=d/'serial';monitor=d/'monitor';screen=d/'screen.ppm'
    p=subprocess.Popen([qemu,'-cdrom',str(iso),'-boot','d','-m','256M','-serial','file:'+str(serial),'-display','none','-monitor','unix:'+str(monitor)+',server=on,wait=off'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if serial.exists() and 'FRAMEBUFFER READY 640 480 4' in serial.read_text(errors='replace'):break
            if p.poll() is not None:raise AssertionError('QEMU exited before framebuffer ready')
            time.sleep(.1)
        assert serial.exists() and 'FRAMEBUFFER READY 640 480 4' in serial.read_text(errors='replace'),'no framebuffer ready serial marker'
        sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor));sock.recv(4096);sock.sendall(('screendump '+str(screen)+'\n').encode())
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and (not screen.exists() or screen.stat().st_size<640*480*3):time.sleep(.1)
        sock.close()
        with screen.open('rb') as f:
            assert f.readline().strip()==b'P6';dims=f.readline()
            while dims.startswith(b'#'):dims=f.readline()
            assert dims.strip()==b'640 480';assert f.readline().strip()==b'255';pixels=f.read()
        assert len(pixels)==640*480*3
        def pixel(x,y):return tuple(pixels[(y*640+x)*3:(y*640+x)*3+3])
        for x,y,rgb in [(0,0,(22,50,79)),(60,60,(56,111,164)),(60,110,(232,237,242)),(100,200,(67,170,139)),(300,150,(128,147,167)),(300,330,(56,111,164)),(582,422,(11,23,38))]:
            assert pixel(x,y)==rgb,(x,y,pixel(x,y),rgb)
        if os.environ.get('HS_TEST_SCREENSHOT'):
            shutil.copyfile(screen,os.environ['HS_TEST_SCREENSHOT'])
        print('3/3 framebuffer kernel gates (native image, GRUB boot, actual guest RGB pixels)')
    finally:
        p.kill();p.wait()
