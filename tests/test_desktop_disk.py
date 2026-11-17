#!/usr/bin/env python3
"""Opt-in disk desktop: real GUI edits, explicit save and complete reboots.

Only a disposable raw image created by this test is ever attached. The default
RAM-only GUI is tested separately. Normal reboot persistence is not crash safety.
"""
import json, os, re, shutil, socket, struct, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_gui_session import boot, qemu, WHITE, INK, CARET, FORMS
FORMS['B']=[30,17,17,30,17,17,30]

def run(d,iso,disk,phase):
    for old in d.glob('*.ppm'):old.unlink()
    serial=d/'serial'; sock=d/'qmp';serial.unlink(missing_ok=True);sock.unlink(missing_ok=True)
    args=[qemu,'-cdrom',str(iso),'-boot','d','-m','256M','-nic','none','-display','none',
          '-serial','file:'+str(serial),'-qmp','unix:'+str(sock)+',server=on,wait=off']
    if disk:args+=['-drive','file='+str(disk)+',if=ide,format=raw']
    err=(d/'qemu.stderr').open('wb');p=subprocess.Popen(args,stderr=err);s=None
    def out():return serial.read_text(errors='replace') if serial.exists() else ''
    def wait(test,label):
        end=time.monotonic()+45
        while time.monotonic()<end:
            if test():return
            assert p.poll() is None,out()
            time.sleep(.03)
        raise AssertionError((phase,label,out()[-2500:]))
    try:
        wait(lambda:'DESKTOP READY' in out(),'ready')
        s=socket.socket(socket.AF_UNIX);s.settimeout(10);s.connect(str(sock));f=s.makefile('rwb',buffering=0);json.loads(f.readline())
        def cmd(name,args=None):
            request={'execute':name}
            if args is not None:request['arguments']=args
            f.write(json.dumps(request).encode()+b'\r\n')
            while True:
                reply=json.loads(f.readline());assert 'error' not in reply,reply
                if 'return' in reply:return reply['return']
        cmd('qmp_capabilities')
        def h(text):assert not cmd('human-monitor-command',{'command-line':text})
        pointer=[0,0]
        def click(x,y):
            h('mouse_move '+str(x-pointer[0])+' '+str(pointer[1]-y));pointer[:]=[x,y];time.sleep(.12)
            h('mouse_button 1');time.sleep(.08);h('mouse_button 0');time.sleep(.12)
        def key(text):
            before=out();h('sendkey '+text)
            wait(lambda:len(out())>len(before),'key '+text)
        def snap(name):
            dest=d/(name+'.ppm');h('screendump '+str(dest))
            with dest.open('rb') as image:
                assert image.readline().strip()==b'P6';assert image.readline().strip()==b'640 480';assert image.readline().strip()==b'255'
                data=image.read();assert len(data)==640*480*3
            return data
        def footer(image):
            return b''.join(image[((132+122+dy)*640+36)*3:((132+122+dy)*640+452)*3] for dy in range(20))
        def field(text,x,y):
            image=snap('phase'+str(phase)+'-field'+str(x));want=bytearray(WHITE*(416*56));row=col=0
            for ch in text:
                if ch=='\n':row+=1;col=0;continue
                for gy,bits in enumerate(FORMS[ch]):
                    for gx in range(5):
                        if bits & (1<<(4-gx)):
                            for dy in range(2):
                                for dx in range(2):
                                    at=((8+row*16+gy*2+dy)*416+4+col*12+gx*2+dx)*3;want[at:at+3]=INK
                col+=1
            for dy in range(14):
                for dx in range(10):
                    at=((8+row*16+dy)*416+4+col*12+dx)*3;want[at:at+3]=CARET
            got=b''.join(image[((y+60+dy)*640+x+12)*3:((y+60+dy)*640+x+428)*3] for dy in range(56))
            assert got==want,(phase,text,x,y)
        if phase==0:
            click(48,170)
            for k in ['h','ret','i','left','a','end']:key(k)
            click(200,346);key('b');field('H\nAI',24,132);field('B',176,308)
            click(60,50);key('5');assert 'DESKTOP SAVE true' in ' '.join(out().split()),out()
            saved_footer=footer(snap('saved'))
            saved=disk.read_bytes();assert saved[:4]==b'KVOL'
            # An edit and clean GUI exit are NOT implicit saves.
            click(48,170);key('left');key('right')
            assert footer(snap('saved-navigation'))==saved_footer
            key('b');assert footer(snap('unsaved'))!=saved_footer
            assert disk.read_bytes()==saved
        elif phase==1:
            field('H\nAI',24,132);field('B',176,308);snap('restored')
            click(60,50);key('3');key('4');click(48,170);key('h');key('i')
            click(60,50);key('5');assert 'DESKTOP SAVE true' in ' '.join(out().split()),out()
        elif phase==2:
            field('HI',24,132);field('',176,308);snap('restored-second')
        else:
            field('',24,132);click(48,170);key('h')
            click(60,50);key('5');assert 'DESKTOP SAVE false' in ' '.join(out().split()),out()
            field('H',24,132);snap('save-failed')
        click(60,50);h('sendkey esc');wait(lambda:re.search(r'GUI SESSION STOPPED\s+0\s+0\s+0\s+0',out()),'complete exit')
        assert re.search(r'GUI SESSION STOPPED\s+0\s+0\s+0\s+0',out()),out()
    finally:
        if s:s.close()
        p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait()
        err.close()
        if os.environ.get('HS_GUI_EVIDENCE'):
            dest=Path(os.environ['HS_GUI_EVIDENCE'])/(d.name+'-'+str(phase));dest.mkdir(parents=True,exist_ok=True)
            for path in d.iterdir():
                if path.suffix=='.ppm' or path.name in ('serial','qemu.stderr'):shutil.copyfile(path,dest/path.name)

def disk_notes(data):
    assert data[:4]==b'KVOL'
    n=struct.unpack_from('<I',data,4)[0];image=data[512:512+n]
    assert image[:4]==b'KRFS';off=8;files={}
    for _ in range(struct.unpack_from('<I',image,4)[0]):
        kind,size=struct.unpack_from('<II',image,off);off+=8
        path=image[off:off+size];off+=(size+3)&~3
        size=struct.unpack_from('<I',image,off)[0];off+=4
        if kind==0:files[b'/'+path.lstrip(b'/')]=image[off:off+size]
        off+=(size+3)&~3
    assert off==n
    assert b'/bin/uunote' not in files, 'app ELF must not consume volume budget'
    return files

def gates(d,iso):
    disk=d/'disposable.img';disk.write_bytes(bytes(1024*1024))
    run(d,iso,disk,0);saved=disk.read_bytes()
    files=disk_notes(saved);assert files[b'/note1']==b'h\nai' and files[b'/note2']==b'b'
    run(d,iso,disk,1);assert disk.read_bytes()!=saved
    final=disk.read_bytes();files=disk_notes(final)
    assert files[b'/note1']==b'hi' and files[b'/note2']==b''
    run(d,iso,disk,2);assert disk.read_bytes()==final
    run(d,iso,None,3)
    corrupt=b'KVOL'+struct.pack('<II',4,1)+bytes(1024*1024-12)
    disk.write_bytes(corrupt);run(d,iso,disk,4);assert disk.read_bytes()==corrupt
    # Valid KRFS with invalid note data must not be treated as edit commands,
    # silently truncated or overwritten. These cases preserve every disk byte.
    for phase,payload in [(5,b'H\x08I'),(6,b'A'*99),(7,b'\xff'),(8,b'\n'*3)]:
        path=b'/note1';entry=struct.pack('<II',0,len(path))+path+bytes((-len(path))%4)+struct.pack('<I',len(payload))+payload+bytes((-len(payload))%4)
        image=b'KRFS'+struct.pack('<I',1)+entry
        bad=b'KVOL'+struct.pack('<II',len(image),1)+bytes(500)+image
        bad+=bytes(1024*1024-len(bad));disk.write_bytes(bad)
        run(d,iso,disk,phase);assert disk.read_bytes()==bad
    print('ok explicit saves, dirty status, two full reboot restores, no disk/corrupt/invalid/oversized refusal')

if __name__=='__main__':
    if '--run-prepared' in sys.argv:
        d=Path(sys.argv[sys.argv.index('--run-prepared')+1]);gates(d,d/'gui.iso')
    else:
        for ir in (True,False):
            with tempfile.TemporaryDirectory(prefix='desktop-disk-'+('ir-' if ir else 'ast-')) as temp:
                d=Path(temp);iso=boot(d,ir,desktop=True,disk=True);gates(d,iso)
            print('ok disk desktop', 'ir' if ir else 'ast')
        print('2/2 disposable-volume desktop gates; native IR full ELF identity checked')
