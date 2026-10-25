#!/usr/bin/env python3
"""Fixed buffer/raw renderer console: real GRUB keyboard, text pixels and native image."""
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
    # Test-only markers surround real PS/2 dequeue, storage, redraw and serial
    # diagnostics for the first16 events. Both compilers see this same source.
    source=d/'session.holy';image=tree/'boot/kernel.elf'
    instrumented=(ROOT/'kernel/kconsole_fixed.holy').read_text()
    instrumented=instrumented.replace('print "FIXED SESSION READY"',
        'def mark():\n  unsafe:\n    return as_int(alloc(1))\n'
        'event_label = "ORDERED EVENT"\nsession_before = mark()\nsession_events = 0\nprint "FIXED SESSION READY"')
    instrumented += ('    session_events = session_events + 1\n'
                     '    if session_events == 16:\n'
                     '      session_after = mark()\n'
                     '      print "FIXED SESSION GAP", session_after - session_before\n'
                     '      steady_before = mark()\n'
                     '    if session_events == 272:\n'
                     '      steady_after = mark()\n'
                     '      print "FIXED STEADY GAP", steady_after - steady_before\n')
    instrumented=instrumented.replace('while true:\n  key = readkey_code()',
        'while true:\n  event = readkey_event()\n'
        '  if event != null:\n    print event_label, event\n'
        '  navigation = readkey_nav()\n'
        '  if navigation != null:\n    print "NAV EVENT", navigation\n'
        '  key = readkey_code()')
    source.write_text(instrumented)
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
    p=subprocess.Popen([qemu,'-cdrom',str(iso),'-boot','d','-m','256M','-serial','file:'+str(serial),'-display','none','-monitor','unix:'+str(monitor)+',server=on,wait=off'],stdout=subprocess.DEVNULL,stderr=qerrfile)
    try:
        # This fixture boots the kernel directly from GRUB config, with no
        # menu or injected boot keys. Keyboard injection starts only in hs.
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if serial.exists() and 'FIXED SESSION READY' in serial.read_text(errors='replace'):break
            if p.poll() is not None:raise AssertionError('QEMU exited before framebuffer ready')
            time.sleep(.1)
        if not serial.exists() or 'FIXED SESSION READY' not in serial.read_text(errors='replace'):
            evidence=os.environ.get('HS_GUI_EVIDENCE')
            if evidence:
                evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=True)
                if serial.exists():shutil.copyfile(serial,evidence/'serial.txt')
                shutil.copyfile(qerr,evidence/'qemu.stderr')
                try:
                    diagnostic=socket.socket(socket.AF_UNIX);diagnostic.settimeout(5)
                    diagnostic.connect(str(monitor));diagnostic.recv(4096)
                    diagnostic.sendall(('screendump '+str(evidence/'boot-failure.ppm')+'\n').encode())
                    time.sleep(1);diagnostic.close()
                except OSError as error:print('boot screenshot unavailable:',error)
            raise AssertionError('no framebuffer ready serial marker; serial='+
                                 (serial.read_text(errors='replace')[-2000:] if serial.exists() else '<absent>')+
                                 '; qemu='+qerr.read_text(errors='replace')[-2000:])
        sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor));sock.recv(4096)
        def cursor_at(column):
            screen.unlink(missing_ok=True)
            sock.sendall(('screendump '+str(screen)+'\n').encode())
            # Wait for the complete monitor command before reading the file.
            reply=b''
            while b'(qemu)' not in reply:
                reply+=sock.recv(4096)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and (not screen.exists() or screen.stat().st_size<640*480*3):time.sleep(.05)
            with screen.open('rb') as f:
                assert f.readline().strip()==b'P6'
                dims=f.readline()
                while dims.startswith(b'#'):dims=f.readline()
                assert dims.strip()==b'640 480'
                assert f.readline().strip()==b'255'
                raw=f.read()
            assert len(raw)==640*480*3
            for y in (294,295):
                for x in range(32,548):
                    offset=(y*640+x)*3
                    ink=(180,35,24) if column==42 else (22,50,79)
                    want=ink if 32+column*12<=x<40+column*12 else (232,237,242)
                    assert tuple(raw[offset:offset+3])==want,('cursor',column,x,y)
        cursor_at(0)
        # Six submissions overflow the four-line transcript; seventh stays editable.
        keys=['a','b','backspace','c','ret','b','ret','c','ret','d','ret','e','ret','f','ret','g']
        submits=edits=0
        for key in keys:
            sock.sendall(('sendkey '+key+'\n').encode());reply=sock.recv(4096)
            assert b'error' not in reply.lower(),reply
            if key=='ret':submits+=1
            else:edits+=1
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                content=serial.read_text(errors='replace')
                if content.count('FIXED SUBMITTED')>=submits and content.count('FIXED EDIT')>=edits:break
                time.sleep(.1)
            else:raise AssertionError('session edit stalled '+key+' '+content[-300:])
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            content=serial.read_text(errors='replace')
            if 'FIXED SESSION GAP ' in content:break
            time.sleep(.1)
        # Finite end-to-end budget, not the renderer-only allocation proof:
        # includes READY (48 bytes) and the marker (16 bytes), while retained
        # diagnostic labels are initialized before measurement. This excludes
        # that one-time initialization, not the serial printing itself.
        # Instrumentation itself uses only scalar counters.
        assert 'FIXED SESSION GAP 64\n' in content,content[-1000:]
        cursor_at(1)
        # A paced256-event real PS/2 session includes edits, backspace,
        # empty submissions and history wrap. No synthetic enqueue bypass.
        for key in ['a','b','backspace','c','ret','ret','a','ret'] * 32:
            sock.sendall(('sendkey '+key+'\n').encode());sock.recv(4096)
            if key=='ret':submits+=1
            else:edits+=1
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                content=serial.read_text(errors='replace')
                if content.count('FIXED SUBMITTED')>=submits and content.count('FIXED EDIT')>=edits:break
                time.sleep(.1)
            else:raise AssertionError('steady session stalled '+key)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            content=serial.read_text(errors='replace')
            if 'FIXED STEADY GAP ' in content:break
            time.sleep(.1)
        assert 'FIXED STEADY GAP 16\n' in content,content[-1000:]
        # Real extended PS/2 make+break produces one event each, no ASCII.
        for key in ['up','down']:
            sock.sendall(('sendkey '+key+'\n').encode());sock.recv(4096)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            content=serial.read_text(errors='replace')
            if 'NAV EVENT 1\n' in content and 'NAV EVENT 2\n' in content:break
            time.sleep(.1)
        assert content.count('NAV EVENT 1\n')==1 and content.count('NAV EVENT 2\n')==1,content[-1000:]
        assert content.count('FIXED EDIT')==edits and content.count('FIXED SUBMITTED')==submits
        cursor_at(0)
        # Restore a single editable character for the capacity boundary walk.
        sock.sendall(b'sendkey g\n');sock.recv(4096);edits+=1
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            content=serial.read_text(errors='replace')
            if content.count('FIXED EDIT')>=edits:break
            time.sleep(.1)
        else:raise AssertionError('post-steady input stalled')
        cursor_at(1)
        # Overflow typing leaves the cursor at the full-capacity position;
        # backspace removes the old marker, and Enter resets it to column 0.
        for key, expected in [('a',i) for i in range(2,43)]+[('a',42),('backspace',41),('ret',0)]:
            sock.sendall(('sendkey '+key+'\n').encode())
            reply=sock.recv(4096)
            if key=='ret':submits+=1
            else:edits+=1
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                content=serial.read_text(errors='replace')
                if content.count('FIXED SUBMITTED')>=submits and content.count('FIXED EDIT')>=edits:break
                time.sleep(.1)
            else:raise AssertionError('cursor boundary edit stalled '+key)
            if expected in (42,41,0):cursor_at(expected)
            if expected==42 and os.environ.get('HS_TEST_FULL_SCREENSHOT'):
                shutil.copyfile(screen,os.environ['HS_TEST_FULL_SCREENSHOT'])
        # Empty submissions must evict old visible text, not leave stale glyphs.
        # An empty backspace must preserve cursor0 and never underflow storage.
        for key in ['backspace'] + ['ret'] * 5:
            sock.sendall(('sendkey '+key+'\n').encode());sock.recv(4096)
            if key=='ret':submits+=1
            else:edits+=1
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                content=serial.read_text(errors='replace')
                if content.count('FIXED SUBMITTED')>=submits and content.count('FIXED EDIT')>=edits:break
                time.sleep(.1)
            else:raise AssertionError('empty-history edit stalled '+key)
        cursor_at(0)
        # cursor_at waits for the completed screendump; check full text strips.
        with screen.open('rb') as f:
            f.readline();f.readline();f.readline();blank=f.read()
        for y0 in (136,160,184,208,280):
            for y in range(y0,y0+14):
                for x in range(32,544):
                    offset=(y*640+x)*3
                    assert tuple(blank[offset:offset+3])==(232,237,242),('stale empty text',x,y)
        if os.environ.get('HS_TEST_EMPTY_SCREENSHOT'):
            shutil.copyfile(screen,os.environ['HS_TEST_EMPTY_SCREENSHOT'])
        # Restore the original transcript/current-line screenshot below.
        for key in ['c','ret','d','ret','e','ret','f','ret','g']:
            sock.sendall(('sendkey '+key+'\n').encode());sock.recv(4096)
            if key=='ret':submits+=1
            else:edits+=1
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                content=serial.read_text(errors='replace')
                if content.count('FIXED SUBMITTED')>=submits and content.count('FIXED EDIT')>=edits:break
                time.sleep(.1)
            else:raise AssertionError('restore edit stalled '+key)
        cursor_at(1)
        assert 'FIXED SUBMITTED 1\n'in content,content
        assert 'FIXED SUBMITTED 6\n'in content,content
        sock.sendall(('screendump '+str(screen)+'\n').encode())
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and (not screen.exists() or screen.stat().st_size<640*480*3):time.sleep(.1)
        before_events=[int(line.split()[-1]) for line in content.splitlines() if line.startswith('ORDERED EVENT ')]
        mixed=['a','up','b','down','backspace','ret']
        for key in mixed:
            sock.sendall(('sendkey '+key+' 20\n').encode());sock.recv(4096)
            time.sleep(.04)
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            event_log=[int(line.split()[-1]) for line in serial.read_text(errors='replace').splitlines() if line.startswith('ORDERED EVENT ')]
            if len(event_log)>=len(before_events)+6:break
            time.sleep(.1)
        assert event_log[len(before_events):]==[97,128,98,129,8,10],event_log[-10:]
        sock.close()
        with screen.open('rb') as f:
            assert f.readline().strip()==b'P6';dims=f.readline()
            while dims.startswith(b'#'):dims=f.readline()
            assert dims.strip()==b'640 480';assert f.readline().strip()==b'255';pixels=f.read()
        assert len(pixels)==640*480*3
        def pixel(x,y):return tuple(pixels[(y*640+x)*3:(y*640+x)*3+3])
        assert pixel(0,0)==(22,50,79)
        # Independent C/D/E/F transcript and G current input bitmaps.
        glyphs=[(32,136,[15,16,16,16,16,16,15]),(32,160,[30,17,17,17,17,17,30]),
                (32,184,[31,16,16,30,16,16,31]),(32,208,[31,16,16,30,16,16,16]),
                (32,280,[15,16,16,23,17,17,15])]
        for x,y,rows in glyphs:
            for row,bits in enumerate(rows):
                for col in range(6):
                    want=(22,50,79)if col<5 and bits & (1<<(4-col))else (232,237,242)
                    for dy in range(2):
                        for dx in range(2):
                            assert pixel(x+col*2+dx,y+row*2+dy)==want,(x,y,row,col)
        # Active cursor follows G at column 1, with no stale cursor at 0.
        for y in (294,295):
            for x in range(32,548):
                assert pixel(x,y)==((22,50,79) if 44<=x<52 else (232,237,242)),(x,y)
        if os.environ.get('HS_TEST_SCREENSHOT'):
            shutil.copyfile(screen,os.environ['HS_TEST_SCREENSHOT'])
        print('5/5 fixed-buffer console gates (native image, transcript, text pixels, cursor capacity/backspace/reset and empty-history boundaries)')
    finally:
        p.kill();p.wait();qerrfile.close()
