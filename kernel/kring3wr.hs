# ring-3 write() returns to ring 3, then exit() stops: the return iretq
# path with a tiny state change (no big mappings to blame)
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

def byte_at(addr, i):
  unsafe:
    return load8(as_ptr(addr) + i)

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
MSG_AT = 64

# mov eax,1 / mov edi,1 / movabs rsi,CODE+64 / mov edx,5 / syscall
# mov eax,60 / mov edi,7 / syscall / hlt
STUB = [0xB8, 0x01, 0, 0, 0, 0xBF, 0x01, 0, 0, 0, 0x48, 0xBE]
STUB2 = [0xBA, 0x05, 0, 0, 0, 0x0F, 0x05]
STUB3 = [0xB8, 0x3C, 0, 0, 0, 0xBF, 0x07, 0, 0, 0, 0x0F, 0x05, 0xF4]

expect("pmm", kpmm.init() > 0, true)
expect("map code", ksyscall.map_user_pages(CODE, PAGE, 7), 1)
expect("map stack", ksyscall.map_user_pages(STACK, PAGE, 7), 1)
fill(CODE, STUB)
# append the 64-bit message address (little-endian) after the movabs opcode
addr = CODE + MSG_AT
fill(CODE + 12, [addr & 255, addr >> 8 & 255, addr >> 16 & 255, addr >> 24 & 255, addr >> 32 & 255, addr >> 40 & 255, addr >> 48 & 255, addr >> 56 & 255])
fill(CODE + 20, STUB2)
fill(CODE + 27, STUB3)
fill(CODE + MSG_AT, [104, 101, 108, 108, 111])
expect("msg bytes", byte_at(CODE + MSG_AT, 0), 104)
expect("msg tail", byte_at(CODE + MSG_AT + 4, 0), 111)
expect("movabs op", byte_at(CODE + 10, 0), 0x48)
expect("movabs rsi", byte_at(CODE + 11, 0), 0xBE)
expect("addr lo", byte_at(CODE + 12, 0), addr & 255)
expect("addr hi", byte_at(CODE + 19, 0), addr >> 56 & 255)
expect("syscall op", byte_at(CODE + 25, 0), 0x0F)
expect("mov eax", byte_at(CODE + 0, 0), 0xB8)
expect("nr 1", byte_at(CODE + 1, 0), 0x01)
expect("mov edi", byte_at(CODE + 5, 0), 0xBF)
expect("fd 1", byte_at(CODE + 6, 0), 0x01)
expect("mov edx", byte_at(CODE + 20, 0), 0xBA)
expect("len 5", byte_at(CODE + 21, 0), 0x05)
expect("handler", ksyscall.start(), true)
enter_user(CODE, kuser.build_frame(CODE, STACK + PAGE))
expect("two syscalls", ksyscall.calls(), 2)
expect("last was exit", ksyscall.last_syscall(), ksyscall.SYS_EXIT)
expect("exit 7", ksyscall.user_exit_code(), 7)
expect("stopped", ksyscall.user_stopped(), true)
print "fails", fails
print "kring3wr-done"