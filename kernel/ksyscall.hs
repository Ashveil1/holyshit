# ring 3 syscalls — the numbers the x64 backend already emits for hosted
# programs (write=1, mmap=9, exit=60), so any `hs.py xbuild` binary can run
# as a user program with no extra runtime support.
#
# The stub in x64gen parks all GPRs, calls handler(nr, a1..a6) like any other
# function (caps in r15) and returns the result in the user's rax; user_stop()
# from inside the handler ends the round trip instead. Helpers come before
# their users: the x64 backend resolves module-level names statically.

import kpage
import kpmm

SYS_WRITE = 1
SYS_MMAP = 9
SYS_EXIT = 60

# user pages live in PML4 slot 1 and up, so a user address space can be built
# without ever touching the kernel half (PML4[0])
USER_BIAS = 0x80000000000
PAGE = 4096

EINVAL = 22
EBADF = 9
ENOMEM = 12

# anonymous mappings are handed out from here, page by page, upward
brk = USER_BIAS + 0x10000000

handler = null
n_calls = 0
last_nr = 0
last_arg = 0
exit_code = 0
stopped = false
mapped_pages = 0

def round_up(n):
  # round to the next page (safe `/` is Float, so do the math in unsafe)
  unsafe:
    I64 x = n + PAGE - 1
    return x & ~(PAGE - 1)

def register(f):
  global handler
  syscall_register(f)
  handler = f
  return true

def unregister():
  global handler
  syscall_register(null)
  handler = null
  return true

def registered():
  return handler != null

def calls():
  return n_calls

def last_syscall():
  return last_nr

def user_exit_code():
  return exit_code

def user_stopped():
  return stopped

def pages_mapped():
  return mapped_pages

def map_user_pages(vaddr, nbytes, flags):
  # map [vaddr, vaddr+nbytes) for ring 3; returns pages mapped
  global mapped_pages
  n = 0
  off = 0
  while off < nbytes:
    p = kpmm.alloc(1)
    if p == 0:
      return n
    if kpage.map(cr3(), vaddr + off, p, flags):
      mapped_pages = mapped_pages + 1
      n = n + 1
    else:
      kpmm.free(p)
      return n
    off = off + PAGE
  return n

def sys_write(fd, buf, n):
  # write(fd, buf, len): fd 1 and 2 go to the serial line. The buffer belongs
  # to the user, so it is copied through read_mem and echoed as one Str.
  if fd != 1 and fd != 2:
    return -EBADF
  if n <= 0:
    return 0
  print read_mem(buf, n)
  return n

def sys_mmap(addr, len, prot, flags, fd, off):
  # mmap(addr, len, prot=3, flags, fd=-1, off=0): anonymous rw mapping.
  # The kernel picks the address; a user address is never honoured.
  global brk
  if len <= 0:
    return -EINVAL
  size = round_up(len)
  start = brk
  got = map_user_pages(start, size, 7)
  if got * PAGE < size:
    return -ENOMEM
  brk = start + got * PAGE
  return start

def sys_exit(code):
  # exit_group / exit: remember the code and end the user program. The stub
  # tags every register word, so `code` already is the original word as an
  # hs Int — except a real user program passes its hs return value, which
  # may itself be tagged (usually Null). Interpret what is left.
  global exit_code, stopped
  if code == 3:
    code = 0
  elif code & 3 == 1:
    code = code >> 2
  exit_code = code
  stopped = true
  user_stop()
  return 0

def dispatch(nr, a1, a2, a3, a4, a5, a6):
  # the stub tags every register word on entry, so the slots already hold
  # the original words as plain hs Ints — use them directly
  global n_calls, last_nr, last_arg
  n_calls = n_calls + 1
  last_nr = nr
  last_arg = a1
  if nr == SYS_WRITE:
    return sys_write(a1, a2, a3)
  if nr == SYS_MMAP:
    return sys_mmap(a1, a2, a3, a4, a5, a6)
  if nr == SYS_EXIT:
    return sys_exit(a1)
  return -38

def start():
  # hook dispatch() into the ring-3 entry stub
  return register(dispatch)