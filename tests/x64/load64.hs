unsafe:
  # 64-bit access: page table entries, pointers, atomics
  Ptr p = alloc(16)
  store64(p, 0x0123456789ABCDEF)
  print load64(p) == 0x0123456789ABCDEF
  print load64(p)

  # little-endian byte order, verified through load8/load32
  print load8(p)
  print load8(p + 7)
  print load32(p) == 0x89ABCDEF

  # sign round-trip: store a negative word, read it back
  store64(p, -1)
  print load64(p) == -1

  # two independent 8-byte slots in one allocation
  Ptr q = p + 8
  store64(p, 111)
  store64(q, 222)
  print load64(p), load64(q)
  print load64(p + 8) == 222

  # round-trip every byte pattern
  store8(p, 255)
  print load64(p) == 255
  store32(p, 0xFFFFFFFF)
  print load64(p) == 0xFFFFFFFF
  store64(p, 0x7FFFFFFFFFFFFFFF)
  print load64(p)

  # a page-table-shaped access: index a table of 64-bit entries
  Ptr tbl = alloc(4096)
  store64(tbl, 0x83)
  store64(tbl + 512 * 8, 0x0123456789ABCDEF)
  print load64(tbl) == 0x83
  print load64(tbl + 512 * 8) == 0x0123456789ABCDEF
  print load32(tbl + 4) == 0
