# kernel vfs — a tiny hierarchical filesystem in plain .hs.
#
# Inodes live in parallel lists; file bytes live in .hs Str values.
# kinds: 0 = file, 1 = dir, 2 = dead (unlinked but maybe still open).
# Root is inode 0 ("/", parent of itself). No cwd: every path is resolved
# from the root (a leading "/" is optional). Sizes are len(data); dirs hold "".
#
# Helpers come before their users: the x64 backend resolves module-level
# names statically.

K_FILE = 0
K_DIR = 1
K_DEAD = 2

v_names = []
v_parent = []
v_kind = []
v_data = []

f_ino = []
f_off = []

def vfs_init():
  global v_names, v_parent, v_kind, v_data, f_ino, f_off
  v_names = []
  v_parent = []
  v_kind = []
  v_data = []
  f_ino = []
  f_off = []
  append(v_names, "/")
  append(v_parent, 0)
  append(v_kind, K_DIR)
  append(v_data, "")
  return true

def ninodes():
  return len(v_names)

def split_segs(path):
  parts = split(path, "/")
  out = []
  for p in parts:
    if p != "":
      append(out, p)
  return out

def find_child(dir, name):
  i = 0
  n = len(v_names)
  while i < n:
    if v_kind[i] != K_DEAD and v_parent[i] == dir and v_names[i] == name:
      return i
    i = i + 1
  return -1

def resolve(path):
  ino = 0
  for s in split_segs(path):
    if s == ".":
      continue
    if s == "..":
      ino = v_parent[ino]
      continue
    ino = find_child(ino, s)
    if ino < 0:
      return -1
  return ino

def split_parent(path):
  # [parent path, leaf name] for anything but root
  segs = split_segs(path)
  if len(segs) == 0:
    return ["/", ""]
  name = segs[len(segs) - 1]
  if len(segs) == 1:
    return ["/", name]
  return ["/" + join("/", segs[:len(segs) - 1]), name]

def add_inode(name, parent, kind):
  append(v_names, name)
  append(v_parent, parent)
  append(v_kind, kind)
  append(v_data, "")
  return len(v_names) - 1

def mkdir(path):
  # single level: the parent must already exist
  parts = split_parent(path)
  parent = resolve(parts[0])
  name = parts[1]
  if name == "" or name == "." or name == "..":
    return false
  if parent < 0 or v_kind[parent] != K_DIR:
    return false
  if find_child(parent, name) >= 0:
    return false
  add_inode(name, parent, K_DIR)
  return true

def mkdirs(path):
  # every level, like mkdir -p; fails if a file blocks the way
  cur = ""
  for s in split_segs(path):
    cur = cur + "/" + s
    if resolve(cur) < 0:
      if not mkdir(cur):
        return false
  return true

def create(path):
  parts = split_parent(path)
  parent = resolve(parts[0])
  name = parts[1]
  if name == "" or name == "." or name == "..":
    return -1
  if parent < 0 or v_kind[parent] != K_DIR:
    return -1
  if find_child(parent, name) >= 0:
    return -1
  return add_inode(name, parent, K_FILE)

def write(path, data):
  # whole-file replace, creating the file (not parents) as needed
  ino = resolve(path)
  if ino < 0:
    ino = create(path)
    if ino < 0:
      return false
  if v_kind[ino] != K_FILE:
    return false
  v_data[ino] = data
  return true

def read(path):
  ino = resolve(path)
  if ino < 0 or v_kind[ino] != K_FILE:
    return null
  return v_data[ino]

def ls(path):
  ino = resolve(path)
  if ino < 0 or v_kind[ino] != K_DIR:
    return null
  out = []
  i = 0
  n = len(v_names)
  while i < n:
    if i != ino and v_kind[i] != K_DEAD and v_parent[i] == ino:
      append(out, v_names[i])
    i = i + 1
  return out

def stat(path):
  ino = resolve(path)
  if ino < 0 or v_kind[ino] == K_DEAD:
    return null
  return [v_kind[ino], len(v_data[ino])]

def is_file(path):
  st = stat(path)
  if st == null:
    return false
  return st[0] == K_FILE

def is_dir(path):
  st = stat(path)
  if st == null:
    return false
  return st[0] == K_DIR

def unlink(path):
  ino = resolve(path)
  if ino <= 0:
    return false
  if v_kind[ino] == K_DEAD:
    return false
  if v_kind[ino] == K_DIR:
    # non-empty dir: any live child blocks the removal
    i = 0
    n = len(v_names)
    while i < n:
      if i != ino and v_kind[i] != K_DEAD and v_parent[i] == ino:
        return false
      i = i + 1
  v_kind[ino] = K_DEAD
  i = 0
  while i < len(f_ino):
    if f_ino[i] == ino:
      f_ino[i] = -1
    i = i + 1
  return true

def fd_valid(fd):
  if fd < 0 or fd >= len(f_ino):
    return false
  if f_ino[fd] < 0:
    return false
  return v_kind[f_ino[fd]] == K_FILE

def fd_alloc(ino):
  i = 0
  while i < len(f_ino):
    if f_ino[i] < 0:
      f_ino[i] = ino
      f_off[i] = 0
      return i
    i = i + 1
  append(f_ino, ino)
  append(f_off, 0)
  return len(f_ino) - 1

def fopen(path, mode):
  if mode == "r":
    ino = resolve(path)
    if ino < 0 or v_kind[ino] != K_FILE:
      return -1
    return fd_alloc(ino)
  if mode == "w":
    ino = resolve(path)
    if ino < 0:
      ino = create(path)
      if ino < 0:
        return -1
    if v_kind[ino] != K_FILE:
      return -1
    v_data[ino] = ""
    return fd_alloc(ino)
  return -1

def fclose(fd):
  if fd < 0 or fd >= len(f_ino) or f_ino[fd] < 0:
    return false
  f_ino[fd] = -1
  return true

def ftell(fd):
  if not fd_valid(fd):
    return -1
  return f_off[fd]

def fseek(fd, off):
  if not fd_valid(fd):
    return -1
  if off < 0:
    return -1
  size = len(v_data[f_ino[fd]])
  if off > size:
    off = size
  f_off[fd] = off
  return off

def fread(fd, n):
  if not fd_valid(fd):
    return null
  if n <= 0:
    return ""
  s = v_data[f_ino[fd]]
  off = f_off[fd]
  if off >= len(s):
    return ""
  chunk = s[off:off + n]
  f_off[fd] = off + len(chunk)
  return chunk

def fwrite(fd, data):
  if not fd_valid(fd):
    return -1
  ino = f_ino[fd]
  s = v_data[ino]
  off = f_off[fd]
  if off > len(s):
    off = len(s)
  v_data[ino] = s[:off] + data + s[off + len(data):]
  f_off[fd] = off + len(data)
  return len(data)