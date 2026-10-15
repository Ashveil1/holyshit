# std.heap — free-list malloc/free on top of unsafe structs (K&R style).
# Addresses are Ints (must fit Int63, like as_int). Single-threaded only.
# heap_init(n) twice leaks the old region (documented, kept simple).

unsafe:
  struct Block:
    U64 size
    Block* next

free_head = 0

def heap_init_at(addr, nbytes):
  # start the heap on an explicit region (already mapped and writable).
  # The kernel maps real frames first, then calls this.
  global free_head
  unsafe:
    Block* b = as_ptr(addr)
    b.size = nbytes - 16
    b.next = null
    free_head = as_int(b)

def heap_init(nbytes):
  global free_head
  unsafe:
    Ptr base = alloc(nbytes)
    Block* b = base
    b.size = nbytes - 16
    b.next = null
    free_head = as_int(b)

def malloc(nbytes):
  global free_head
  unsafe:
    U64 n = nbytes
    U64 size = (n + 7) / 8 * 8
    Block* prev = null
    Block* cur = as_ptr(free_head)
    while cur != null:
      if cur.size >= size:
        if cur.size >= size + 32:
          Block* rest = as_ptr(as_int(cur) + 16 + size)
          rest.size = cur.size - size - 16
          rest.next = cur.next
          cur.size = size
          if prev == null:
            free_head = as_int(rest)
          else:
            prev.next = rest
        else:
          if prev == null:
            free_head = as_int(cur.next)
          else:
            prev.next = cur.next
        return as_int(cur) + 16
      prev = cur
      cur = cur.next
    return 0

def free(p):
  global free_head
  unsafe:
    if p == 0:
      return
    Block* b = as_ptr(p - 16)
    Block* prev = null
    Block* cur = as_ptr(free_head)
    while cur != null and as_int(cur) < as_int(b):
      prev = cur
      cur = cur.next
    b.next = cur
    if prev == null:
      free_head = as_int(b)
    else:
      prev.next = b
    if cur != null and as_int(b) + 16 + b.size == as_int(cur):
      b.size = b.size + 16 + cur.size
      b.next = cur.next
    if prev != null and as_int(prev) + 16 + prev.size == as_int(b):
      prev.size = prev.size + 16 + b.size
      prev.next = b.next

def heap_free():
  unsafe:
    U64 total = 0
    Block* cur = as_ptr(free_head)
    while cur != null:
      total = total + cur.size
      cur = cur.next
    return total

def heap_nblocks():
  unsafe:
    I64 n = 0
    Block* cur = as_ptr(free_head)
    while cur != null:
      n = n + 1
      cur = cur.next
    return n
