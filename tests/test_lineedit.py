#!/usr/bin/env python3
"""Bounded line edits against independent state model + actual QEMU keyboard."""
from pathlib import Path
import json,os,random,shutil,socket,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
def literal(s):
    return 'null' if s is None else json.dumps(s).replace('\\b','\x08').replace('\\u0000','\\0')
rng=random.Random(197);lines=['import std.lineedit','s = std.lineedit.create(7)'];want='';text='';submitted=False
for n in range(240):
    if n%23==0:
        lines.append('std.lineedit.reset(s)');text='';submitted=False
    key=rng.choice(list('abc XYZ0123456789')+['\x08','\x08','\n','\t','\r',None])
    lines.append('std.lineedit.feed(s, '+literal(key)+')')
    if key is not None and not submitted:
        if key=='\n':submitted=True
        elif key=='\x08':text=text[:-1]
        elif ' '<=key<='~' and len(text)<7:text+=key
    lines.append('print json_str(s)');want+=json.dumps([text,submitted,7],separators=(', ', ': '))+'\n'
for arg in ['0','257','true','1.5','"1"']:
    lines+=['try:',f'  std.lineedit.create({arg})','except:','  print "rejected"'];want+='rejected\n'
for arg in ['""','"ab"','true','1','[]']:
    lines+=['try:',f'  std.lineedit.feed(s, {arg})','except:','  print "rejected"','print json_str(s)'];want+='rejected\n'+json.dumps([text,submitted,7],separators=(', ', ': '))+'\n'
env=dict(os.environ,HSPATH=str(ROOT),HSROOT=str(ROOT));passed=failed=0
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);source=d/'line.holy';source.write_text('\n'.join(lines)+'\n')
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(source),str(exe)],env=env,capture_output=True,text=True,timeout=90)
            if not r.returncode:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(source),'--backend',backend],env=env,capture_output=True,text=True,timeout=90)
        ok=not r.returncode and r.stdout==want;passed+=ok;failed+=not ok
        if not ok:print('FAIL',backend,r.returncode,repr(r.stdout[-200:]),'first mismatch',next(((i,a,b) for i,(a,b) in enumerate(zip(r.stdout.splitlines(),want.splitlines())) if a!=b),None),r.stderr[-300:])
    source.write_text('import std.lineedit\ns = std.lineedit.create(7)\nprint "LINE READY"\nwhile not s[1]:\n  std.lineedit.feed(s, readkey())\nprint "LINE RESULT", s[0]\n')
    image=d/'line.elf';r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,capture_output=True,text=True,timeout=60)
    ok=not r.returncode;passed+=ok;failed+=not ok
    if not ok:print('FAIL kernel compile',r.stderr[-300:])
    qemu=shutil.which('qemu-system-x86_64')
    if qemu and ok:
        serial=d/'serial';monitor=d/'monitor';p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','unix:'+str(monitor)+',server=on,wait=off','-m','256M'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if serial.exists() and 'LINE READY' in serial.read_text(errors='replace'):break
                if p.poll() is not None:raise AssertionError('QEMU exited')
                time.sleep(.1)
            assert serial.exists() and 'LINE READY' in serial.read_text(errors='replace'),'keyboard demo not ready'
            sock=socket.socket(socket.AF_UNIX);sock.settimeout(5);sock.connect(str(monitor));sock.recv(4096)
            for key in ['a','b','backspace','c','ret']:
                sock.sendall(('sendkey '+key+'\n').encode());reply=sock.recv(4096);assert b'error' not in reply.lower(),reply;time.sleep(.4)
            sock.close();deadline=time.monotonic()+10
            while time.monotonic()<deadline and 'LINE RESULT ac' not in serial.read_text(errors='replace'):time.sleep(.1)
            ok='LINE RESULT ac' in serial.read_text(errors='replace');passed+=ok;failed+=not ok
            if not ok:print('FAIL QEMU edits',serial.read_text(errors='replace')[-300:])
        finally:p.kill();p.wait()
    elif not qemu:print('skip actual QEMU keyboard edits (unavailable)')
print(f'{passed}/{passed+failed} line editor gates (240 independent state transitions)')
sys.exit(bool(failed))
