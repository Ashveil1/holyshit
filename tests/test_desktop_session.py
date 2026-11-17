#!/usr/bin/env python3
"""Real GRUB multi-window session: independent edits, raise, drag, reopen, exit."""
import json, os, re, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gui_session import boot, qemu, BG, INK, WHITE, CARET, FORMS
ROOT = Path(__file__).resolve().parent.parent
FORMS['B'] = [30,17,17,30,17,17,30]


def run(d):
    serial = d/'serial'; qmp = d/'qmp'; serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    p = subprocess.Popen([qemu,'-cdrom',str(d/'gui.iso'),'-boot','d','-m','256M','-nic','none',
        '-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off'],stderr=err)
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
        def field(im,text,x,y):
            want=bytearray(WHITE*(352*24))
            for idx,ch in enumerate(text):
                for row,bits in enumerate(FORMS[ch]):
                    for col in range(5):
                        if bits & (1<<(4-col)):
                            at=((8+row)*352+4+idx*6+col)*3;want[at:at+3]=INK
            for row in range(7):
                for col in range(5):
                    at=((8+row)*352+4+len(text)*6+col)*3;want[at:at+3]=CARET
            got=b''.join(im[((y+60+dy)*640+x+12)*3:((y+60+dy)*640+x+364)*3] for dy in range(24))
            assert got==want,('field mismatch',text[:5],len(text),x,y)
        initial=snap('initial');field(initial,'',36,112);field(initial,'',224,252)
        click(60,150);key('h');key('i')
        click(250,290);key('b')
        both=snap('both');field(both,'HI',36,112);field(both,'B',224,252)
        click(60,150);key('backspace');key('a');field(snap('independent'),'HA',36,112)
        # Drag note2 over note1. It raises on title press and preserves text.
        move(240,255);h('mouse_button 1');time.sleep(.15);move(196,155);h('mouse_button 0')
        def moved():return pixel(snap('overlap'),180,152)==bytes.fromhex('2a6fdb')
        wait_for(moved,'note2 move/raise')
        overlap=snap('overlap');field(overlap,'B',180,152)
        assert pixel(overlap,224,360)==BG,'old note2 location remains'
        # Note1's exposed title raises it over note2 without changing text.
        click(60,115)
        wait_for(lambda:pixel(snap('raised'),180,152)==bytes.fromhex('e8edf2'),'note1 raise')
        raised=snap('raised');field(raised,'HA',36,112)
        # Close note2 through its exposed body, then close note1.
        click(500,200);key('down');field(snap('one-note'),'HA',36,112)
        click(60,150);key('down')
        empty=snap('launcher-only')
        for x,y in [(36,112),(100,190),(224,252),(400,330)]:assert pixel(empty,x,y)==BG
        # Launcher survives both closes and reopens retained independent RAM text.
        click(60,50);key('1');key('2')
        reopened=snap('reopened');field(reopened,'HA',36,112);field(reopened,'B',224,252)
        before=count();key('1',False);key('2',False);assert count()==before, 'duplicate note opened'
        # Note1 cap is independent of note2 and ignored keys create no edits.
        click(60,150);key('ret')
        for _ in range(54):key('a')
        before=count();key('a',False);key('up',False);assert count()==before
        capped=snap('capped');field(capped,'A'*54,36,112);field(capped,'B',224,252)
        # No focused window means a key does not reach either note.
        click(620,450);key('h',False);assert count()==before
        click(60,50);key('down',False)
        wait_for(lambda:'GUI SESSION STOPPED' in out(),'session exit')
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
        for ir_backend in (True,False):
            with tempfile.TemporaryDirectory(prefix='desktop-'+('ir-' if ir_backend else 'ast-')) as temp:
                d=Path(temp);boot(d,ir_backend,desktop=True);run(d)
            print('ok real multi-window desktop focus/edit/raise/drag/reopen/exit', 'ir' if ir_backend else 'ast')
        print('2/2 desktop session gates; native IR kernel and user bytes verified')
