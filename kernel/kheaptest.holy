# kmalloc on bare metal: std.heap over real frames mapped at HEAP_VADDR
import kmb
import kpmm
import kpage
import kheap

fails = 0

def poke(addr, value):
  unsafe:
    store64(as_ptr(addr), value)

def peek(addr):
  unsafe:
    I64 v = load64(as_ptr(addr))
    return v

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

expect("boot info found", kmb.usable(), true)
expect("pmm ready", kpmm.init() > 0, true)
expect("heap init", kheap.init(16), true)
expect("heap ready", kheap.ready(), true)
expect("heap pages", kheap.pages(), 16)
expect("heap virt", kheap.virt(), 0x60000000)
expect("heap phys nonzero", kheap.phys() != 0, true)
expect("heap mapped", kpage.translate(cr3(), 0x60000000), kheap.phys())

# small blocks come out distinct, aligned and usable
a = kheap.malloc(8)
expect("a nonzero", a != 0, true)
expect("a aligned", a % 8, 0)
b = kheap.malloc(100)
expect("b nonzero", b != 0, true)
expect("b distinct", b - a >= 16, true)
c = kheap.malloc(4096)
expect("c nonzero", c != 0, true)
expect("c after b with no overlap", c - b >= 120, true)

poke(a, 0xAAAAAAAAAAAAAAAA)
poke(b, 0xBBBBBBBBBBBBBBBB)
poke(c, 0xCCCCCCCCCCCCCCCC)
expect("a kept its pattern", peek(a), 0xAAAAAAAAAAAAAAAA)
expect("b kept its pattern", peek(b), 0xBBBBBBBBBBBBBBBB)
expect("c kept its pattern", peek(c), 0xCCCCCCCCCCCCCCCC)

# free middle-out and reuse: the free list hands the block back
before = kheap.free_bytes()
expect("free b", kheap.free(b), true)
expect("bytes back", kheap.free_bytes() > before, true)
d = kheap.malloc(100)
expect("reused block", d, b)
poke(d, 0xDDDDDDDDDDDDDDDD)
expect("d pattern", peek(d), 0xDDDDDDDDDDDDDDDD)
expect("a undisturbed", peek(a), 0xAAAAAAAAAAAAAAAA)
expect("c undisturbed", peek(c), 0xCCCCCCCCCCCCCCCC)

# free everything: one block again (headers merge back)
expect("free a", kheap.free(a), true)
expect("free c", kheap.free(c), true)
expect("free d", kheap.free(d), true)
expect("one block again", kheap.nblocks(), 1)

# exhaustion fails cleanly instead of corrupting the heap
expect("too big", kheap.malloc(1024 * 1024), 0)
expect("heap intact after failure", kheap.nblocks(), 1)
e = kheap.malloc(16)
expect("usable after failure", e != 0, true)
expect("free e", kheap.free(e), true)

print "fails", fails
print "kheap-done"