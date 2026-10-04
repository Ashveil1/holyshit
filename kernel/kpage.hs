# kernel paging — 4-level page tables in plain .hs.
#
#   CR3 -> PML4 -> PDPT -> PD -> PT -> physical frame
#
# Entry bits used here:
#   0x001 present, 0x002 writable, 0x004 user,
#   0x080 PS (huge: 2MB in the PD, 1GB in the PDPT -- must stay 0 in a 4K PTE),
#   0x010 accessed
# A 512-entry table is one 4K frame. Missing tables are allocated from the
# kernel heap and zeroed; a huge page that has to hold a 4K mapping is split
# into its 512 children first (the boot identity map is made of 2MB pages).
#
# The root table is always passed in (read it with cr3()) because kernel
# builtins cannot be called from inside `unsafe:` blocks. Helpers come before
# their users: the x64 backend resolves module-level names statically.

PAGE_PRESENT = 1
PAGE_WRITE = 2
PAGE_USER = 4
PAGE_HUGE = 0x80

KERNEL_FLAGS = 0x03     # present | writable
USER_FLAGS = 0x07       # present | writable | user
HUGE_FLAGS = 0x83       # present | writable | PS (2MB page in the PD)
TABLE_FLAGS = 0x03      # present | writable (intermediate level)

PAGE_MASK = ~0xFFF
MB_MASK = ~0x1FFFFF      # 2 MiB
GB_MASK = ~0x3FFFFF      # 1 GiB

def entry_get(table, idx):
  # unsafe: no function calls allowed here, so `idx * 8` is inlined
  unsafe:
    return load64(as_ptr(table + idx * 8))

def entry_set(table, idx, value):
  unsafe:
    store64(as_ptr(table + idx * 8), value)

def new_table():
  # one zeroed, page-aligned 4K frame usable as a page table.
  # alloc() only guarantees 16-byte alignment, so ask for two pages and round
  # up; the kernel heap is identity-mapped, so the result is directly usable
  # as a physical address.
  unsafe:
    Ptr t = alloc(8192)
    I64 a = as_int(t)
    I64 page = (a + 4095) & PAGE_MASK
    I64 i = 0
    while i < 4096:
      store64(as_ptr(page + i), 0)
      i = i + 8
    return page

def split_huge(table, idx, entry, level, user):
  # Replace a huge (2MB/1GB) entry with a next-level table that covers the
  # same range with 512 children, and return that table.
  #   level 2 (PD):  2MB -> 512 x 4K pages
  #   level 3 (PDPT): 1GB -> 512 x 2MB pages
  # `user` marks the new table user-accessible: without the U/S bit on every
  # intermediate level, ring 3 faults even when the leaf itself allows it.
  flags = entry & 0xFF
  if level == 2:
    base = entry & MB_MASK
    child_step = 0x200000 / 512
    child_flags = flags & ~PAGE_HUGE
  else:
    base = entry & GB_MASK
    child_step = 0x40000000 / 512
    child_flags = flags
  fresh = new_table()
  i = 0
  while i < 512:
    entry_set(fresh, i, (base + i * child_step) | child_flags)
    i = i + 1
  tflags = TABLE_FLAGS
  if user:
    tflags = TABLE_FLAGS | PAGE_USER
  entry_set(table, idx, fresh | tflags)
  tlb_flush()
  return fresh

def level_index(vaddr, level):
  # level 4 = PML4, 3 = PDPT, 2 = PD, 1 = PT
  shift = 12 + 9 * (level - 1)
  return vaddr >> shift & 511

def pte_addr_read(root, vaddr):
  # address of the entry that governs vaddr (huge entries included),
  # never allocating; 0 when a level is absent
  table = root
  l = 4
  while l >= 1:
    idx = level_index(vaddr, l)
    addr = table + idx * 8
    entry = entry_get(table, idx)
    if entry & PAGE_PRESENT == 0:
      return 0
    if entry & PAGE_HUGE != 0:
      return addr
    if l == 1:
      return addr
    table = entry & PAGE_MASK
    l = l - 1
  return 0

def pte_addr(root, vaddr, flags):
  # address of the leaf PTE, allocating tables and splitting huge pages.
  # The leaf level returns its slot directly (an absent PTE is fine: the
  # caller fills it in); only intermediate levels allocate or split.
  # A user mapping needs the U/S bit on the whole path, so fresh tables
  # inherit it and existing supervisor tables are upgraded on first use.
  user = flags & PAGE_USER
  tflags = TABLE_FLAGS
  if user != 0:
    tflags = TABLE_FLAGS | PAGE_USER
  table = root
  l = 4
  while l >= 1:
    idx = level_index(vaddr, l)
    if l == 1:
      return table + idx * 8
    entry = entry_get(table, idx)
    if entry & PAGE_PRESENT == 0:
      fresh = new_table()
      entry_set(table, idx, fresh | tflags)
      table = fresh
    elif entry & PAGE_HUGE != 0:
      table = split_huge(table, idx, entry, l, user)
    else:
      if user != 0 and entry & PAGE_USER == 0:
        entry_set(table, idx, entry | PAGE_USER)
      table = entry & PAGE_MASK
    l = l - 1
  return 0

def pte_get(root, vaddr):
  p = pte_addr_read(root, vaddr)
  if p == 0:
    return 0
  unsafe:
    return load64(as_ptr(p))

def pte_set(root, vaddr, value):
  p = pte_addr(root, vaddr, value)
  if p == 0:
    return false
  unsafe:
    store64(as_ptr(p), value)
  return true

def translate(root, vaddr):
  # physical address behind a mapped vaddr, or 0
  table = root
  l = 4
  while l >= 1:
    idx = level_index(vaddr, l)
    entry = entry_get(table, idx)
    if entry & PAGE_PRESENT == 0:
      return 0
    if entry & PAGE_HUGE != 0:
      if l == 3:
        return entry & GB_MASK + vaddr & 0x3FFFFF
      return entry & MB_MASK + vaddr & 0x1FFFFF
    if l == 1:
      return entry & PAGE_MASK
    table = entry & PAGE_MASK
    l = l - 1
  return 0

def map(root, vaddr, paddr, flags):
  # map one 4K page, allocating tables, splitting huge pages, then dropping
  # the stale TLB entry
  ok = pte_set(root, vaddr, paddr & PAGE_MASK | flags)
  if ok:
    invlpg(vaddr)
  return ok

def unmap(root, vaddr):
  # clear a 4K mapping; refuses to touch a huge page (it has no single PTE).
  # All returns stay at safe level so callers get real Bools: a `return`
  # inside `unsafe:` would box the word as an Int instead.
  p = pte_addr_read(root, vaddr)
  if p == 0:
    return false
  if pte_get(root, vaddr) & PAGE_HUGE != 0:
    return false
  unsafe:
    store64(as_ptr(p), 0)
  invlpg(vaddr)
  return true

def protect(root, vaddr, flags):
  # change the permission bits of an existing 4K mapping, keeping the frame.
  # Used to hand ring 3 read-only text after the loader has copied it in.
  entry = pte_get(root, vaddr)
  if entry & PAGE_PRESENT == 0:
    return false
  if entry & PAGE_HUGE != 0:
    return false
  p = pte_addr_read(root, vaddr)
  unsafe:
    store64(as_ptr(p), entry & PAGE_MASK | (flags & 0xFF))
  invlpg(vaddr)
  return true

def is_mapped(root, vaddr):
  return translate(root, vaddr) != 0

def map_phys(root, vaddr, paddr):
  return map(root, vaddr, paddr, KERNEL_FLAGS)

def map_user(root, vaddr, paddr):
  return map(root, vaddr, paddr, USER_FLAGS)

def map_range(root, vaddr, paddr, nbytes):
  # map nbytes (rounded up to whole pages); returns pages mapped
  n = 0
  off = 0
  while off < nbytes:
    if not map(root, vaddr + off, paddr + off, KERNEL_FLAGS):
      return n
    n = n + 1
    off = off + 4096
  return n