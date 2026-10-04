# kvfs unit tests: the whole VFS without any kernel (runs everywhere)
import kvfs

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

expect("init", kvfs.vfs_init(), true)
expect("root is dir", kvfs.is_dir("/"), true)
expect("root ls empty", kvfs.ls("/"), [])
expect("missing is null", kvfs.read("/nope"), null)
expect("missing stat null", kvfs.stat("/nope"), null)

# mkdir: single level, parents must exist
expect("mkdir top", kvfs.mkdir("/etc"), true)
expect("mkdir again", kvfs.mkdir("/etc"), false)
expect("mkdir nested need parents", kvfs.mkdir("/a/b"), false)
expect("mkdir under file later", kvfs.is_dir("/etc"), true)
expect("ls root", kvfs.ls("/"), ["etc"])
expect("ls etc empty", kvfs.ls("/etc"), [])

# files: create/write/read/stat
expect("create", kvfs.create("/etc/hosts") >= 0, true)
expect("create dup", kvfs.create("/etc/hosts"), -1)
expect("create missing parent", kvfs.create("/x/y"), -1)
expect("write", kvfs.write("/etc/hosts", "127.0.0.1 localhost"), true)
expect("read", kvfs.read("/etc/hosts"), "127.0.0.1 localhost")
expect("stat file", kvfs.stat("/etc/hosts"), [0, 19])
expect("stat dir", kvfs.stat("/etc"), [1, 0])
expect("is_file", kvfs.is_file("/etc/hosts"), true)
expect("is_file dir", kvfs.is_file("/etc"), false)
expect("write replaces", kvfs.write("/etc/hosts", "short"), true)
expect("read replaced", kvfs.read("/etc/hosts"), "short")
expect("write makes file", kvfs.write("/new.txt", "new"), true)
expect("read new", kvfs.read("/new.txt"), "new")
expect("write under missing parent", kvfs.write("/zz/top.txt", "x"), false)
expect("read dir is null", kvfs.read("/etc"), null)
expect("write dir fails", kvfs.write("/etc", "x"), false)
expect("open dir for write", kvfs.fopen("/etc", "w"), -1)

# relative paths resolve from root too, . and .. work
expect("relative", kvfs.read("etc/hosts"), "short")
expect("dot", kvfs.read("/etc/./hosts"), "short")
expect("dotdot", kvfs.read("/etc/../new.txt"), "new")
expect("rootdot", kvfs.ls("/."), ["etc", "new.txt"])

# fds: open/read/write/seek/tell/close
fd = kvfs.fopen("/etc/hosts", "r")
expect("open r", fd >= 0, true)
expect("tell 0", kvfs.ftell(fd), 0)
expect("read 5", kvfs.fread(fd, 5), "short")
expect("tell 5", kvfs.ftell(fd), 5)
expect("read rest", kvfs.fread(fd, 100), "")
expect("tell end", kvfs.ftell(fd), 5)
expect("seek 1", kvfs.fseek(fd, 1), 1)
expect("read 2", kvfs.fread(fd, 2), "ho")
expect("seek past clamps", kvfs.fseek(fd, 99), 5)
expect("seek neg", kvfs.fseek(fd, -1), -1)
expect("close", kvfs.fclose(fd), true)
expect("close again", kvfs.fclose(fd), false)
expect("read closed null", kvfs.fread(fd, 1), null)
expect("tell closed", kvfs.ftell(fd), -1)
expect("open missing r", kvfs.fopen("/nope", "r"), -1)
expect("open bad mode", kvfs.fopen("/etc/hosts", "x"), -1)

fw = kvfs.fopen("/out.log", "w")
expect("open w creates", fw >= 0, true)
expect("write fd", kvfs.fwrite(fw, "ab"), 2)
expect("write more", kvfs.fwrite(fw, "cd"), 2)
expect("tell 4", kvfs.ftell(fw), 4)
expect("seek 1", kvfs.fseek(fw, 1), 1)
expect("overwrite", kvfs.fwrite(fw, "X"), 1)
expect("close w", kvfs.fclose(fw), true)
expect("file content", kvfs.read("/out.log"), "aXcd")
expect("write closed", kvfs.fwrite(fw, "z"), -1)

# unlink: files go, non-empty dirs stay, root stays, fds go stale
expect("unlink missing", kvfs.unlink("/nope"), false)
expect("unlink root", kvfs.unlink("/"), false)
expect("unlink nonempty dir", kvfs.unlink("/etc"), false)
fd2 = kvfs.fopen("/etc/hosts", "r")
expect("unlink file", kvfs.unlink("/etc/hosts"), true)
expect("gone", kvfs.read("/etc/hosts"), null)
expect("fd stale", kvfs.fread(fd2, 1), null)
expect("unlink twice", kvfs.unlink("/etc/hosts"), false)
expect("unlink empty dir now", kvfs.unlink("/etc"), true)
expect("ls root after", kvfs.ls("/"), ["new.txt", "out.log"])

print "fails", fails
