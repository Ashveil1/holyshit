# Linux x86-64 executable-memory ownership for future JIT code.
# No page is writable and executable at the same time. This is not a JIT.
extern:
  I64 mmap(Ptr addr, U64 length, I64 prot, I64 flags, I64 fd, I64 offset)
  I64 mprotect(Ptr addr, U64 length, I64 prot)
  I64 munmap(Ptr addr, U64 length)
def publish(code):
  # Validate before allocating; reject Bool and non-byte values.
  code = code + []
  n = len(code)
  if n < 1 or n > 16777216:
    raise "jitmem: code size must be 1..16777216"
  for b in code:
    if b & 255 != b:
      raise "jitmem: code must contain bytes"
  size = (n + 4095) & -4096
  ptr = mmap(0, size, 3, 34, -1, 0)
  if ptr == -1 or ptr == 0:
    raise "jitmem: mmap failed"
  try:
    unsafe:
      Ptr p = as_ptr(ptr)
    i = 0
    while i < n:
      b = code[i]
      unsafe:
        store8(p + i, b)
      i = i + 1
    if mprotect(ptr, size, 5) != 0:
      raise "jitmem: mprotect failed"
  except as e:
    munmap(ptr, size)
    raise e
  return {"ptr": ptr, "size": size, "length": n, "live": true}
def release(image):
  if not image["live"]:
    raise "jitmem: image already released"
  if munmap(image["ptr"], image["size"]) != 0:
    raise "jitmem: munmap failed"
  image["live"] = false
  image["ptr"] = 0
