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
import kvfs

SYS_READ = 0
SYS_WRITE = 1
SYS_OPEN = 2
SYS_CLOSE = 3
SYS_MMAP = 9
SYS_EXEC = 59
SYS_EXIT = 60
SYS_LS = 78
SYS_MKDIR = 83
SYS_UNLINK = 87

# user pages live in PML4 slot 1 and up, so a user address space can be built
# without ever touching the kernel half (PML4[0])
USER_BIAS = 0x80000000000
PAGE = 4096

EINVAL = 22
EBADF = 9
ENOMEM = 12
EFAULT = 14

# anonymous mappings are handed out from here, page by page, upward
brk = USER_BIAS + 0x10000000

handler = null
exec_fn = null
n_calls = 0
last_nr = 0
last_arg = 0
exit_code = 0
stopped = false
mapped_pages = 0
bs_cached = null

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

def user_range_ok(addr, n):
  # user memory lives at/above USER_BIAS; anything below is kernel memory
  # (or null) and must never be touched through a ring-3 pointer
  if n < 0:
    return false
  if addr < USER_BIAS:
    return false
  if addr + n < addr:
    return false
  return true

def sys_write(fd, buf, n):
  # write(fd, buf, len): fd 1 and 2 go to the serial line. The buffer belongs
  # to the user, so it is copied through read_mem and echoed as one Str.
  # NOTE: `print` appends one `\n` the caller did not write — fd 1/2 is a
  # serial line discipline, not byte-exact write(). Return value stays exact.
  if fd == 1 or fd == 2:
    if not user_range_ok(buf, n):
      return -EFAULT
    if n <= 0:
      return 0
    print read_mem(buf, n)
    return n
  # user fds start at 3 (0/1/2 are stdin/stdout/stderr); kvfs owns the table
  if fd < 3 or not kvfs.fd_valid(fd - 3):
    return -EBADF
  if not user_range_ok(buf, n):
    return -EFAULT
  if n <= 0:
    return 0
  wrote = kvfs.fwrite(fd - 3, read_mem(buf, n))
  if wrote < 0:
    return -EBADF
  return wrote

def copy_out(dst, s, n):
  # copy a kernel Str into user memory; returns bytes copied, -EFAULT when
  # the destination is not user memory
  if n <= 0:
    return 0
  if not user_range_ok(dst, n):
    return -EFAULT
  count = len(s)
  if count > n:
    count = n
  unsafe:
    I64 d = dst
    Ptr p = as_ptr(s)
    Ptr q = as_ptr(d)
    I64 i = 0
    I64 o = 0
    while i < count:
      o = 16 + i
      store8(q + i, load8(p + o))
      i = i + 1
  return count

def poke_bs():
  unsafe:
    Ptr p = alloc(8)
    store8(p, 8)
    return as_int(p)

def bs_char():
  # the one byte readkey can never spell as a literal (no \0..\8 escapes):
  # build it once from raw memory and keep it
  global bs_cached
  if bs_cached == null:
    bs_cached = read_mem(poke_bs(), 1)
  return bs_cached

def readline():
  # blocking line input for fd 0: spin on readkey with IRQs on (the stub
  # runs with IF clear, so without sti the keyboard IRQ never arrives).
  # No echo — the serial log stays assertion-friendly. Backspace pops.
  irq_on()
  out = ""
  bs = bs_char()
  while true:
    k = readkey()
    if k == null:
      continue
    if k == "\n":
      break
    if k == bs:
      if len(out) > 0:
        out = out[:len(out) - 1]
      continue
    out = out + k
  irq_off()
  return out

def sys_read(fd, buf, n):
  # read(fd, buf, len): fd 0 is the keyboard (one line, no newline);
  # files come from kvfs; returns bytes read, 0 at EOF
  if fd == 0:
    if n <= 0:
      return 0
    return copy_out(buf, readline(), n)
  if fd < 3 or not kvfs.fd_valid(fd - 3):
    return -EBADF
  if n <= 0:
    return 0
  return copy_out(buf, kvfs.fread(fd - 3, n), n)

def sys_open(path_ptr, path_len, flags):
  # open(path, len, flags): 0 = read (must exist), anything else =
  # write (create/truncate). Returns a user fd (kvfs fd + 3), -2 when the
  # path does not exist, -EFAULT when the path pointer is not user memory.
  if not user_range_ok(path_ptr, path_len):
    return -EFAULT
  path = read_mem(path_ptr, path_len)
  mode = "r"
  if flags != 0:
    mode = "w"
  kfd = kvfs.fopen(path, mode)
  if kfd < 0:
    return -2
  return kfd + 3

def sys_close(fd):
  if fd < 3 or not kvfs.fd_valid(fd - 3):
    return -EBADF
  if kvfs.fclose(fd - 3):
    return 0
  return -EBADF

def sys_unlink(path_ptr, path_len):
  if not user_range_ok(path_ptr, path_len):
    return -EFAULT
  if kvfs.unlink(read_mem(path_ptr, path_len)):
    return 0
  return -2

def sys_mkdir(path_ptr, path_len):
  if not user_range_ok(path_ptr, path_len):
    return -EFAULT
  if kvfs.mkdirs(read_mem(path_ptr, path_len)):
    return 0
  return -2

def sys_ls(path_ptr, path_len, buf, n):
  if not user_range_ok(path_ptr, path_len):
    return -EFAULT
  names = kvfs.ls(read_mem(path_ptr, path_len))
  if names == null:
    return -2
  if len(names) == 0:
    return 0
  return copy_out(buf, join("\n", names), n)

def sys_exec(path_ptr, path_len):
  # exec lives in kuser (importing it here would cycle ksyscall<->kuser),
  # so dispatch calls through the exec_fn hook kuser installs. One-shot by
  # construction: the new text usually overlaps the old one, so there is
  # no caller to come back to; on its exit the kernel resumes where the
  # old program entered.
  if exec_fn == null:
    return -38
  return exec_fn(path_ptr, path_len)

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
  if nr == SYS_READ:
    return sys_read(a1, a2, a3)
  if nr == SYS_OPEN:
    return sys_open(a1, a2, a3)
  if nr == SYS_CLOSE:
    return sys_close(a1)
  if nr == SYS_UNLINK:
    return sys_unlink(a1, a2)
  if nr == SYS_MKDIR:
    return sys_mkdir(a1, a2)
  if nr == SYS_LS:
    return sys_ls(a1, a2, a3, a4)
  if nr == SYS_EXEC:
    return sys_exec(a1, a2)
  return -38

def start():
  # hook dispatch() into the ring-3 entry stub
  return register(dispatch)