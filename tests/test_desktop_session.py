#!/usr/bin/env python3
"""Real GRUB multi-window session: independent edits, raise, drag, reopen, exit."""
import json, os, re, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gui_session import boot, qemu, BG, INK, WHITE, CARET, FORMS
ROOT = Path(__file__).resolve().parent.parent
FORMS['B'] = [30,17,17,30,17,17,30]


def run(d, disk=None, firmware=None, firmware_vars=None):
    serial = d/'serial'; qmp = d/'qmp'; serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    args = [qemu,'-cdrom',str(d/'gui.iso'),'-boot','d','-m','256M','-nic','none',
        '-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off']
    if firmware_vars:
        args+=['-drive','if=pflash,format=raw,readonly=on,file='+str(firmware),
               '-drive','if=pflash,format=raw,file='+str(firmware_vars)]
    elif firmware:args+=['-bios',str(firmware)]
    if disk:args+=['-drive','file='+str(disk)+',if=ide,format=raw']
    p = subprocess.Popen(args,stderr=err)
    s = None
    def out(): return serial.read_text(errors='replace') if serial.exists() else ''
    def wait_for(test, label, seconds=15):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            if test(): return
            assert p.poll() is None, out()
            time.sleep(.03)
        raise AssertionError((label,out()[-3000:]))
    try:
        wait_for(lambda:'DESKTOP READY' in out(),'desktop ready',45)
        s = socket.socket(socket.AF_UNIX); s.settimeout(10); s.connect(str(qmp)); f=s.makefile('rwb',buffering=0);json.loads(f.readline())
        def cmd(name,args=None):
            req={'execute':name}
            if args is not None:req['arguments']=args
            f.write(json.dumps(req).encode()+b'\r\n')
            while True:
                r=json.loads(f.readline());assert 'error' not in r,r
                if 'return' in r:return r['return']
        cmd('qmp_capabilities')
        def h(c): assert not cmd('human-monitor-command',{'command-line':c})
        cursor=[0,0]
        def move(x,y):
            h('mouse_move '+str(x-cursor[0])+' '+str(cursor[1]-y));cursor[:]=[x,y];time.sleep(.15)
        def click(x,y):
            move(x,y);h('mouse_button 1');time.sleep(.1);h('mouse_button 0');time.sleep(.15)
        def count():return len(re.findall(r'DESKTOP\s+(EDIT|OPEN|CLOSE)\s+',out()))
        def key(k,changed=True):
            before=count();h('sendkey '+k)
            if changed:wait_for(lambda:count()==before+1,'key '+k)
            else:time.sleep(.2)
        def snap(name):
            path=d/(name+'.ppm');h('screendump '+str(path))
            with path.open('rb') as im:
                assert im.readline().strip()==b'P6';dims=im.readline()
                while dims.startswith(b'#'):dims=im.readline()
                assert dims.strip()==b'640 480';assert im.readline().strip()==b'255'
                data=im.read();assert len(data)==640*480*3
            return data
        def pixel(im,x,y):return im[(y*640+x)*3:(y*640+x)*3+3]
        def field(im,text,x,y,caret=None):
            want=bytearray(WHITE*(416*56))
            row_index=0; column=0
            caret_pos=None
            if caret is None:caret=len(text)
            for offset,ch in enumerate(text):
                if ch != '\n' and column==32:
                    row_index+=1;column=0
                if offset==caret:caret_pos=(row_index,column)
                if ch == '\n':
                    row_index+=1;column=0;continue
                for row,bits in enumerate(FORMS[ch]):
                    for col in range(5):
                        if bits & (1<<(4-col)):
                            for dy in range(2):
                                for dx in range(2):
                                    at=((8+row_index*16+row*2+dy)*416+4+column*12+col*2+dx)*3
                                    want[at:at+3]=INK
                column+=1
            if caret_pos is None:caret_pos=(row_index,column)
            for row in range(14):
                for col in range(10):
                    at=((8+caret_pos[0]*16+row)*416+4+caret_pos[1]*12+col)*3;want[at:at+3]=CARET
            got=b''.join(im[((y+60+dy)*640+x+12)*3:((y+60+dy)*640+x+428)*3] for dy in range(56))
            assert got==want,('field mismatch',text[:5],len(text),x,y)
        initial=snap('initial');field(initial,'',24,132);field(initial,'',176,308)
        click(48,170);key('h');key('i')
        click(200,346);key('b')
        both=snap('both');field(both,'HI',24,132);field(both,'B',176,308)
        click(48,170);key('backspace');key('a');field(snap('independent'),'HA',24,132)
        # Drag note2 over note1. It raises on title press and preserves text.
        move(192,311);h('mouse_button 1');time.sleep(.15);move(196,175);h('mouse_button 0')
        def moved():return pixel(snap('overlap'),180,172)==bytes.fromhex('2a6fdb')
        wait_for(moved,'note2 move/raise')
        overlap=snap('overlap');field(overlap,'B',180,172)
        assert pixel(overlap,176,450)==BG,'old note2 location remains'
        # Note1's exposed title raises it over note2 without changing text.
        click(48,135)
        wait_for(lambda:pixel(snap('raised'),24,132)==bytes.fromhex('2a6fdb'),'note1 raise')
        raised=snap('raised');field(raised,'HA',24,132)
        # Close note2 through its exposed body, then close note1.
        click(550,200);key('esc');field(snap('one-note'),'HA',24,132)
        click(48,170);key('esc')
        empty=snap('launcher-only')
        for x,y in [(24,132),(100,210),(176,308),(400,410)]:assert pixel(empty,x,y)==BG
        # Launcher survives both closes and reopens retained independent RAM text.
        click(60,50);key('1');key('2')
        reopened=snap('reopened');field(reopened,'HA',24,132);field(reopened,'B',176,308)
        before=count();key('1',False);key('2',False);assert count()==before, 'duplicate note opened'
        # Note1 cap is independent of note2 and ignored keys create no edits.
        click(60,50);key('3');click(48,170)
        key('h');key('ret');key('i');field(snap('multiline'),'H\nI',24,132)
        key('backspace');key('backspace');key('a');field(snap('joined'),'HA',24,132)
        key('ret');key('b');field(snap('manual-line'),'HA\nB',24,132)
        key('esc');click(60,50);key('1')
        field(snap('multiline-reopened'),'HA\nB',24,132)
        click(60,50);key('3');click(48,170)
        for _ in range(96):key('a')
        before=count();key('a',False);key('ret',False);assert count()==before
        capped=snap('capped');field(capped,'A'*32+'\n'+'A'*32+'\n'+'A'*32,24,132);field(capped,'B',176,308)
        # Erase the whole last implicit row, then append and wrap again.
        for _ in range(32):key('backspace')
        field(snap('wrap-erased'),'A'*32+'\n'+'A'*32,24,132)
        key('b');field(snap('rewrapped'),'A'*32+'\n'+'A'*32+'\nB',24,132)
        # Middle insertion/delete and visual-row caret movement on real keys.
        click(60,50);key('3');click(48,170)
        key('h');key('i');key('ret');key('a');key('b')
        key('left');key('i');field(snap('inserted'),'HI\nAIB',24,132,5)
        key('delete');field(snap('deleted'),'HI\nAI',24,132,5)
        key('home');field(snap('home'),'HI\nAI',24,132,3)
        key('up');field(snap('up'),'HI\nAI',24,132,0)
        key('end');key('down');field(snap('down'),'HI\nAI',24,132,5)
        key('left');key('backspace');field(snap('backspace-middle'),'HI\nI',24,132,3)
        key('home',False);key('left');key('delete');field(snap('delete-newline'),'HII',24,132,2)
        key('right');key('end',False);key('right',False)
        # Closing/reopening preserves the in-buffer caret, not just the text.
        key('left');key('esc');click(60,50);key('1')
        field(snap('caret-reopened'),'HII',24,132,2)
        before=count()
        # No focused window means a key does not reach either note.
        click(620,470);key('h',False);assert count()==before
        click(60,50);key('esc',False)
        wait_for(lambda:re.search(r'GUI SESSION STOPPED\s+0\s+0\s+0\s+0',out()),'complete session exit')
        assert re.search(r'GUI SESSION STOPPED\s+0\s+0\s+0\s+0',out()),out()
        closed=snap('closed')
        for y in range(480):
            for x in range(640):
                if 60<=x<67 and 50<=y<57:continue
                assert pixel(closed,x,y)==BG,('stale exit pixel',x,y)
    finally:
        if s:s.close()
        p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait()
        err.close()
        if os.environ.get('HS_GUI_EVIDENCE'):
            dest=Path(os.environ['HS_GUI_EVIDENCE'])/d.name;dest.mkdir(parents=True,exist_ok=True)
            for path in d.iterdir():
                if path.suffix=='.ppm' or path.name in ('serial','qemu.stderr'):shutil.copyfile(path,dest/path.name)


if __name__=='__main__':
    if '--run-prepared' in sys.argv:
        run(Path(sys.argv[sys.argv.index('--run-prepared')+1]));print('ok prepared desktop session')
    else:
        backends = (True,False)
        if '--backend' in sys.argv:
            backends = (sys.argv[sys.argv.index('--backend')+1] == 'ir',)
        for ir_backend in backends:
            with tempfile.TemporaryDirectory(prefix='desktop-'+('ir-' if ir_backend else 'ast-')) as temp:
                d=Path(temp);boot(d,ir_backend,desktop=True)
                disk=d/'untouched.img';before=b'NOT A KVOL DISK'+bytes(1024*1024-15);disk.write_bytes(before)
                run(d,disk)
                assert disk.read_bytes()==before, 'default GUI wrote attached disk'
                assert 'GUI VOLUME' not in (d/'serial').read_text(), 'default GUI probed volume'
            print('ok real multi-window desktop focus/edit/raise/drag/reopen/exit', 'ir' if ir_backend else 'ast')
        print(str(len(backends))+'/'+str(len(backends))+' desktop session gates; native IR bytes verified when selected')
