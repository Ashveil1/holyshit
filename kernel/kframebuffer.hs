# Multiboot2 direct-RGB framebuffer, restricted to byte-aligned RGB24/32.
# GRUB must provide a graphics mode. No GPU acceleration or general driver.
import kpage
import std.fbinfo
def rd8(address):
  unsafe:
    return load8(as_ptr(address))
def rd32(address):
  unsafe:
    return load32(as_ptr(address))
def descriptor():
  if mb_magic() != 0x36d76289:
    raise "framebuffer requires Multiboot2"
  base = mb_info()
  if base < 8 or base >= 1073676288:
    raise "invalid Multiboot2 address"
  size = rd32(base)
  if size < 16 or size > 65536 or base + size > 1073741824:
    raise "invalid Multiboot2 size"
  offset = 8
  while offset + 8 <= size:
    tag = base + offset
    kind = rd32(tag)
    length = rd32(tag + 4)
    if length < 8 or offset + length > size:
      raise "invalid Multiboot2 tag"
    if kind == 0:
      break
    if kind == 8:
      if length < 38 or rd8(tag + 29) != 1:
        raise "framebuffer is not direct RGB"
      data = []
      for i in range(38):
        append(data, rd8(tag + i))
      # Only the fixed RGB tag prefix is needed; ignore permitted extensions.
      data[4] = 38
      data[5] = 0
      data[6] = 0
      data[7] = 0
      return std.fbinfo.decode(data)
    offset = (offset + length + 7) & -8
  raise "no framebuffer tag"
def map(frame):
  root = cr3()
  start = frame[0] & -4096
  stop = (frame[0] + frame[1] * frame[3] + 4095) & -4096
  page = start
  while page < stop:
    # Supervisor writable, cache-disable and write-through device mapping.
    if not kpage.map(root, page, page, 27):
      raise "framebuffer mapping failed"
    page = page + 4096
def pixel(frame, x, y, color):
  if x < 0 or y < 0 or x >= frame[2] or y >= frame[3]:
    return
  address = frame[0] + y * frame[1] + x * frame[4]
  red = color >> 16 & 255
  green = color >> 8 & 255
  blue = color & 255
  red_address = address + frame[5]
  green_address = address + frame[6]
  blue_address = address + frame[7]
  unsafe:
    store8(as_ptr(red_address), red)
    store8(as_ptr(green_address), green)
    store8(as_ptr(blue_address), blue)
def rect(frame, x, y, width, height, color):
  left = 0 if x < 0 else x
  top = 0 if y < 0 else y
  right = frame[2] if x + width > frame[2] else x + width
  bottom = frame[3] if y + height > frame[3] else y + height
  for row in range(top, bottom):
    for col in range(left, right):
      pixel(frame, col, row, color)
