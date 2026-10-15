# kernel heap — std.heap (K&R malloc/free) on top of real frames.
#
# init() takes contiguous frames from the PMM, maps them at HEAP_VADDR and
# starts the free list there. Everything after that is plain std.heap:
# malloc/free/heap_free/heap_nblocks. Helpers come before their users.
import kpmm
import kpage
import std.heap

HEAP_VADDR = 0x60000000

heap_base = 0
heap_pages = 0

def init(npages):
  # returns true when npages of heap are ready
  global heap_base, heap_pages
  base = kpmm.alloc(npages)
  if base == 0:
    return false
  if kpage.map_range(cr3(), HEAP_VADDR, base, npages * 4096) != npages:
    return false
  std.heap.heap_init_at(HEAP_VADDR, npages * 4096)
  heap_base = base
  heap_pages = npages
  return true

def ready():
  return heap_pages > 0

def pages():
  return heap_pages

def phys():
  return heap_base

def virt():
  return HEAP_VADDR

def malloc(nbytes):
  return std.heap.malloc(nbytes)

def free(p):
  std.heap.free(p)
  return true

def free_bytes():
  return std.heap.heap_free()

def nblocks():
  return std.heap.heap_nblocks()