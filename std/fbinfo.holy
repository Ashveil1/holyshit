# Multiboot2 framebuffer tag decoder. Input is one complete tag byte list.
def read32(data, offset):
  return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16) | (data[offset + 3] << 24)
def decode(data):
  if len(data) < 38:
    raise "framebuffer tag truncated"
  for byte in data:
    if byte | 0 != byte or byte < 0 or byte > 255:
      raise "framebuffer tag must contain bytes"
  if read32(data, 0) != 8 or read32(data, 4) != len(data) or data[29] != 1:
    raise "framebuffer tag is not direct RGB"
  address = read32(data, 8)
  if read32(data, 12) != 0:
    raise "framebuffer address unsupported"
  pitch = read32(data, 16)
  width = read32(data, 20)
  height = read32(data, 24)
  bpp = data[28]
  if width < 1 or height < 1 or width > 4096 or height > 4096:
    raise "framebuffer dimensions unsupported"
  if bpp != 24 and bpp != 32:
    raise "framebuffer depth unsupported"
  bytes_per_pixel = bpp >> 3
  if pitch < width * bytes_per_pixel or pitch > 65536 or pitch * height > 67108864:
    raise "framebuffer pitch unsupported"
  if address < 1073741824 or address + pitch * height > 4294967296:
    raise "framebuffer address unsupported"
  red = data[32]
  green = data[34]
  blue = data[36]
  if data[33] != 8 or data[35] != 8 or data[37] != 8:
    raise "framebuffer RGB masks unsupported"
  if red % 8 != 0 or green % 8 != 0 or blue % 8 != 0 or red >= bpp or green >= bpp or blue >= bpp:
    raise "framebuffer RGB positions unsupported"
  if red == green or red == blue or green == blue:
    raise "framebuffer RGB masks overlap"
  return [address, pitch, width, height, bytes_per_pixel, red >> 3, green >> 3, blue >> 3]
