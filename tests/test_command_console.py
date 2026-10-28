#!/usr/bin/env python3
"""Separate command console: actual PS/2 commands and complete result pixels."""
from pathlib import Path
import os,shutil,socket,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
grub=shutil.which('grub-mkrescue')
if not qemu or not grub or not shutil.which('xorriso'):
    if os.environ.get('HS_REQUIRE_GUI') == '1':
        print('FAIL required framebuffer boot: QEMU/GRUB/xorriso unavailable');sys.exit(1)
    print('skip framebuffer boot (QEMU/GRUB/xorriso unavailable; optional local dependencies)');sys.exit(0)
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel'),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);tree=d/'iso';(tree/'boot/grub').mkdir(parents=True)
    source=ROOT/'kernel/kcommand_console.holy';image=tree/'boot/kernel.elf'
    subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,check=True,capture_output=True,timeout=90)
    # Native hs kernel linker must produce the complete same image.
    driver=d/'compiler';native=d/'native.elf'
    local=dict(env,HSPATH=env['HSPATH']+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'))
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/kernel_ir.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)])
    subprocess.run(build,env=local,check=True,capture_output=True,timeout=240)
    subprocess.run([str(driver),str(source),str(native)],env=local,check=True,capture_output=True,timeout=90)
    assert native.read_bytes()==image.read_bytes(),'native kernel complete image differs'
    (tree/'boot/grub/grub.cfg').write_text('serial --unit=0 --speed=38400\nterminal_output console serial\necho HS_GRUB_CONFIG_START\nset timeout=0\nset default=0\ninsmod all_video\nset gfxmode=640x480x32\nset gfxpayload=keep\nterminal_output gfxterm serial\necho HS_GRUB_LOADING_KERNEL\nmultiboot2 /boot/kernel.elf\necho HS_GRUB_LOAD_STATUS=$?\nboot\necho HS_GRUB_BOOT_RETURNED=$?\n')
    iso=d/'hs.iso';command=[grub]
    if os.environ.get('HS_TEST_GRUB_DIR'):command+=['-d',os.environ['HS_TEST_GRUB_DIR']]
    rescue=subprocess.run(command+['-o',str(iso),str(tree)],capture_output=True,timeout=60)
    if rescue.returncode:
        raise AssertionError('grub-mkrescue failed: '+rescue.stderr.decode(errors='replace')[-4000:])
    serial=d/'serial';monitor=d/'monitor';screen=d/'screen.ppm'
    qerr=d/'qemu.stderr'
    qerrfile=qerr.open('wb')
    p=subprocess.Popen([qemu,'-cdrom',str(iso),'-boot','d','-m','256M','-serial','file:'+str(serial),'-display','none','-nic','none','-monitor','unix:'+str(monitor)+',server=on,wait=off'],stdout=subprocess.DEVNULL,stderr=qerrfile)
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if serial.exists() and 'COMMAND CONSOLE READY' in serial.read_text(errors='replace'):break
            if p.poll() is not None:raise AssertionError('QEMU exited before command console ready: '+qerr.read_text(errors='replace'))
            time.sleep(.1)
        assert serial.exists() and 'COMMAND CONSOLE READY' in serial.read_text(errors='replace'),'no command ready: '+(serial.read_text(errors='replace') if serial.exists() else '')
        sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor));sock.recv(4096)
        def monitor_command(value):
            sock.sendall((value+'\n').encode())
            reply=b''
            while b'(qemu)' not in reply:reply+=sock.recv(4096)
            assert b'Error' not in reply,reply
            return reply
        edits=results=0
        def command(text):
            global edits,results
            for key in [*text,'ret']:
                name='spc' if key==' ' else key
                monitor_command('sendkey '+name)
                edits+=1
                if key=='ret':results+=1
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    data=serial.read_text(errors='replace')
                    if data.count('COMMAND EDIT')>=edits and data.count('COMMAND RESULT')>=results:break
                    time.sleep(.05)
                else:raise AssertionError('key stalled '+key+' '+data[-500:])
        def capture(name):
            screen.unlink(missing_ok=True)
            monitor_command('screendump '+str(screen))
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and (not screen.exists() or screen.stat().st_size<640*480*3):time.sleep(.05)
            with screen.open('rb') as f:
                assert f.readline().strip()==b'P6'
                dims=f.readline()
                while dims.startswith(b'#'):dims=f.readline()
                assert dims.strip()==b'640 480' and f.readline().strip()==b'255'
                raw=f.read()
            assert len(raw)==640*480*3
            evidence=os.environ.get('HS_GUI_EVIDENCE')
            if evidence:
                Path(evidence).mkdir(parents=True,exist_ok=True)
                shutil.copyfile(screen,Path(evidence)/(name+'.ppm'))
            return raw
        # Independent literal glyphs, not the font module under test.
        glyphs={
            ' ': [0,0,0,0,0,0,0],
            'A': [14,17,17,31,17,17,17], 'C':[15,16,16,16,16,16,15],
            'D':[30,17,17,17,17,17,30], 'E':[31,16,16,30,16,16,31],
            'H':[17,17,17,31,17,17,17], 'K':[17,18,20,24,20,18,17],
            'L':[16,16,16,16,16,16,31], 'M':[17,27,21,21,17,17,17],
            'N':[17,25,21,19,17,17,17], 'O':[14,17,17,17,17,17,14],
            'P':[30,17,17,30,16,16,16], 'U':[17,17,17,17,17,17,14],
            'W':[17,17,17,21,21,27,17],
        }
        def result_pixels(raw,text):
            for y in range(16):
                for x in range(512):
                    cell=x//12;col=(x%12)//2;row=y//2
                    lit=cell<len(text) and col<5 and row<7 and bool(glyphs[text[cell]][row] & (1<<(4-col)))
                    want=(22,50,79) if lit else (232,237,242)
                    offset=((352+y)*640+32+x)*3
                    assert tuple(raw[offset:offset+3])==want,('result pixel',text,x,y)
        command('help');result_pixels(capture('help'),'HELP ECHO')
        command('echo ok');result_pixels(capture('echo'),'OK')
        command('nope');result_pixels(capture('unknown'),'UNKNOWN COMMAND')
        command('');result_pixels(capture('empty'),'')
        command('echo ac');result_pixels(capture('final'),'AC')
        data=serial.read_text(errors='replace')
        assert [line for line in data.splitlines() if line.startswith('COMMAND RESULT')]==[
            'COMMAND RESULT 1 9','COMMAND RESULT 2 2','COMMAND RESULT 3 15','COMMAND RESULT 0 0','COMMAND RESULT 2 2'],data
        print('command console gates passed (native image, GRUB/PS2, help/echo/unknown/empty, independent full-row pixels)')
    finally:
        evidence=os.environ.get('HS_GUI_EVIDENCE')
        if evidence:
            Path(evidence).mkdir(parents=True,exist_ok=True)
            if serial.exists():shutil.copyfile(serial,Path(evidence)/'serial.txt')
            shutil.copyfile(qerr,Path(evidence)/'qemu.stderr')
        p.kill();p.wait();qerrfile.close()
