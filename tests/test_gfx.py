#!/usr/bin/env python3
"""Software drawing independently checked per pixel, then differential backends."""
from pathlib import Path
import os,random,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
def check(ok,label):
    global passed,failed
    passed+=int(ok);failed+=int(not ok)
    if not ok: print('FAIL',label,flush=True)
env=dict(os.environ,HSPATH=str(ROOT))
w,h=17,13;expected=[0]*(w*h);lines=['import std.gfx',f's = std.gfx.surface({w}, {h}, 0)']
rng=random.Random(718)
for n in range(55):
    x,y=rng.randrange(-20,25),rng.randrange(-20,25);rw,rh=rng.randrange(-3,30),rng.randrange(-3,30);color=rng.randrange(1<<24)
    lines.append(f'std.gfx.rect(s, {x}, {y}, {rw}, {rh}, {color})')
    for row in range(h):
        for col in range(w):
            if x<=col<x+rw and y<=row<y+rh:expected[row*w+col]=color
for x,y in [(2,1),(-3,-2),(99,99),(-99,-99),(0,0)]:
    lines.append(f'std.gfx.blit(s, s, {x}, {y})');prior=expected[:]
    for row in range(h):
        for col in range(w):
            if 0<=col-x<w and 0<=row-y<h:expected[row*w+col]=prior[(row-y)*w+col-x]
lines+=['a = std.gfx.surface(3, 2, 11)', 'std.gfx.pixel(a, 1, 0, 22)', 'std.gfx.blit(s, a, -1, 11)', 'std.gfx.pixel(s, -1, 0, 0)','std.gfx.pixel(s, 0, 0, 66051)','print s[2]','print std.gfx.sample(s, 0, 0)'];expected[0]=66051
for row in range(2):
    for col in range(2):expected[(11+row)*w+col]=22 if row==0 and col==0 else 11
lines+=['try:', '  std.gfx.rect(s, 0, 0, 2, 2, true)','except:', '  print "bad color"','try:', '  std.gfx.surface(4096, 4096, 0)','except:', '  print "too large"','try:', '  std.gfx.sample(s, -1, 0)','except:', '  print "bad read"','print s[2]']
want=str(expected)+'\n66051\nbad color\ntoo large\nbad read\n'+str(expected)+'\n'
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'gfx.hs';source.write_text('\n'.join(lines)+'\n')
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';cmd=[str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)]
            r=subprocess.run(cmd,env=dict(env,HSROOT=str(ROOT)),capture_output=True,text=True,timeout=90)
            if r.returncode==0:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=90)
        check(r.returncode==0 and r.stdout==want,backend+' pixels/clipping/alias/validation '+r.stderr[-150:])
    # Kernel fixture shares the drawing implementation; boot is required in full CI.
    kernel=d/'kernel.hs';kernel.write_text('import std.gfx\ns = std.gfx.surface(8, 6, 0)\nstd.gfx.rect(s, -1, 1, 4, 3, 7)\nstd.gfx.blit(s, s, 2, 1)\nprint "GFX", sum(s[2]), std.gfx.sample(s, 2, 2)\n')
    image=d/'kernel.elf'
    r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(kernel),'-o',str(image)],env=env,capture_output=True,text=True,timeout=60)
    check(r.returncode==0,'freestanding compile '+r.stderr[-200:])
    qemu=shutil.which('qemu-system-x86_64')
    if qemu:
        serial=d/'serial.log'
        p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-m','256M'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:p.wait(timeout=8)
        except subprocess.TimeoutExpired:p.kill();p.wait()
        check(serial.exists() and 'GFX 105 7' in serial.read_text(errors='replace'),'QEMU surface execution')
    else: print('skip QEMU software surface execution (unavailable; full CI requires QEMU)')
print(f'{passed}/{passed+failed} software surface gates')
sys.exit(bool(failed))
