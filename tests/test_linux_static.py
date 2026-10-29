#!/usr/bin/env python3
"""Same static ELF on host Linux and native kernel, bounded experimental ABI."""
from pathlib import Path
import os, platform, shutil, subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parent.parent
qemu=os.environ.get('HS_TEST_QEMU') or shutil.which('qemu-system-x86_64')
if not qemu or not shutil.which('as') or not shutil.which('ld') or platform.machine()!='x86_64':
    if os.environ.get('HS_REQUIRE_LINUX_STATIC')=='1':raise SystemExit('required Linux static prerequisites unavailable')
    print('skip Linux static personality: x64 host/as/ld/QEMU required');sys.exit(0)
env=dict(os.environ,HSPATH=f'{ROOT}:{ROOT}/kernel:{ROOT}/selfhost:{ROOT}/selfhost/be',HSROOT=str(ROOT))
ASM='''
.global _start
.section .text
_start:
 # Linux startup ABI: aligned rsp, argc, argv/envp NULL boundaries, auxv.
 test $15,%rsp
 jne bad
 cmpq $2,(%rsp)
 jne bad
 mov 8(%rsp),%rsi
 cmpl $0x74786966,(%rsi)
 jne bad
 mov 16(%rsp),%rsi
 cmpl $0x6c696174,(%rsi)
 jne bad
 cmpb $0,4(%rsi)
 jne bad
 cmpq $0,24(%rsp)
 jne bad
 mov 32(%rsp),%rsi
 cmpl $0x505f5348,(%rsi)
 jne bad
 cmpq $0,40(%rsp)
 jne bad
 lea 48(%rsp),%rsi
 xor %r8d,%r8d
aux:
 mov (%rsi),%rax
 test %rax,%rax
 jz auxdone
 cmp $9,%rax
 jne pagesize
 lea _start(%rip),%rdx
 cmp %rdx,8(%rsi)
 jne bad
 or $2,%r8d
pagesize:
 cmp $6,%rax
 jne next
 cmpq $4096,8(%rsi)
 jne bad
 or $1,%r8d
next:
 add $16,%rsi
 jmp aux
auxdone:
 cmp $3,%r8d
 jne bad
 # Unsupported syscall and bad FD must return Linux negative errno.
 mov $999,%eax
 syscall
 cmp $-38,%rax
 jne bad
 mov $1,%eax
 mov $9,%edi
 xor %esi,%esi
 mov $1,%edx
 syscall
 cmp $-9,%rax
 jne bad
 # NULL pointer is rejected without a guest fault.
 mov $1,%eax
 mov $1,%edi
 xor %esi,%esi
 mov $1,%edx
 syscall
 cmp $-14,%rax
 jne bad
 # BSS must be zero, not reused physical frame contents.
 lea blank(%rip),%rsi
 cmpq $0,(%rsi)
 jne bad
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
msg: .ascii "linux-ok!"
.section .bss
.lcomm blank,8
'''
with tempfile.TemporaryDirectory() as temp:
 d=Path(temp);s=d/'fixture.s';s.write_text(ASM);obj=d/'fixture.o';elf=d/'fixture'
 subprocess.run(['as','--64',str(s),'-o',str(obj)],check=True)
 subprocess.run(['ld','-static','-nostdlib','-z','max-page-size=4096','-Ttext-segment=0x80000400000',str(obj),'-o',str(elf)],check=True)
 before=elf.read_bytes();host=subprocess.run(['fixture','tail'],executable=str(elf),env={'HS_PROBE':'ok'},capture_output=True)
 assert host.returncode==5 and host.stdout==b'linux-ok!',(host.returncode,host.stdout)
 source=d/'boot.holy';source.write_text('''import kmb
import kpmm
import kuser
import klinux
assert kpmm.init() > 0
base = kmb.mod_start(0)
size = kmb.mod_len(0)
assert not klinux.validate(base, 63)
assert not klinux.validate(base, 128)
# Mutate and restore the actual boot module for negative loader checks.
def reject_byte(offset, value):
  old = klinux.byte(base, offset)
  unsafe:
    store8(as_ptr(base + offset), value)
  assert not klinux.validate(base, size)
  unsafe:
    store8(as_ptr(base + offset), old)
for change in [[4,1],[5,2],[16,3],[18,3],[52,63],[54,55],[56,0],[56,9]]:
  reject_byte(change[0],change[1])
first = kmb.rd64(base + 32)
reject_byte(first,3)
reject_byte(first + 4,7)
old = kmb.rd64(base + first + 16)
kuser.poke(base + first + 16, 0x400000)
assert not klinux.validate(base, size)
kuser.poke(base + first + 16, old)
old = kmb.rd64(base + first + 32)
kuser.poke(base + first + 32, size + 1)
assert not klinux.validate(base, size)
kuser.poke(base + first + 32, old)
assert klinux.validate(base, size)
assert klinux.load_image(base, size)
assert not klinux.readable(0, 1)
assert not klinux.readable(klinux.entry_point, -1)
assert not klinux.readable(klinux.entry_point, 65537)
# Empty-vector compatibility path and bounds failures cannot alter the stack.
empty = klinux.initial_stack([], [])
assert empty % 16 == 0
assert kmb.rd64(empty) == 0
assert kmb.rd64(empty + 8) == 0
assert kmb.rd64(empty + 16) == 0
assert kmb.rd64(empty + 24) == 6
assert kmb.rd64(empty + 32) == 4096
marker = klinux.STACK + 100
kuser.poke(marker, 12345)
badbuf = "abc"
unsafe:
  p = as_int(as_ptr(badbuf)) + 16
  store8(as_ptr(p + 1), 0)
assert klinux.initial_stack([badbuf], []) == 0
assert kmb.rd64(marker) == 12345
print "LINUX BEGIN"
assert klinux.initial_stack(["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"], []) == 0
many = []
for i in range(17):
  append(many, "a")
assert not klinux.run_with(many, [])
large = []
for i in range(9):
  append(large, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
assert klinux.vector_bytes(large, []) == -1
assert klinux.run_with(["fixture", "tail"], ["HS_PROBE=ok"])
print "LINUX END", klinux.exit_code, klinux.n_calls
assert klinux.exit_code == 5
assert klinux.n_calls == 5
print "LINUX DONE"
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
   if b'LINUX DONE' in out or b'error:' in out:break
   time.sleep(.1)
  assert out==b'LINUX BEGIN\nlinux-ok!LINUX END 5 5\nLINUX DONE\n',out
 finally:p.kill();p.wait()
 assert elf.read_bytes()==before,'fixture modified between host and guest'
print('Linux static startup gates passed: argc/argv/envp/auxv/alignment/bounds, same ELF host/guest, byte-exact write, raw exit5, errno, BSS, whole native kernel equality')
