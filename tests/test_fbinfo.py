#!/usr/bin/env python3
"""Framebuffer tags: independent binary fixture, strict rejection before mapping."""
from pathlib import Path
import os,struct,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent.parent
passed=failed=0
base=bytearray(struct.pack('<IIQIIIBBH6B',8,38,0xe0000000,2560,640,480,32,1,0,16,8,8,8,0,8))
cases=[(base,True)]
for offset,value,fmt in [(0,2,'I'),(4,37,'I'),(12,1,'I'),(16,1,'I'),(20,0,'I'),(24,5000,'I'),(28,16,'B'),(29,2,'B'),(32,7,'B'),(33,5,'B'),(34,16,'B'),(36,40,'B'),(8,0x100000,'I'),(8,0xfffff000,'I')]:
    bad=base[:];struct.pack_into('<'+fmt,bad,offset,value);cases.append((bad,False))
cases.append((base[:20],False))
source='import std.fbinfo\n'
for data,valid in cases:
    source+='try:\n  frame = std.fbinfo.decode('+str(list(data))+')\n  print frame\nexcept:\n  print "rejected"\n'
want='[3758096384, 2560, 640, 480, 4, 2, 1, 0]\n'+'rejected\n'*(len(cases)-1)
env=dict(os.environ,HSPATH=str(ROOT),HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);path=d/'tags.holy';path.write_text(source)
    for backend in ['interp','native','x64','native-hs']:
        if backend=='native-hs':
            exe=d/'program';r=subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(path),str(exe)],env=env,capture_output=True,text=True,timeout=90)
            if not r.returncode:r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        else:r=subprocess.run([sys.executable,str(ROOT/'hs.py'),'run',str(path),'--backend',backend],env=env,capture_output=True,text=True,timeout=90)
        ok=r.returncode==0 and r.stdout==want;passed+=int(ok);failed+=int(not ok)
        if not ok:print('FAIL',backend,r.returncode,repr(r.stdout),r.stderr[-200:])
print(f'{passed}/{passed+failed} framebuffer descriptor gates ({len(cases)} tags per backend)')
sys.exit(bool(failed))
