#!/usr/bin/env python3
"""Direct framebuffer font: independent guarded RGB24/32 byte oracle in QEMU."""
from pathlib import Path
import contextlib,io,json,os,random,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from x64gen import build_x64,build_xkernel
qemu=shutil.which('qemu-system-x86_64')
if not qemu:print('skip direct framebuffer font: QEMU unavailable');sys.exit(0)
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel')+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
os.environ['HSPATH']=env['HSPATH']
forms={'H':[17,17,17,31,17,17,17],'I':[31,4,4,4,4,4,31],
       'A':[14,17,17,31,17,17,17],'?':[14,17,1,2,4,0,4],' ':[0]*7}
passed=0
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);driver=d/'driver'
    if '--python-bootstrap'in sys.argv:
        with contextlib.redirect_stdout(io.StringIO()):rc=build_x64(str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver))
        assert not rc
    else:
        r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)],env=env,capture_output=True,timeout=240);assert not r.returncode,r.stderr[-250:]
    for bpp,channels in [(3,[0,1,2]),(4,[2,1,0])]:
        w,h=43,29;pitch=w*bpp+7;size=pitch*h+32;want=[90]*size
        lines=['import kfont','def make(size):','  unsafe:','    return as_int(alloc(size))','def put(p, value):','  unsafe:','    store8(as_ptr(p), value)','def get(p):','  unsafe:','    return load8(as_ptr(p))',f'p = make({size})',f'for i in range({size}):','  put(p + i, 90)',f'f = [p + 16, {pitch}, {w}, {h}, {bpp}, '+', '.join(map(str,channels))+']',f'kfont.fill(f, 0, 0, {w}, {h}, 7)']
        def pixel(x,y,color):
            if 0<=x<w and 0<=y<h:
                for channel,shift in zip(channels,[16,8,0]):want[16+y*pitch+x*bpp+channel]=(color>>shift)&255
        for y in range(h):
            for x in range(w):pixel(x,y,7)
        rng=random.Random(907)
        for i in range(22):
            text=rng.choice(['HI','Hi A','A\nI','@ H','?','']);scale=rng.randrange(1,5);x=rng.randrange(-25,50);y=rng.randrange(-25,35);color=0x125690+i
            lines.append(f'kfont.draw(f, {x}, {y}, '+json.dumps(text)+f', {color}, {scale})');cx,cy=x,y
            for ch in text:
                if ch=='\n':cx=x;cy+=8*scale;continue
                for row,bits in enumerate(forms.get(ch.upper(),forms['?'])):
                    for col in range(5):
                        if bits & (1<<(4-col)):
                            for dy in range(scale):
                                for dx in range(scale):pixel(cx+col*scale+dx,cy+row*scale+dy,color)
                cx+=6*scale
        invalid=['kfont.draw(f, 0, 0, "A", 1, 0)','kfont.draw(f, 0, 0, "A", 1, true)','kfont.draw(f, 0, 0, "A", -1, 1)','kfont.fill(f, 0, 0, 1, true, 9)','kfont.draw(f, 1048577, 0, "A", 1, 1)']
        for call in invalid:lines+=['try:','  '+call,'except:','  print "rejected"']
        lines+=['out = []',f'for i in range({size}):','  append(out, get(p + i))','print out','print "KFONT DONE"']
        source=d/'source.holy';source.write_text('\n'.join(lines)+'\n');image=d/'image'
        with contextlib.redirect_stdout(io.StringIO()):rc=build_xkernel(str(source),str(image))
        assert not rc
        r=subprocess.run([str(driver),str(source),str(d/'native')],env=env,capture_output=True,timeout=90)
        assert not r.returncode and (d/'native').read_bytes()==image.read_bytes(),r.stderr[-250:];passed+=1
        serial=d/'serial';serial.unlink(missing_ok=True)
        p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            end=time.monotonic()+20;out=''
            while time.monotonic()<end:
                out=serial.read_text(errors='replace')if serial.exists()else ''
                if 'KFONT DONE\n'in out:break
                time.sleep(.1)
        finally:p.kill();p.wait()
        expected='rejected\n'*len(invalid)+str(want)+'\nKFONT DONE\n'
        assert out==expected,(bpp,out[-100:],expected[-100:]);passed+=1
print(f'{passed}/{passed} direct font guarded RGB24/32 native-image/QEMU pixel gates')
