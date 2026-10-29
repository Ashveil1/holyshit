#!/usr/bin/env python3
"""Two private low virtual mappings with live CR3 round trips on QEMU."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
 if os.environ.get('HS_REQUIRE_KSPACE')=='1':raise SystemExit('QEMU required')
 print('skip address space: QEMU unavailable');sys.exit(0)
env=dict(os.environ,HSPATH=f'{ROOT}:{ROOT}/kernel:{ROOT}/selfhost:{ROOT}/selfhost/be',HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
 d=Path(temp);s=d/'space.holy';s.write_text('''import kspace
import kpage
import kpmm
import kuser
assert kpmm.init() > 0
original = cr3()
a = kspace.create()
b = kspace.create()
assert a != 0 and b != 0 and a != b
va = kspace.LOW
original_entry = kpage.pte_get(original, va)
pa = kspace.map_user(a, va)
pb = kspace.map_user(b, va)
assert pa != 0 and pb != 0 and pa != pb
assert kpage.pte_get(original, va) == original_entry
assert kspace.map_user(original, va) == 0
assert kspace.map_user(a, va) == 0
assert kspace.map_user(a, 0x400000) == 0
assert kspace.map_user(a, va + 1) == 0
assert kspace.map_user(a, kspace.HIGH) == 0
assert kpage.pte_get(a, va) & 4 != 0
assert kpage.pte_get(b, va) & 4 != 0
# Neighbor remains the original supervisor identity mapping after huge split.
assert kpage.pte_get(a, va + 4096) & 4 == 0
assert kpage.pte_get(b, va + 4096) & 4 == 0
assert kpage.pte_get(a, 0x100000) & 4 == 0
set_cr3(a)
assert cr3() == a
assert kpage.entry_get(va, 0) == 0
kuser.poke(va, 111)
set_cr3(b)
assert cr3() == b
assert kpage.entry_get(va, 0) == 0
kuser.poke(va, 222)
set_cr3(a)
assert kpage.entry_get(va, 0) == 111
set_cr3(original)
assert cr3() == original
assert kpage.entry_get(pa, 0) == 111
assert kpage.entry_get(pb, 0) == 222
assert kpage.pte_get(original, va) == original_entry
assert kpmm.available() > 0
print "ADDRESS SPACE DONE"
''')
 image=d/'kernel';native=d/'native';driver=d/'driver'
 for cmd in [[sys.executable,str(ROOT/'hs.py'),'xkernel',str(s),'-o',str(image)], [str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)], [str(driver),str(s),str(native)]]:
  subprocess.run(cmd,env=env,capture_output=True,check=True,timeout=240)
 assert image.read_bytes()==native.read_bytes(),'native/reference image mismatch'
 serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(image),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  end=time.monotonic()+30;out=b''
  while time.monotonic()<end:
   out=serial.read_bytes() if serial.exists() else b''
   if b'ADDRESS SPACE DONE' in out or b'error:' in out:break
   time.sleep(.1)
  assert out==b'ADDRESS SPACE DONE\n',out
 finally:p.kill();p.wait()
print('address-space gates passed: private low mappings, zero frames, two-root CR3 roundtrip, original table untouched, native whole image')
