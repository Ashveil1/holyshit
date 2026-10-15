# Software RGB24 drawing. Surface layout: [width, height, row-major pixels].
# Keep dimensions/pixel storage intact. No hardware access or host dependency.
def coordinate(n):
  n = n | 0
  if n < -1048576 or n > 1048576:
    raise "gfx coordinate outside -1048576..1048576"
  return n
def color24(color):
  color = color | 0
  if color < 0 or color > 16777215:
    raise "gfx color outside RGB24"
  return color
def surface(width, height, color):
  width = coordinate(width)
  height = coordinate(height)
  color = color24(color)
  if width < 1 or height < 1 or width > 4096 or height > 4096:
    raise "gfx dimensions must be 1..4096"
  if width * height > 1048576:
    raise "gfx surface exceeds 1048576 pixels"
  pixels = []
  for i in range(width * height):
    append(pixels, color)
  return [width, height, pixels]
def pixel(dst, x, y, color):
  x = coordinate(x)
  y = coordinate(y)
  color = color24(color)
  if x >= 0 and y >= 0 and x < dst[0] and y < dst[1]:
    dst[2][y * dst[0] + x] = color
def sample(src, x, y):
  x = coordinate(x)
  y = coordinate(y)
  if x < 0 or y < 0 or x >= src[0] or y >= src[1]:
    raise "gfx sample outside surface"
  return src[2][y * src[0] + x]
def rect(dst, x, y, width, height, color):
  x = coordinate(x)
  y = coordinate(y)
  width = coordinate(width)
  height = coordinate(height)
  color = color24(color)
  if width <= 0 or height <= 0:
    return
  left = 0 if x < 0 else x
  top = 0 if y < 0 else y
  right = dst[0] if x + width > dst[0] else x + width
  bottom = dst[1] if y + height > dst[1] else y + height
  for row in range(top, bottom):
    for col in range(left, right):
      dst[2][row * dst[0] + col] = color
def blit(dst, src, x, y):
  x = coordinate(x)
  y = coordinate(y)
  left = 0 if x < 0 else x
  top = 0 if y < 0 else y
  right = dst[0] if x + src[0] > dst[0] else x + src[0]
  bottom = dst[1] if y + src[1] > dst[1] else y + src[1]
  # Snapshot even for distinct surfaces: aliases can share a pixel list.
  pixels = src[2][0:len(src[2])]
  for row in range(top, bottom):
    for col in range(left, right):
      dst[2][row * dst[0] + col] = pixels[(row - y) * src[0] + col - x]
