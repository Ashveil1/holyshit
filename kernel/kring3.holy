# ring 3 without an ELF: a hand-assembled user page runs `exit(7)` through
# the syscall stub, which must land the kernel back in the caller.
import kmb
import kpmm
import kpage
import ksyscall
import kuser

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

def byte_at(addr, i):
  unsafe:
    return load8(as_ptr(addr) + i)

def fill(addr, bytes):
  # no loops inside `unsafe:` -- write one byte at a time from safe code
  i = 0
  while i < len(bytes):
    b = bytes[i]
    unsafe:
      store8(as_ptr(addr) + i, b)
    i = i + 1

PAGE = 4096
CODE = ksyscall.USER_BIAS + 0x40000
STACK = ksyscall.USER_BIAS + 0x80000

# mov eax,60 / mov edi,7 / syscall / hlt / ud2
STUB = [0xB8, 0x3C, 0, 0, 0, 0xBF, 0x07, 0, 0, 0, 0x0F, 0x05, 0xF4, 0x0F, 0x0B]

expect("boot info", kmb.usable(), true)
expect("pmm ready", kpmm.init() > 0, true)
expect("code page mapped", ksyscall.map_user_pages(CODE, PAGE, 7), 1)
expect("stack page mapped", ksyscall.map_user_pages(STACK, PAGE, 7), 1)
fill(CODE, STUB)
expect("kernel half is not user", kpage.is_mapped(cr3(), CODE), true)

expect("handler registered", ksyscall.start(), true)
expect("before: no syscalls", ksyscall.calls(), 0)
expect("before: not stopped", ksyscall.user_stopped(), false)

expect("code bytes written", byte_at(CODE, 0), 0xB8)
expect("code bytes 2", byte_at(CODE, 1), 0x3C)
expect("stack readable", byte_at(STACK + PAGE - 1, 0), 0)
FRAME = kuser.build_frame(CODE, STACK + PAGE)
expect("frame rip", byte_at(FRAME, 0), 0x00)
expect("frame rip low", byte_at(FRAME, 0), CODE % 256)
expect("frame cs", byte_at(FRAME, 8), 0x23)
expect("frame rflags", byte_at(FRAME, 16), 2)
expect("frame ss", byte_at(FRAME, 32), 0x1B)
expect("pre-enter calls", ksyscall.calls(), 0)
enter_user(CODE, FRAME)
expect("post code byte", byte_at(CODE, 0), 0xB8)
expect("post code byte 12", byte_at(CODE, 12), 0xF4)

expect("syscall served", ksyscall.calls(), 1)
expect("last syscall", ksyscall.last_syscall(), ksyscall.SYS_EXIT)
expect("exit code", ksyscall.user_exit_code(), 7)
expect("user stopped", ksyscall.user_stopped(), true)
expect("back in the kernel", cr3() != 0, true)

print "fails", fails
print "kring3-done"