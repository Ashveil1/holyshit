# return to ring 3 via sysret: the handler prints proof it ran and returns
# 0, the stub resumes the user past its syscall, and the user hits hlt —
# privileged at CPL3, so the kernel reports EXC 13 with the USER rip and
# halts. Nothing after enter_user runs; the harness asserts ret-ok + EXC.
import kmb
import kpmm
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

def dumb(nr, a1, a2, a3, a4, a5, a6):
  print "ret-ok"
  return 0

def fill(addr, bytes):
  i = 0
  while i < len(bytes):
    b = bytes[i]
    unsafe:
      store8(as_ptr(addr) + i, b)
    i = i + 1

PAGE = 4096
CODE = ksyscall.USER_BIAS + 0x40000
STACK = ksyscall.USER_BIAS + 0x80000
# mov eax,1 / mov edi,1 / mov esi,2 / mov edx,3 / syscall / hlt / ud2
STUB = [0xB8, 0x01, 0, 0, 0, 0xBF, 0x01, 0, 0, 0, 0xBE, 0x02, 0, 0, 0, 0xBA, 0x03, 0, 0, 0, 0x0F, 0x05, 0xF4, 0x0F, 0x0B]

expect("pmm", kpmm.init() > 0, true)
expect("map code", ksyscall.map_user_pages(CODE, PAGE, 7), 1)
expect("map stack", ksyscall.map_user_pages(STACK, PAGE, 7), 1)
fill(CODE, STUB)
syscall_register(dumb)
enter_user(CODE, kuser.build_frame(CODE, STACK + PAGE))
print "FAIL: returned past user hlt"
print "fails", fails