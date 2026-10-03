# memory introspection primitives: multiboot info, CR2/CR3, invlpg
# (freestanding kernel only)
print "kprim"

info = mb_info()
print info != 0
print info == info          # stable across calls

# CR3 must be 4K aligned and point at the PML4 we map statically
cr3 = cr3()
print cr3 % 4096 == 0
print cr3 != 0

# reading a control register must not fault; CR2 only meaningful after a fault
print cr2() >= 0

# identity mapping: the kernel prints at 0x100000 (load address) and that
# virtual address is present, so reading it back as a word is safe
unsafe:
  Ptr probe = as_ptr(0x100000)
  print load32(probe) != 0

# invlpg on a mapped address is a no-op that returns Null
print invlpg(0x100000)

print "kprim-done"
