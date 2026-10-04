# real frame allocator driven by the bootloader's memory map
import kmb
import kpmm
import kpage

fails = 0

def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1

def poke(addr, value):
  unsafe:
    store64(as_ptr(addr), value)

def peek(addr):
  unsafe:
    I64 v = load64(as_ptr(addr))
    return v

# --- the memory map itself ---
expect("boot info found", kmb.usable(), true)
n = kmb.count_entries()
expect("several regions", n > 2, true)
expect("abi detected", kmb.abi() != 0, true)
expect("mem_lower known", kmb.mem_lower() > 0, true)
expect("mem_upper known", kmb.mem_upper() > 0, true)

# the biggest usable region must cover the memory the machine really has
big = 0
big_len = 0
i = 0
while i < n:
  if kmb.map_type(i) == 1:
    if kmb.map_len(i) > big_len:
      big_len = kmb.map_len(i)
      big = kmb.map_base(i)
  i = i + 1
expect("pool starts at 1 MiB", big, 0x100000)
expect("pool covers most of RAM", big_len > 0xFE00000, true)

# --- the pool ---
frames = kpmm.init()
expect("pmm ready", kpmm.ready(), true)
expect("frame count", frames, big_len / 4096)
expect("total()", kpmm.total(), frames)
expect("base()", kpmm.base(), big)
expect("usable regions counted", kpmm.regions() >= 2, true)
expect("frames available", kpmm.available() > 0, true)
expect("kernel image reserved", kpmm.available() < frames, true)

# frames come out page-aligned, distinct and counted
before = kpmm.available()
a = kpmm.alloc(1)
expect("one frame aligned", a % 4096, 0)
expect("one frame counted", kpmm.available(), before - 1)
b = kpmm.alloc(4)
expect("run aligned", b % 4096, 0)
expect("run does not overlap", b - a >= 4096, true)
expect("run counted", kpmm.available(), before - 5)
c = kpmm.alloc(16)
expect("big run counted", kpmm.available(), before - 21)
d = kpmm.alloc(1)
expect("reserved frames stay reserved", d >= image_end(), true)

# the frames are real memory: map one into a fresh vaddr and use it
root = cr3()
va = 0x50000000
expect("map the frame", kpage.map_phys(root, va, a), true)
poke(va, 0xDEADBEEFCAFEF00D)
expect("write through the mapping", peek(va), 0xDEADBEEFCAFEF00D)
expect("same data at the physical address", peek(a), 0xDEADBEEFCAFEF00D)
expect("unmap it again", kpage.unmap(root, va), true)

# free returns frames to the pool, first-in-first-out
expect("free one", kpmm.free(a), true)
expect("available after free", kpmm.available(), before - 21)
again = kpmm.alloc(1)
expect("the freed frame comes back first", again, a)
expect("free the run", kpmm.free_run(b, 4), true)
expect("free the big run", kpmm.free_run(c, 16), true)
expect("free the reused frame", kpmm.free(again), true)
expect("free the reserved-check frame", kpmm.free(d), true)
expect("pool restored", kpmm.available(), before)

# bogus requests fail cleanly instead of corrupting anything
expect("alloc(0)", kpmm.alloc(0), 0)
expect("alloc(too much)", kpmm.alloc(1 << 22), 0)
expect("free below the pool", kpmm.free(0x10), false)
expect("free inside the kernel image", kpmm.free(0x1000), false)
expect("still usable after bad requests", kpmm.alloc(1) % 4096, 0)

print "fails", fails
print "kpmm-done"