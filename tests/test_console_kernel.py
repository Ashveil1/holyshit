#!/usr/bin/env python3
"""Boot actual hs framebuffer through GRUB and check guest screenshot pixels."""
from pathlib import Path
import os,shutil,socket,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
grub=shutil.which('grub-mkrescue')
if not qemu or not grub or not shutil.which('xorriso'):
    print('skip framebuffer boot (QEMU/GRUB/xorriso unavailable; optional local dependencies)');sys.exit(0)
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);tree=d/'iso';(tree/'boot/grub').mkdir(parents=True)
    source=ROOT/'kernel/kconsole_demo.holy';image=tree/'boot/kernel.elf'
    subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,check=True,capture_output=True,timeout=90)
    # Native hs kernel linker must produce the complete same image.
    driver=d/'compiler';native=d/'native.elf'
    local=dict(env,HSPATH=env['HSPATH']+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
    subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)],env=local,check=True,capture_output=True,timeout=240)
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
            if serial.exists() and 'CONSOLE READY' in serial.read_text(errors='replace'):break
            if p.poll() is not None:raise AssertionError('QEMU exited before framebuffer ready')
            time.sleep(.1)
        assert serial.exists() and 'CONSOLE READY' in serial.read_text(errors='replace'),'no framebuffer ready serial marker'
        sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor));sock.recv(4096)
        for key in ['a','b','backspace','c','ret']:
            sock.sendall(('sendkey '+key+'\n').encode());sock.recv(4096)
            deadline=time.monotonic()+15
            # Poll the actual ready markers after each edit before another key.
            expected={'a':'CONSOLE EDIT 1','b':'CONSOLE EDIT 2','backspace':'CONSOLE EDIT 1','c':'CONSOLE EDIT 2','ret':'CONSOLE SUBMITTED ac'}[key]
            # Count transitions, not just a substring left from an earlier edit.
            target=['a','b','backspace','c','ret'].index(key)+1
            while time.monotonic()<deadline:
                content=serial.read_text(errors='replace')
                if (key=='ret' and expected in content) or (key!='ret' and content.count('CONSOLE EDIT')>=target):break
                time.sleep(.1)
            else:raise AssertionError('edit did not finish: '+key+' '+content[-300:])
        sock.sendall(('screendump '+str(screen)+'\n').encode())
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and (not screen.exists() or screen.stat().st_size<640*480*3):time.sleep(.1)
        sock.close()
        with screen.open('rb') as f:
            assert f.readline().strip()==b'P6';dims=f.readline()
            while dims.startswith(b'#'):dims=f.readline()
            assert dims.strip()==b'640 480';assert f.readline().strip()==b'255';pixels=f.read()
        assert len(pixels)==640*480*3
        def pixel(x,y):return tuple(pixels[(y*640+x)*3:(y*640+x)*3+3])
        assert pixel(0,0)==(22,50,79)
        # Independent A/C bitmaps at x32/y144, scale2; backspace removed B.
        for index,rows in enumerate([[14,17,17,31,17,17,17],[15,16,16,16,16,16,15]]):
            for row,bits in enumerate(rows):
                for col in range(6):
                    want=(22,50,79) if col<5 and bits & (1<<(4-col)) else (232,237,242)
                    for dy in range(2):
                        for dx in range(2):
                            assert pixel(32+index*12+col*2+dx,144+row*2+dy)==want,(index,row,col)
        if os.environ.get('HS_TEST_SCREENSHOT'):
            shutil.copyfile(screen,os.environ['HS_TEST_SCREENSHOT'])
        print('4/4 console kernel gates (native image, GRUB boot, keyboard edits, actual text pixels)')
    finally:
        p.kill();p.wait()
