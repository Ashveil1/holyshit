# file syscalls without ring 3: exercise sys_open/read/write/close/copy_out
# directly (no keyboard timing involved). Buffers and paths live in real
# user pages (map_user_pages + poke), so the USER_BIAS checks in ksyscall
# run the same way they do for ring 3.
import kmb
import kpmm
import ksyscall
import kvfs
import kramdisk

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

def upoke(addr, s):
  # copy a kernel Str into already-mapped user memory
  n = len(s)
  unsafe:
    Ptr p = as_ptr(s)
    Ptr q = as_ptr(addr)
    I64 i = 0
    I64 o = 0
    while i < n:
      o = 16 + i
      store8(q + i, load8(p + o))
      i = i + 1
  return n

UBASE = ksyscall.USER_BIAS + 0x50000000
UPATH = UBASE
UPATH2 = UBASE + 256
UDATA = UBASE + 512
UROOT = UBASE + 768
UBUF = UBASE + 1024

expect("boot", kmb.usable(), true)
expect("pmm", kpmm.init() > 0, true)
expect("vfs", kvfs.vfs_init(), true)
expect("rd", kramdisk.load() > 0, true)
expect("handler", ksyscall.start(), true)
expect("user pages", ksyscall.map_user_pages(UBASE, 8192, 7), 2)
expect("poke motd", upoke(UPATH, "/motd"), 5)
expect("poke nope", upoke(UPATH2, "/nope"), 5)
expect("poke root", upoke(UROOT, "/"), 1)

expect("open r", ksyscall.sys_open(UPATH, 5, 0), 3)
expect("read 39", ksyscall.sys_read(3, UBUF, 64), 39)
expect("content", read_mem(UBUF, 39), kvfs.read("/motd"))
expect("eof", ksyscall.sys_read(3, UBUF, 64), 0)
expect("close", ksyscall.sys_close(3), 0)
expect("read closed", ksyscall.sys_read(3, UBUF, 64), -9)
expect("open missing", ksyscall.sys_open(UPATH2, 5, 0), -2)

expect("poke wpath", upoke(UPATH2, "/w.txt"), 6)
expect("poke wdata", upoke(UDATA, "hello"), 5)
wfd = ksyscall.sys_open(UPATH2, 6, 1)
expect("open w", wfd >= 3, true)
expect("write new", ksyscall.sys_write(wfd, UDATA, 5), 5)
expect("close w", ksyscall.sys_close(wfd), 0)
expect("written", kvfs.read("/w.txt"), "hello")

# kernel pointers must be rejected, never touched
expect("open kern path", ksyscall.sys_open(4096, 5, 0), -14)
expect("open null path", ksyscall.sys_open(0, 5, 0), -14)
expect("close kern fd", ksyscall.sys_close(4096), -9)
rbfd = ksyscall.sys_open(UPATH, 5, 0)
expect("reopen r", rbfd >= 3, true)
expect("read kern buf", ksyscall.sys_read(rbfd, 4096, 10), -14)
expect("close rbfd", ksyscall.sys_close(rbfd), 0)
expect("write kern buf", ksyscall.sys_write(1, 4096, 4), -14)
expect("ls root", ksyscall.sys_ls(UROOT, 1, UBUF, 64) > 0, true)
expect("ls kern buf", ksyscall.sys_ls(UROOT, 1, 4096, 64), -14)
expect("ls kern path", ksyscall.sys_ls(4096, 5, UBUF, 64), -14)

# zero-length never blocks (fd 0 would spin on readline otherwise)
expect("read0 zero", ksyscall.sys_read(0, UBUF, 0), 0)
expect("write zero", ksyscall.sys_write(1, UBUF, 0), 0)

# raw port I/O (the kernel has no `asm`; ioport_* is how ATA will talk to
# the disk controller). CMOS shadow RAM round-trips byte for byte.
ioport_out(0x70, 0x15, 1)
ioport_out(0x71, 0x5A, 1)
expect("port out/in 8", ioport_in(0x71, 1), 0x5A)
ioport_out(0x70, 0x16, 1)
ioport_out(0x71, 0xA5, 1)
expect("port out/in 8b", ioport_in(0x71, 1), 0xA5)
expect("port width 16", ioport_in(0xE9, 2), 0)
expect("port width 32", ioport_in(0xE9, 4), 0)
print "fails", fails
print "kiotest-done"
