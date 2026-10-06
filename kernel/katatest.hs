import kata
import kprim
fails = 0
def expect(label, got, want):
  global fails
  if got == want:
    print "ok", label
    return
  print "FAIL", label, got, want
  fails = fails + 1
def byte_at(buf, off):
  unsafe:
    Ptr p = as_ptr(buf)
    return load8(p + off)
def put7(buf, i):
  unsafe:
    Ptr p = as_ptr(buf)
    store8(p + i, (i * 7) & 0xFF)
def fill(buf, n):
  i = 0
  while i < n:
    put7(buf, i)
    i = i + 1
def same_buf(a, b, n):
  i = 0
  while i < n:
    unsafe:
      Ptr pa = as_ptr(a)
      Ptr pb = as_ptr(b)
      if load8(pa + i) != load8(pb + i):
        return false
    i = i + 1
  return true
print "kata-start"
if not kata.present():
  print "FAIL no device"
  print "fails", fails + 1
  print "kata-done"
else:
  print "ok", "device present"
  buf = kata.identify_buf()
  kata.read_identify(buf)
  nsect = kata.sectors(buf)
  expect("sectors plausible", nsect > 16, true)
  print "nsect", nsect, "spir", kata.sectors_per_irq(buf)
  m = kata.model(buf)
  print "model", m
  expect("model nonempty", len(m) > 0, true)
  buf2 = alloc(512)
  kata.read(4, 1, buf2)
  expect("read pattern lo", byte_at(buf2, 0), 0xAB)
  expect("read pattern hi", byte_at(buf2, 1), 0xCD)
  expect("read pattern mid", byte_at(buf2, 300), 0xAB)
  expect("read pattern tail", byte_at(buf2, 511), 0xCD)
  out = alloc(512)
  fill(out, 512)
  kata.write(9, 1, out)
  back = alloc(512)
  kata.read(9, 1, back)
  expect("write/read same", same_buf(out, back, 512), true)
  kata.read(10, 1, back)
  expect("neighbour intact", byte_at(back, 0), 0x5A)
print "fails", fails
print "kata-done"
