# filesystem on bare metal: ramdisk from the multiboot module plus live
# file operations end to end
import kmb
import kpmm
import kheap
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

expect("boot info found", kmb.usable(), true)
expect("one module", kmb.mods_count(), 1)
expect("module nonzero", kmb.mod_len(0) > 64, true)
expect("pmm ready", kpmm.init() > 0, true)
expect("heap ready", kheap.init(16), true)
expect("vfs init", kvfs.vfs_init(), true)

# the ramdisk image the test harness passes with -initrd
loaded = kramdisk.load()
expect("ramdisk loads", loaded, 4)
expect("motd", kvfs.read("/motd"), "holyshit test ramdisk\nsecond line here\n")
expect("hello", kvfs.read("/hello.txt"), "hello from a ramdisk file\n")
expect("nested config", kvfs.read("/etc/config"), "nested file in etc\n")
expect("root listing", kvfs.ls("/"), ["etc", "hello.txt", "motd"])
expect("etc listing", kvfs.ls("/etc"), ["config"])
expect("motd stat", kvfs.stat("/motd"), [0, 39])

# live operations on top of the ramdisk contents
expect("mkdir", kvfs.mkdir("/tmp"), true)
expect("write new", kvfs.write("/tmp/note.txt", "hello"), true)
expect("read new", kvfs.read("/tmp/note.txt"), "hello")
expect("overwrite motd copy", kvfs.write("/tmp/note.txt", "bye"), true)
expect("ramdisk file untouched", kvfs.read("/motd") == "holyshit test ramdisk\nsecond line here\n", true)

fd = kvfs.fopen("/tmp/log.txt", "w")
expect("open w", fd >= 0, true)
expect("fwrite", kvfs.fwrite(fd, "line1\nline2\n"), 12)
expect("fseek", kvfs.fseek(fd, 0), 0)
expect("fread", kvfs.fread(fd, 20), "line1\nline2\n")
expect("fclose", kvfs.fclose(fd), true)
expect("log content", kvfs.read("/tmp/log.txt"), "line1\nline2\n")

expect("unlink nested", kvfs.unlink("/etc/config"), true)
expect("unlink dir now empty", kvfs.unlink("/etc"), true)
expect("root listing after", kvfs.ls("/"), ["hello.txt", "motd", "tmp"])
expect("missing module", kramdisk.load_module(3), -1)

print "fails", fails
print "kfs-done"