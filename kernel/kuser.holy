import kmb
import kpage
import kpmm
import ksyscall
import kvfs
BIAS = ksyscall.USER_BIAS
PAGE = 4096
PT_LOAD = 1
PF_W = 2
STACK_TOP = BIAS + 0x20000000
STACK_PAGES = 8
CS_USER = 0x23
SS_USER = 0x1B
RFLAGS_USER = 0x2
seg_base = 0
seg_end = 0
entry_point = 0
seg_count = 0
stack_top = 0
def magic_byte(base, i):
  unsafe:
    return load8(as_ptr(base) + i)

def elf_magic_ok(base):
  # 0x7f "ELF" byte by byte: hs string escapes cover \n \t \" \\ only
  return magic_byte(base, 0) == 127 and magic_byte(base, 1) == 69 and magic_byte(base, 2) == 76 and magic_byte(base, 3) == 70
def ph_num(base):
  return kmb.rd32(base + 54) >> 16
def ph_size(base):
  return kmb.rd32(base + 54) & 0xFFFF
def phdr(base, i):
  return base + kmb.rd64(base + 32) + i * ph_size(base)
def ph_type(p):
  return kmb.rd32(p)  # p_type is 32-bit and p_flags sits right after it
def ph_flags(p):
  return kmb.rd32(p + 4)
def ph_offset(p):
  return kmb.rd64(p + 8)
def ph_vaddr(p):
  return kmb.rd64(p + 16)
def ph_filesz(p):
  return kmb.rd64(p + 32)
def ph_memsz(p):
  return kmb.rd64(p + 40)
def copy_in(dst, src, n):
  unsafe:
    Ptr s = as_ptr(src)
    Ptr d = as_ptr(dst)
    I64 i = 0
    while i < n:
      store8(d + i, load8(s + i))
      i = i + 1
  return n
def poke(addr, value):
  unsafe:
    store64(as_ptr(addr), value)
def load_segment(p, mod_base):
  vaddr = ph_vaddr(p) + BIAS
  memsz = ph_memsz(p)
  if memsz <= 0:
    return 0
  # map whole pages covering [vaddr, vaddr+memsz): a segment that starts
  # mid-page (vaddr % PAGE != 0) can spill into one more page than
  # ceil(memsz / PAGE)
  pbase = vaddr - vaddr % PAGE
  span = vaddr + memsz - pbase
  if ksyscall.map_user_pages(pbase, span, 7) * PAGE < span:
    return 0
  filesz = ph_filesz(p)
  if filesz > 0:
    copy_in(vaddr, mod_base + ph_offset(p), filesz)
  if ph_flags(p) & PF_W == 0:
    off = 0
    while off < span:
      kpage.protect(cr3(), pbase + off, 5)
      off = off + PAGE
  return 1
def load_image(mod_base, size):
  # load an ELF from raw bytes; shared by multiboot modules and by exec
  # (which reads the file from VFS). 1 once ready to enter, 0 otherwise.
  global seg_base, seg_end, entry_point, seg_count, stack_top
  seg_count = 0
  seg_base = 0
  seg_end = 0
  if mod_base == 0 or size < 128:
    return 0
  if not elf_magic_ok(mod_base):
    return 0
  n = ph_num(mod_base)
  if n <= 0 or n > 64:
    return 0
  lo = 0
  hi = 0
  i = 0
  while i < n:
    p = phdr(mod_base, i)
    if ph_type(p) == PT_LOAD:
      if not load_segment(p, mod_base):
        return 0
      if seg_count == 0 or ph_vaddr(p) < lo:
        lo = ph_vaddr(p)
      if ph_vaddr(p) + ph_memsz(p) > hi:
        hi = ph_vaddr(p) + ph_memsz(p)
      seg_count = seg_count + 1
    i = i + 1
  if seg_count == 0:
    return 0
  seg_base = lo + BIAS
  seg_end = hi + BIAS
  entry_point = kmb.rd64(mod_base + 24) + BIAS
  stack_bytes = STACK_PAGES * PAGE
  if ksyscall.map_user_pages(STACK_TOP - stack_bytes, stack_bytes, 7) != STACK_PAGES:
    return 0
  stack_top = STACK_TOP
  return 1

def load_module(idx):
  if kmb.mods_count() <= idx:
    return 0
  return load_image(kmb.mod_start(idx), kmb.mod_len(idx))

def segments():
  return seg_count
def text_base():
  return seg_base
def text_end():
  return seg_end
def entry():
  return entry_point
def user_stack_top():
  return stack_top
def build_frame(rip, rsp):
  # argv for kernel-loaded programs is empty: lay argc=0 and argv[0]=NULL
  # on the stack top (envp after it reads NULL too), and start the user
  # rsp below them. The hosted _start prologue reads argc from [rsp] the
  # way Linux lays it out — without this it would read an unmapped word
  # and fault before main runs.
  frame = rsp - 56
  poke(rsp - 8, 0)
  poke(rsp - 16, 0)
  poke(frame, rip)
  poke(frame + 8, CS_USER)
  poke(frame + 16, RFLAGS_USER)
  poke(frame + 24, rsp - 16)
  poke(frame + 32, SS_USER)
  return frame
def run():
  return enter_user(entry_point, build_frame(entry_point, stack_top))

def payload_addr(s):
  # heap address of a Str payload (header [kind][len] is 16 bytes)
  unsafe:
    Ptr p = as_ptr(s)
    return as_int(p + 16)

def sys_exec(path_ptr, path_len):
  # exec(path, len) over the current image; one-shot, no return on success.
  # Uses exec_enter (not run): run would record a continuation over the
  # dying session, and the new program's exit could never resume the shell.
  data = kvfs.read(read_mem(path_ptr, path_len))
  if data == null:
    return -2
  if load_image(payload_addr(data), len(data)) == 0:
    return -12
  exec_enter(entry_point, build_frame(entry_point, stack_top))
  return -12

def enable_exec():
  # ksyscall cannot import kuser (cycle), so it calls exec through this hook
  ksyscall.exec_fn = sys_exec
  return true
