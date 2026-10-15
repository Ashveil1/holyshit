# Experimental boot screen and keyboard entry. No command/agent execution.
import kframebuffer
import std.font
import std.lineedit
def present(frame, surface, x, y):
  for row in range(surface[1]):
    for col in range(surface[0]):
      kframebuffer.pixel(frame, x + col, y + row, surface[2][row * surface[0] + col])
frame = kframebuffer.descriptor()
kframebuffer.map(frame)
kframebuffer.rect(frame, 0, 0, frame[2], frame[3], 0x16324f)
header = std.gfx.surface(576, 64, 0x386fa4)
std.font.draw(header, 16, 16, "HS SYSTEM CONSOLE", 0xffffff, 3)
present(frame, header, 24, 24)
entry = std.gfx.surface(576, 96, 0xe8edf2)
line = std.lineedit.create(42)
def redraw():
  std.gfx.rect(entry, 0, 0, 576, 96, 0xe8edf2)
  std.font.draw(entry, 8, 8, "INPUT:", 0x386fa4, 2)
  std.font.draw(entry, 8, 40, line[0], 0x16324f, 2)
  if line[1]:
    std.font.draw(entry, 8, 72, "SUBMITTED - NO COMMAND EXECUTION", 0x386fa4, 1)
  present(frame, entry, 24, 104)
redraw()
print "CONSOLE READY"
while not line[1]:
  key = readkey()
  if key != null:
    std.lineedit.feed(line, key)
    redraw()
    print "CONSOLE EDIT", len(line[0])
print "CONSOLE SUBMITTED", line[0]
while true:
  pass
