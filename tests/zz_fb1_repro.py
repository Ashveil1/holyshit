#!/usr/bin/env python3
"""Owned ELF lifecycle: same static ELF on host Linux and 100 owned load/run/exit cycles on QEMU."""
from pathlib import Path
import os, platform, shutil, subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu or not shutil.which('as') or not shutil.which('ld') or platform.machine()!='x86_64':
    if os.environ.get('HS_REQUIRE_OWNEDELF')=='1':raise SystemExit('required Linux static prerequisites unavailable')
    print('skip owned ELF lifecycle: x64 host/as/ld/QEMU required');sys.exit(0)
env=dict(os.environ,HSPATH=f'{ROOT}:{ROOT}/kernel:{ROOT}/selfhost:{ROOT}/selfhost/be',HSROOT=str(ROOT))
ASM='''
.global _start
.section .text
_start:
 xor %eax,%eax
 mov %cs,%ax
 and $3,%eax
 cmp $3,%eax
 jne bad
 mov $999,%eax
 syscall
 cmp $-38,%rax
 jne bad
 mov $1,%eax
 mov $1,%edi
 xor %esi,%esi
 mov $1,%edx
 syscall
 cmp $-14,%rax
 jne bad
 lea blank(%rip),%rsi
 cmpq $0,(%rsi)
 jne bad
 movq $123,(%rsi)
 mov $1,%eax
 mov $1,%edi
 lea msg(%rip),%rsi
 mov $9,%edx
 syscall
 cmp $9,%rax
 jne bad
 mov $60,%eax
 mov $5,%edi
 syscall
bad:
 mov $60,%eax
 mov $99,%edi
 syscall
.section .rodata
msg: .ascii "ownedelf!"
.section .bss
.lcomm blank,8
'''
# Faulting guests for the containment gates: each must be killed and
# reclaimed while the kernel survives. If the fault does not fire the
# guest falls through to exit(99), which the assertions below reject.
ASM_PF='''
.global _start
.section .text
_start:
 mov $0xDEADBEEF,%eax
 mov (%rax),%bl
 mov $60,%eax
 mov $99,%edi
 syscall
'''
ASM_DE='''
.global _start
.section .text
_start:
 xor %edx,%edx
 mov $1,%eax
 xor %ecx,%ecx
 div %ecx
 mov $60,%eax
 mov $99,%edi
 syscall
'''
ASM_GP='''
.global _start
.section .text
_start:
 mov $0x3F8,%edx
 out %al,(%dx)
 mov $60,%eax
 mov $99,%edi
 syscall
'''
def build_elf(d,name,asm_text):
 s=d/(name+'.s');s.write_text(asm_text);obj=d/(name+'.o');out=d/name
 subprocess.run(['as','--64',str(s),'-o',str(obj)],check=True)
 subprocess.run(['ld','-static','-nostdlib','-z','max-page-size=4096','-Ttext-segment=0x10000000',str(obj),'-o',str(out)],check=True)
 return out
with __import__('contextlib').nullcontext('/tmp/fb1work') as temp:
 d=Path(temp);elf=build_elf(d,'fixture',ASM)
 pfe=build_elf(d,'faultpf',ASM_PF);dee=build_elf(d,'faultde',ASM_DE);gpe=build_elf(d,'faultgp',ASM_GP)
 before=elf.read_bytes();host=subprocess.run([str(elf)],capture_output=True)
 assert host.returncode==5 and host.stdout==b'ownedelf!',(host.returncode,host.stdout)
 for _ in range(3):
  again=subprocess.run([str(elf)],capture_output=True)
  assert again.returncode==5 and again.stdout==b'ownedelf!',(again.returncode,again.stdout)
 source=d/'boot.holy';source.write_text('''import kmb
import kpmm
import kpage
import kowned
import kuser
import kownedelf
assert kpmm.init() > 0
assert kowned.init()
assert kownedelf.init()
original = cr3()
kernel_value = kpage.entry_get(0x100000, 0)
original_low_pte = kpage.pte_get(original, kowned.LOW)
base = kmb.mod_start(0)
size = kmb.mod_len(0)
assert not kownedelf.validate(base, 63)
assert not kownedelf.validate(base, 128)
assert kownedelf.state() == kownedelf.EMPTY
def reject_byte(offset, value):
  old = kownedelf.byte(base, offset)
  unsafe:
    store8(as_ptr(base + offset), value)
  assert not kownedelf.validate(base, size)
  unsafe:
    store8(as_ptr(base + offset), old)
for change in [[4,1],[5,2],[16,3],[18,3],[52,63],[54,55],[56,0],[56,9]]:
  reject_byte(change[0], change[1])
first = kmb.rd64(base + 32)
reject_byte(first, 3)
reject_byte(first + 4, 7)
old = kmb.rd64(base + first + 16)
kuser.poke(base + first + 16, 0x400000)
assert not kownedelf.validate(base, size)
kuser.poke(base + first + 16, kownedelf.CODE_HIGH)
assert not kownedelf.validate(base, size)
kuser.poke(base + first + 16, kownedelf.STACK)
assert not kownedelf.validate(base, size)
kuser.poke(base + first + 16, old)
old = kmb.rd64(base + first + 32)
kuser.poke(base + first + 32, size + 1)
assert not kownedelf.validate(base, size)
kuser.poke(base + first + 32, old)
old = kmb.rd64(base + 24)
kuser.poke(base + 24, kownedelf.CODE_HIGH)
assert not kownedelf.validate(base, size)
kuser.poke(base + 24, old)
assert kownedelf.state() == kownedelf.EMPTY
frames_base = kpmm.available()
for budget in range(9):
  kowned.set_budget(budget)
  assert not kownedelf.prepare(base, size)
  assert kownedelf.state() == kownedelf.EMPTY
  assert kownedelf.active_handle() == 0
  assert kpmm.available() == frames_base
kowned.set_budget(-1)
assert kownedelf.prepare(base, size)
assert kownedelf.state() == kownedelf.READY
assert not kownedelf.prepare(base, size)
h = kownedelf.active_handle()
root = kowned.root(h)
assert root != 0
assert root != original
assert (kpage.pte_get(root, 0x10000000) & 7) == 5
assert (kpage.pte_get(root, 0x10001000) & 7) == 5
assert (kpage.pte_get(root, 0x10002000) & 7) == 5
assert (kpage.pte_get(root, 0x10003000) & 7) == 7
assert (kpage.pte_get(root, kownedelf.STACK) & 7) == 7
assert (kpage.pte_get(root, 0x101FE000) & 4) == 0
assert kpage.pte_get(original, kowned.LOW) == original_low_pte
# Teardown rejection must not lose the loader's ownership record. An active
# root cannot be destroyed; after restoring the boot root, discard can retry.
prepared_frames = kpmm.available()
prepared_spans = kownedelf.rd(kownedelf.metadata + kownedelf.OFF_NSPANS)
irq_off()
set_cr3(root)
assert not kownedelf.discard()
assert cr3() == root
assert kownedelf.state() == kownedelf.READY
assert kownedelf.active_handle() == h
assert kownedelf.rd(kownedelf.metadata + kownedelf.OFF_NSPANS) == prepared_spans
assert kowned.root(h) == root
assert kpmm.available() == prepared_frames
set_cr3(original)
irq_on()
assert kownedelf.discard()
assert kownedelf.state() == kownedelf.EMPTY
assert kownedelf.active_handle() == 0
assert kownedelf.rd(kownedelf.metadata + kownedelf.OFF_NSPANS) == 0
assert kpmm.available() == frames_base
assert not kowned.destroy(h)
assert not kownedelf.discard()
assert not kownedelf.run()
assert kpmm.available() == frames_base
def marker():
  unsafe:
    return as_int(alloc(16))
print "OWNED ELF BEGIN"
start = marker()
i = 0
while i < 100:
  assert kownedelf.prepare(base, size)
  assert kownedelf.run()
  assert kownedelf.exit_code() == 5
  assert kownedelf.calls() == 4
  assert kownedelf.seen_root() != 0
  assert kownedelf.seen_root() != original
  assert kownedelf.state() == kownedelf.EMPTY
  assert cr3() == original
  assert kpmm.available() == frames_base
  i = i + 1
end = marker()
print "OWNED ELF END"
assert end - start == 16
print "OWNED FAULT BEGIN"
assert kownedelf.prepare(kmb.mod_start(1), kmb.mod_len(1))
assert kownedelf.run()
assert kownedelf.fault_vector() == 14
assert kownedelf.state() == kownedelf.EMPTY
assert cr3() == original
assert kpmm.available() == frames_base
assert kownedelf.prepare(kmb.mod_start(2), kmb.mod_len(2))
assert kownedelf.run()
assert kownedelf.fault_vector() == 0
assert kownedelf.state() == kownedelf.EMPTY
assert cr3() == original
assert kpmm.available() == frames_base
assert kownedelf.prepare(kmb.mod_start(3), kmb.mod_len(3))
assert kownedelf.run()
assert kownedelf.fault_vector() == 13
assert kownedelf.state() == kownedelf.EMPTY
assert cr3() == original
assert kpmm.available() == frames_base
assert kownedelf.prepare(base, size)
assert kownedelf.run()
assert kownedelf.fault_vector() == -1
assert kownedelf.exit_code() == 5
assert kownedelf.state() == kownedelf.EMPTY
assert cr3() == original
assert kpmm.available() == frames_base
print "OWNED FAULT END"
assert kpage.entry_get(0x100000, 0) == kernel_value
assert kpage.pte_get(original, kowned.LOW) == original_low_pte
print "OWNED ELF DONE"
''')
 kernel=d/'kernel';native=d/'native';driver=d/'driver'
 subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(kernel)],env=env,capture_output=True,check=True,timeout=90)
 serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(kernel),'-initrd','{},{},{},{}'.format(elf,pfe,dee,gpe),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  deadline=time.monotonic()+60;out=b''
  want=b'OWNED ELF BEGIN\n'+b'ownedelf!'*100+b'OWNED ELF END\n'
  while time.monotonic()<deadline:
   out=serial.read_bytes() if serial.exists() else b''
   if b'OWNED ELF DONE' in out or b'error:' in out:
    __import__('time').sleep(5);out=serial.read_bytes() if serial.exists() else b'';open('/tmp/fb1-harness-full.log','wb').write(out);break
   time.sleep(.1)
  assert out.startswith(want),out[-400:]
  # containment gates: each fault is reported (EXC <vec> ... cr2=...), the
  # guest is killed and reclaimed, and the kernel runs on to the next one.
  rest=out[len(want):]
  for piece in (b'OWNED FAULT BEGIN\n',b'EXC 14 ',b'cr2=3735928559',b'EXC 0 ',b'EXC 13 ',b'ownedelf!',b'OWNED FAULT END\n',b'OWNED ELF DONE\n'):
   i=rest.find(piece)
   assert i>=0,(piece,out[-400:])
   rest=rest[i+len(piece):]
  assert rest==b'',out[-400:]
 finally:p.kill();p.wait()
 assert elf.read_bytes()==before,'fixture modified between host and guest'
print('owned ELF lifecycle gates passed:100 load/run/exit cycles reclaimed, allocation-budget unwind, malformed/discard/stale rejection, perms, native image, 3 contained ring-3 fault kills (#PF/#DE/#GP) reclaimed with the kernel alive')
