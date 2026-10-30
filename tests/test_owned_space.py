#!/usr/bin/env python3
"""Two private low virtual mappings with live CR3 round trips on QEMU."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu:
 if os.environ.get('HS_REQUIRE_KOWNED')=='1':raise SystemExit('QEMU required')
 print('skip address space: QEMU unavailable');sys.exit(0)
env=dict(os.environ,HSPATH=f'{ROOT}:{ROOT}/kernel:{ROOT}/selfhost:{ROOT}/selfhost/be',HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as temp:
 d=Path(temp);s=d/'space.holy';s.write_text('''import kowned
import kpage
import kpmm
import kuser
assert kpmm.init() > 0
kowned.init()
original = cr3()
original_entry = kpage.pte_get(original, kowned.LOW)
base = kpmm.available()
kernel_value = kpage.entry_get(0x100000, 0)
def marker():
  unsafe:
    return as_int(alloc(16))
# Failure budget covers each clone and first-map allocation boundary.
for budget in range(6):
  kowned.set_budget(budget)
  h = kowned.create()
  if h != 0:
    before_map = kpmm.available()
    before = kpage.pte_get(kowned.root(h), kowned.LOW)
    p = kowned.map_user(h, kowned.LOW)
    if p == 0:
      assert kpmm.available() == before_map
      assert kpage.pte_get(kowned.root(h), kowned.LOW) == before
    assert kowned.destroy(h)
  assert kpmm.available() == base
kowned.set_budget(-1)
start = marker()
i = 0
while i < 100:
  h = kowned.create()
  assert h != 0
  r = kowned.root(h)
  p = kowned.map_user(h, kowned.LOW)
  q = kowned.map_user(h, kowned.LOW + 4096)
  assert p != 0 and q != 0 and p != q
  assert kpage.entry_get(p, 0) == 0
  assert kowned.map_user(h, kowned.LOW) == 0
  assert kowned.map_user(h, kowned.HIGH) == 0
  assert kowned.map_user(h, kowned.LOW + 1) == 0
  assert kowned.map_user(original, kowned.LOW) == 0
  set_cr3(r)
  assert not kowned.destroy(h)
  kuser.poke(kowned.LOW, 1234)
  set_cr3(original)
  assert kpage.entry_get(p, 0) == 1234
  assert kowned.destroy(h)
  assert not kowned.destroy(h)
  assert kowned.root(h) == 0
  assert kpmm.available() == base
  i = i + 1
end = marker()
assert end - start == 16
# Two concurrent slots, exhaustion and generation-protected stale handle.
a = kowned.create()
b = kowned.create()
assert a != 0 and b != 0 and a != b
assert kowned.create() == 0
assert kowned.destroy(a)
c = kowned.create()
assert c != a
assert not kowned.destroy(a)
assert kowned.map_user(a, kowned.LOW) == 0
# Failure on an already split table must preserve earlier mappings too.
p = kowned.map_user(c, kowned.LOW)
assert p != 0
before = kpmm.available()
kowned.set_budget(0)
assert kowned.map_user(c, kowned.LOW + 4096) == 0
assert kpmm.available() == before
assert kpage.translate(kowned.root(c), kowned.LOW) == p
kowned.set_budget(-1)
assert kowned.destroy(b)
assert kowned.destroy(c)
assert kpmm.available() == base
assert cr3() == original
assert kpage.pte_get(original, kowned.LOW) == original_entry
assert kpage.entry_get(0x100000, 0) == kernel_value
print "OWNED SPACE DONE"
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
   if b'OWNED SPACE DONE' in out or b'error:' in out:break
   time.sleep(.1)
  assert out==b'OWNED SPACE DONE\n',out
 finally:p.kill();p.wait()
print('owned-space gates passed:100 cycles, allocation-budget unwind, frame baseline, stable bump marker, active/stale/unknown refusal, native image')
