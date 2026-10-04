# file syscalls without ring 3: exercise sys_open/read/write/close/copy_out
# directly (no keyboard timing involved)
import kmb
import kpmm
import ksyscall
import kvfs
import kramdisk
import kuser

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

def kbuf(n):
  unsafe:
    Ptr p = alloc(n)
    return as_int(p)

expect("boot", kmb.usable(), true)
expect("pmm", kpmm.init() > 0, true)
expect("vfs", kvfs.vfs_init(), true)
expect("rd", kramdisk.load() > 0, true)
expect("handler", ksyscall.start(), true)

mp = kuser.payload_addr("/motd")
expect("open r", ksyscall.sys_open(mp, 5, 0), 3)
b = kbuf(64)
expect("read 39", ksyscall.sys_read(3, b, 64), 39)
expect("content", read_mem(b, 39), kvfs.read("/motd"))
expect("eof", ksyscall.sys_read(3, b, 64), 0)
expect("close", ksyscall.sys_close(3), 0)
expect("read closed", ksyscall.sys_read(3, b, 64), -9)
expect("open missing", ksyscall.sys_open(mp, 5, 0) >= 0, true)
expect("write new", ksyscall.sys_open(kuser.payload_addr("/w.txt"), 6, 1) >= 3, true)
print "fails", fails
print "kiotest-done"