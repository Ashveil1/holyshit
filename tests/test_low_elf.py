#!/usr/bin/env python3
"""Same static ELF on host Linux and native kernel, bounded experimental ABI."""
from pathlib import Path
import os, platform, shutil, subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu or not shutil.which('as') or not shutil.which('ld') or platform.machine()!='x86_64':
    if os.environ.get('HS_REQUIRE_LOWELF')=='1':raise SystemExit('required Linux static prerequisites unavailable')
    print('skip Linux static personality: x64 host/as/ld/QEMU required');sys.exit(0)
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
msg: .ascii "low-elf!!"
.section .bss
.lcomm blank,8
'''
with tempfile.TemporaryDirectory() as temp:
 d=Path(temp);s=d/'fixture.s';s.write_text(ASM);obj=d/'fixture.o';elf=d/'fixture'
 subprocess.run(['as','--64',str(s),'-o',str(obj)],check=True)
 subprocess.run(['ld','-static','-nostdlib','-z','max-page-size=4096','-Ttext-segment=0x10000000',str(obj),'-o',str(elf)],check=True)
 before=elf.read_bytes();host=subprocess.run([str(elf)],capture_output=True)
 assert host.returncode==5 and host.stdout==b'low-elf!!',(host.returncode,host.stdout)
 source=d/'boot.holy';source.write_text('''import kmb
import kpmm
import kpage
import kuser
import klowelf
assert kpmm.init() > 0
original = cr3()
base = kmb.mod_start(0)
size = kmb.mod_len(0)
assert not klowelf.validate(base, 63)
assert not klowelf.validate(base, 128)
def reject_byte(offset, value):
  old = klowelf.byte(base, offset)
  unsafe:
    store8(as_ptr(base + offset), value)
  assert not klowelf.validate(base, size)
  unsafe:
    store8(as_ptr(base + offset), old)
for change in [[4,1],[5,2],[16,3],[18,3],[52,63],[54,55],[56,0],[56,9]]:
  reject_byte(change[0], change[1])
first = kmb.rd64(base + 32)
reject_byte(first, 3)
reject_byte(first + 4, 7)
old = kmb.rd64(base + first + 16)
kuser.poke(base + first + 16, 0x400000)
assert not klowelf.validate(base, size)
kuser.poke(base + first + 16, old)
old = kmb.rd64(base + first + 32)
kuser.poke(base + first + 32, size + 1)
assert not klowelf.validate(base, size)
kuser.poke(base + first + 32, old)
old = kmb.rd64(base + 24)
kuser.poke(base + 24, klowelf.HIGH)
assert not klowelf.validate(base, size)
kuser.poke(base + 24, old)
code_before = kpage.pte_get(original, 0x10001000)
stack_before = kpage.pte_get(original, klowelf.STACK)
assert klowelf.load_image(base, size)
assert not klowelf.load_image(base, size)
assert klowelf.root != original
assert cr3() == original
assert kpage.pte_get(original, 0x10001000) == code_before
assert kpage.pte_get(klowelf.root, 0x10001000) & 4 != 0
assert kpage.pte_get(klowelf.root, 0x10001000) & 2 == 0
assert kpage.pte_get(klowelf.root, klowelf.STACK) & 6 == 6
assert kpage.pte_get(klowelf.root, 0x100000) & 4 == 0
print "LOW ELF BEGIN"
assert klowelf.run()
assert not klowelf.run()
assert cr3() == original
assert klowelf.seen_root == klowelf.root
assert kpage.pte_get(original, 0x10001000) == code_before
assert kpage.pte_get(original, klowelf.STACK) == stack_before
print "LOW ELF END", klowelf.exit_code, klowelf.n_calls
assert klowelf.exit_code == 5
assert klowelf.n_calls == 4
print "LOW ELF DONE"
''')
 kernel=d/'kernel';native=d/'native';driver=d/'driver'
 subprocess.run([sys.executable,str(ROOT/'hs.py'),'xkernel',str(source),'-o',str(kernel)],env=env,capture_output=True,check=True,timeout=90)
 subprocess.run([str(ROOT/'bootstrap/hs-hosted-x86_64'),str(ROOT/'selfhost/be/kernel_ir.holy'),str(driver)],env=env,capture_output=True,check=True,timeout=240)
 subprocess.run([str(driver),str(source),str(native)],env=env,capture_output=True,check=True,timeout=90)
 assert kernel.read_bytes()==native.read_bytes(),'native/reference whole kernel mismatch'
 serial=d/'serial';p=subprocess.Popen([qemu,'-kernel',str(kernel),'-initrd',str(elf),'-serial','file:'+str(serial),'-display','none','-monitor','none','-nic','none'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  deadline=time.monotonic()+30;out=b''
  while time.monotonic()<deadline:
   out=serial.read_bytes() if serial.exists() else b''
   if b'LOW ELF DONE' in out or b'error:' in out:break
   time.sleep(.1)
  assert out==b'LOW ELF BEGIN\nlow-elf!!LOW ELF END 5 4\nLOW ELF DONE\n',out
 finally:p.kill();p.wait()
 assert elf.read_bytes()==before,'fixture modified between host and guest'
print('private-root low ELF gates passed: same ELF host/guest, ring3, bounds, errno/BSS, original root restored, native image')
