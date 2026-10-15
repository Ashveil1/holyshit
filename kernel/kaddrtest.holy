# address spaces on bare metal: a new PML4 shares the kernel, maps its own
# pages, isolates them from the old space, and keeps them across switches
import kmb
import kpmm
import kpage
import kaddr

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

root = kaddr.current()
expect("root aligned", root % 4096, 0)

ns = kaddr.new()
expect("new space nonzero", ns != 0, true)
expect("new space aligned", ns % 4096, 0)
expect("new space is not the root", ns == root, false)
expect("kernel visible through the new root", kpage.translate(ns, 0x100000), 0x100000)

# the switch itself: serial still works, which proves code/stack/data survive
expect("switch to the new space", kaddr.switch(ns), true)
expect("current is the new space", kaddr.current(), ns)
print "ok alive after switch"
expect("kernel still mapped", kpage.translate(ns, 0x100000), 0x100000)

# map a frame only in the new space and use it there
frame = kpmm.alloc(1)
expect("frame aligned", frame % 4096, 0)
va = kaddr.USER_MIN
expect("hole unmapped in the new space", kpage.is_mapped(ns, va), false)
expect("map in the new space", kpage.map_phys(ns, va, frame), true)
poke(va, 0x123456789ABCDEF0)
expect("write in the new space", peek(va), 0x123456789ABCDEF0)
expect("same data at the frame", peek(frame), 0x123456789ABCDEF0)

# back in the old space the page does not exist: real isolation
expect("switch back", kaddr.switch(root), true)
expect("unmapped in the old space", kpage.is_mapped(root, va), false)
expect("translate is 0 in the old space", kpage.translate(root, va), 0)

# and the mapping survives the round trip
expect("switch again", kaddr.switch(ns), true)
expect("data survived the switches", peek(va), 0x123456789ABCDEF0)
expect("still mapped", kpage.translate(ns, va), frame)

# unmap in the new space, come home, kernel intact
expect("unmap", kpage.unmap(ns, va), true)
expect("gone", kpage.translate(ns, va), 0)
expect("switch home", kaddr.switch(root), true)
expect("identity intact", kpage.translate(root, 0x100000), 0x100000)
expect("free the frame", kpmm.free(frame), true)

print "fails", fails
print "kaddr-done"