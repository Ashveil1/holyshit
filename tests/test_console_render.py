#!/usr/bin/env python3
"""Finite fixed edit/history + raw font allocation proof with guarded RAM frame."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel')+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
qemu=os.environ.get('HS_TEST_QEMU')or shutil.which('qemu-system-x86_64')
if not qemu:print('skip console render kernel: QEMU unavailable');sys.exit(0)
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);source=d/'proof.holy';source.write_text('''import kfont
import kconsole_buffer
def make(n):
  unsafe:
    return as_int(alloc(n))
def put(p,b):
  unsafe:
    store8(as_ptr(p),b)
def get(p):
  unsafe:
    return load8(as_ptr(p))
s = kconsole_buffer.create(42,4)
p = make(30784)
i = 0
while i < 30784:
  put(p + i,90)
  i = i + 1
f = [p + 16,384,128,80,3,2,1,0]
before = make(1)
n = 0
while n < 1000:
  kconsole_buffer.feed(s,97)
  kconsole_buffer.feed(s,98)
  kconsole_buffer.feed(s,8)
  kconsole_buffer.feed(s,99)
  kconsole_buffer.feed(s,10)
  kfont.fill(f,0,0,128,80,0xe8edf2)
  row = 0
  while row < s[6]:
    kfont.draw_bytes(f,0,row * 16,kconsole_buffer.history_address(s,row),kconsole_buffer.history_length(s,row),0x16324f,2)
    row = row + 1
  kfont.draw_bytes(f,0,64,s[0],s[3],0x16324f,2)
  kfont.fill(f,0,78,128,2,0xe8edf2)
  kfont.fill(f,s[3] * 12,78,8,2,0x16324f)
  n = n + 1
after = make(1)
print after - before
print s[3],s[6],s[7]
out = []
i = 0
while i < 30784:
  append(out,get(p + i))
  i = i + 1
print out
print "CONSOLE RENDER DONE"
''')
    image=d/'image';subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,capture_output=True,check=True,timeout=90)
    driver=d/'driver';native=d/'native'
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/kernel_ir.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)])
    subprocess.run(build,env=env,capture_output=True,check=True,timeout=240)
    subprocess.run([str(driver),str(source),str(native)],env=env,capture_output=True,check=True,timeout=90)
    assert image.read_bytes()==native.read_bytes(),'native/Python image mismatch'
    serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        end=time.monotonic()+60;out=''
        while time.monotonic()<end:
            out=serial.read_text(errors='replace')if serial.exists()else ''
            if 'CONSOLE RENDER DONE\n'in out:break
            time.sleep(.1)
    finally:p.kill();p.wait()
    import json
    rows=out.splitlines();assert len(rows)==4 and rows[:2]==['16','0 4 1000'] and rows[-1]=='CONSOLE RENDER DONE',out[-400:]
    actual=json.loads(rows[2]);want=[90]*30784
    for y in range(80):
        for x in range(128):
            offset=16+y*384+x*3;want[offset:offset+3]=[242,237,232]
    forms=[[14,17,17,31,17,17,17],[15,16,16,16,16,16,15]]
    for line in range(4):
        for character,bits in enumerate(forms):
            for row,mask in enumerate(bits):
                for col in range(5):
                    if mask & (1<<(4-col)):
                        for dy in range(2):
                            for dx in range(2):
                                offset=16+(line*16+row*2+dy)*384+(character*12+col*2+dx)*3;want[offset:offset+3]=[79,50,22]
    for y in (78,79):
        for x in range(8):
            offset=16+y*384+x*3;want[offset:offset+3]=[79,50,22]
    assert actual==want,'integrated pixels/guard mismatch'
print('3/3 integrated console render gates (native image,1000 submissions+redraws16byte marker gap,independent guarded pixels)')
