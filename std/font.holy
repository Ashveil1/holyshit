# Original5x7 bitmap labels. ASCII only; lowercase folds to uppercase.
import std.gfx
characters = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:!?-+/=<>[]()_"
rows = [[0, 0, 0, 0, 0, 0, 0], [14, 17, 17, 31, 17, 17, 17], [30, 17, 17, 30, 17, 17, 30], [15, 16, 16, 16, 16, 16, 15], [30, 17, 17, 17, 17, 17, 30], [31, 16, 16, 30, 16, 16, 31], [31, 16, 16, 30, 16, 16, 16], [15, 16, 16, 23, 17, 17, 15], [17, 17, 17, 31, 17, 17, 17], [31, 4, 4, 4, 4, 4, 31], [7, 2, 2, 2, 18, 18, 12], [17, 18, 20, 24, 20, 18, 17], [16, 16, 16, 16, 16, 16, 31], [17, 27, 21, 21, 17, 17, 17], [17, 25, 21, 19, 17, 17, 17], [14, 17, 17, 17, 17, 17, 14], [30, 17, 17, 30, 16, 16, 16], [14, 17, 17, 17, 21, 18, 13], [30, 17, 17, 30, 20, 18, 17], [15, 16, 16, 14, 1, 1, 30], [31, 4, 4, 4, 4, 4, 4], [17, 17, 17, 17, 17, 17, 14], [17, 17, 17, 17, 17, 10, 4], [17, 17, 17, 21, 21, 27, 17], [17, 17, 10, 4, 10, 17, 17], [17, 17, 10, 4, 4, 4, 4], [31, 1, 2, 4, 8, 16, 31], [14, 17, 19, 21, 25, 17, 14], [4, 12, 4, 4, 4, 4, 14], [14, 17, 1, 2, 4, 8, 31], [30, 1, 1, 14, 1, 1, 30], [2, 6, 10, 18, 31, 2, 2], [31, 16, 16, 30, 1, 1, 30], [14, 16, 16, 30, 17, 17, 14], [31, 1, 2, 4, 8, 8, 8], [14, 17, 17, 14, 17, 17, 14], [14, 17, 17, 15, 1, 1, 14], [0, 0, 0, 0, 0, 6, 6], [0, 0, 0, 0, 6, 4, 8], [0, 6, 6, 0, 6, 6, 0], [4, 4, 4, 4, 4, 0, 4], [14, 17, 1, 2, 4, 0, 4], [0, 0, 0, 31, 0, 0, 0], [0, 4, 4, 31, 4, 4, 0], [1, 2, 2, 4, 8, 8, 16], [0, 0, 31, 0, 31, 0, 0], [2, 4, 8, 16, 8, 4, 2], [8, 4, 2, 1, 2, 4, 8], [14, 8, 8, 8, 8, 8, 14], [14, 2, 2, 2, 2, 2, 14], [2, 4, 8, 8, 8, 4, 2], [8, 4, 2, 2, 2, 4, 8], [0, 0, 0, 0, 0, 0, 31]]
def glyph(character):
  character = character + ""
  if len(character) != 1:
    raise "font glyph requires one character"
  index = find(characters, character)
  lower = find("abcdefghijklmnopqrstuvwxyz", character)
  if lower >= 0:
    index = lower + 1
  if index < 0:
    index = find(characters, "?")
  return rows[index][0:7]
def measure(text, scale):
  text = text + ""
  scale = scale | 0
  if scale < 1 or scale > 16:
    raise "font scale must be 1..16"
  if len(text) > 1024:
    raise "font text exceeds 1024 characters"
  if len(text) == 0:
    return [0, 0]
  width = 0
  widest = 0
  lines = 1
  for character in text:
    if character == "\n":
      if width > widest:
        widest = width
      width = 0
      lines = lines + 1
    else:
      width = width + 6 * scale
  if width > widest:
    widest = width
  return [widest, lines * 8 * scale]
def draw(dst, x, y, text, color, scale):
  # Validate the complete call before the first pixel is changed.
  bounds = measure(text, scale)
  x = std.gfx.coordinate(x)
  y = std.gfx.coordinate(y)
  color = std.gfx.color24(color)
  left = x
  for character in text:
    if character == "\n":
      x = left
      y = y + 8 * scale
    else:
      bits = glyph(character)
      for row in range(7):
        for col in range(5):
          if bits[row] & (1 << (4 - col)):
            px = x + col * scale
            py = y + row * scale
            if px < dst[0] and py < dst[1] and px + scale > 0 and py + scale > 0:
              std.gfx.rect(dst, px, py, scale, scale, color)
      x = x + 6 * scale
