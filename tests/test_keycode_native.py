#!/usr/bin/env python3
"""Seed-native keyboard-code kernel image and allocation-free empty polling."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
env=dict(os.environ,HSPATH=str(ROOT)+':'+str(ROOT/'kernel')+':'+str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'),HSROOT=str(ROOT))
qemu=os.environ.get('HS_TEST_QEMU')or shutil.which('qemu-system-x86_64')
if not qemu:print('skip native keyboard code kernel: QEMU unavailable');sys.exit(0)
with tempfile.TemporaryDirectory()as temp:
    d=Path(temp);source=d/'source.holy';image=d/'image';native=d/'native';driver=d/'driver'
    source.write_text('def mark():\n  unsafe:\n    return as_int(alloc(1))\nbefore = mark()\ni = 0\nvalid = true\nwhile i < 100000:\n  if readkey_code() != null:\n    valid = false\n  if readkey_nav() != null:\n    valid = false\n  if readkey_event() != null:\n    valid = false\n  i = i + 1\nafter = mark()\nprint after - before\nprint valid\nprint "CODE DONE"\n')
    subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],env=env,capture_output=True,check=True,timeout=90)
    build=([sys.executable,str(ROOT/'hs.py'),'xbuild',str(ROOT/'selfhost/be/kernel_ir.holy'),'-o',str(driver)]if '--python-bootstrap'in sys.argv else [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)])
    subprocess.run(build,env=env,capture_output=True,check=True,timeout=240)
    subprocess.run([str(driver),str(source),str(native)],env=env,capture_output=True,check=True,timeout=90)
    assert native.read_bytes()==image.read_bytes(),'native/Python code kernel mismatch'
    p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(d/'serial'),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        end=time.monotonic()+20;out=''
        while time.monotonic()<end:
            out=(d/'serial').read_text(errors='replace')if(d/'serial').exists()else''
            if 'CODE DONE\n'in out:break
            time.sleep(.1)
    finally:p.kill();p.wait()
    assert out=='16\ntrue\nCODE DONE\n',out
    for name in ['readkey_code','readkey_nav','readkey_event']:
        source.write_text(name+'(1)\n')
        for command in [[sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(image)],[str(driver),str(source),str(native)]]:
            r=subprocess.run(command,env=env,capture_output=True,timeout=90)
            assert r.returncode and (name+' takes no args').encode() in r.stderr,(r.stdout,r.stderr)
print('3/3 native keyboard code gates (complete image,QEMU100000 empty polls16byte marker gap,arity errors)')
