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
import ksyscall
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
# Same ring3 virtual code and stack in independent roots. User verifies CS.RPL
# and reads its root-specific marker. A syscall handler records active CR3.
code = va + 4096
stack = va + 8192
ca = kspace.map_user(a, code)
cb = kspace.map_user(b, code)
sa = kspace.map_user(a, stack)
sb = kspace.map_user(b, stack)
assert ca != 0 and cb != 0 and sa != 0 and sb != 0
# xor eax,eax; mov ax,cs; and eax,3; cmp eax,3; jne fail;
# mov rax,[abs va]; mov rdi,rax; mov eax,60; syscall; ud2.
program = [49,192,102,140,200,131,224,3,131,248,3,117,22,72,161,0,0,0,16,0,0,0,0,72,137,199,184,60,0,0,0,15,5,15,11,191,99,0,0,0,184,60,0,0,0,15,5,15,11]
def fill(address, values):
  i = 0
  while i < len(values):
    value = values[i]
    unsafe:
      store8(as_ptr(address + i), value)
    i = i + 1
fill(ca, program)
fill(cb, program)
assert kpage.protect(a, code, 5)
assert kpage.protect(b, code, 5)
seen = 0
status = 0
calls = 0
def stop(nr, x1, x2, x3, x4, x5, x6):
  global seen, status, calls
  assert nr == 60
  seen = cr3()
  status = x1
  calls = calls + 1
  user_stop()
  return 0
ksyscall.register(stop)
set_cr3(a)
enter_user(code, kuser.build_frame(code, stack + 4096))
set_cr3(original)
assert seen == a and status == 111 and calls == 1
set_cr3(b)
enter_user(code, kuser.build_frame(code, stack + 4096))
set_cr3(original)
assert seen == b and status == 222 and calls == 2
ksyscall.start()
assert cr3() == original
assert kpage.entry_get(pa, 0) == 111
assert kpage.entry_get(pb, 0) == 222
assert kpage.pte_get(original, code) & 4 == 0
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
print('address-space gates passed: private low mappings, ring3CS/marker/syscall checks in two roots, zero frames, two-root CR3 roundtrip, original table untouched, native whole image')
