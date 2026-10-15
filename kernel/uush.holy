# holyshit shell — runs in ring 3, talks to the kernel only through scall().
# Files come from the ramdisk the kernel mounted; `run` execs an ELF from
# VFS (one-shot: the new text usually overlaps this one, so on its exit the
# kernel resumes where this shell entered, and there is no shell anymore).
# xbuild-only: scall has no interp/native backend (like enter_user).
SYS_READ = 0
SYS_WRITE = 1
SYS_OPEN = 2
SYS_CLOSE = 3
SYS_EXEC = 59
SYS_LS = 78
SYS_MKDIR = 83
SYS_UNLINK = 87

def sc(nr, a1, a2, a3, a4, a5, a6):
  return scall(nr, a1, a2, a3, a4, a5, a6)

def saddr(s):
  # address of a Str's payload (header [kind][len] is 16 bytes)
  unsafe:
    Ptr p = as_ptr(s)
    return as_int(p + 16)

def ubuf(n):
  unsafe:
    Ptr p = alloc(n)
    return as_int(p)

def puts(s):
  # exact bytes, no extra newline (unlike print)
  return sc(SYS_WRITE, 1, saddr(s), len(s), 0, 0, 0)

def readline():
  b = ubuf(256)
  n = sc(SYS_READ, 0, b, 256, 0, 0, 0)
  if n <= 0:
    return null
  return read_mem(b, n)

def cat(path):
  fd = sc(SYS_OPEN, saddr(path), len(path), 0, 0, 0, 0)
  if fd < 0:
    print "no such file"
    return
  b = ubuf(256)
  while true:
    n = sc(SYS_READ, fd, b, 256, 0, 0, 0)
    if n <= 0:
      break
    sc(SYS_WRITE, 1, b, n, 0, 0, 0)
  sc(SYS_CLOSE, fd, 0, 0, 0, 0, 0)

def ls(path):
  b = ubuf(1024)
  n = sc(SYS_LS, saddr(path), len(path), b, 1024, 0, 0)
  if n < 0:
    print "no such dir"
    return
  if n == 0:
    print "(empty)"
    return
  sc(SYS_WRITE, 1, b, n, 0, 0, 0)

def writefile(path, text):
  fd = sc(SYS_OPEN, saddr(path), len(path), 1, 0, 0, 0)
  if fd < 0:
    print "cannot write"
    return
  sc(SYS_WRITE, fd, saddr(text), len(text), 0, 0, 0)
  sc(SYS_CLOSE, fd, 0, 0, 0, 0, 0)

def main():
  print "holyshit sh - type help"
  while true:
    puts("sh> ")
    line = readline()
    if line == null:
      return null
    if line == "":
      continue
    parts = split(line)
    if len(parts) == 0:
      continue
    cmd = parts[0]
    if cmd == "exit":
      return null
    if cmd == "help":
      print "commands: help echo cat ls mkdir rm write run exit"
      continue
    if cmd == "echo":
      print join(" ", parts[1:])
      continue
    if cmd == "cat":
      if len(parts) > 1:
        cat(parts[1])
      else:
        print "usage: cat <file>"
      continue
    if cmd == "ls":
      if len(parts) > 1:
        ls(parts[1])
      else:
        ls("/")
      continue
    if cmd == "mkdir":
      if len(parts) > 1:
        if sc(SYS_MKDIR, saddr(parts[1]), len(parts[1]), 0, 0, 0, 0) < 0:
          print "mkdir failed"
      else:
        print "usage: mkdir <dir>"
      continue
    if cmd == "rm":
      if len(parts) > 1:
        if sc(SYS_UNLINK, saddr(parts[1]), len(parts[1]), 0, 0, 0, 0) < 0:
          print "rm failed"
      else:
        print "usage: rm <file>"
      continue
    if cmd == "write":
      if len(parts) > 2:
        writefile(parts[1], join(" ", parts[2:]))
      else:
        print "usage: write <file> <text...>"
      continue
    if cmd == "run":
      if len(parts) > 1:
        if sc(SYS_EXEC, saddr(parts[1]), len(parts[1]), 0, 0, 0, 0) < 0:
          print "exec failed"
      else:
        print "usage: run <prog>"
      continue
    print "unknown command: " + cmd
  return null
main()
