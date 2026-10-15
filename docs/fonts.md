# Tiny bitmap labels

`std.font` draws an original5x7 bitmap font into `std.gfx` software surfaces.
It is intended for early boot labels and diagnostics, not general typography.

```
import std.font
screen = std.gfx.surface(320, 80, 0x16324f)
std.font.draw(screen, 12, 12, "HS SYSTEM READY", 0xe8edf2, 2)
print std.font.measure("HS SYSTEM READY", 2)
```

- `glyph(character)` returns a fresh list of seven5-bit rows, left pixel bit4.
- `measure(text, scale)` returns `[width,height]`, with6x8 cells including
  trailing spacing. Newline starts a new row; empty text measures `[0,0]`.
- `draw(surface,x,y,text,color,scale)` clips to the surface and changes only
  foreground pixels. It does not clear the background or wrap lines.

The built-in shapes are A-Z,0-9, space and `.,:!?-+/=<>[]()_`.
ASCII lowercase uses the uppercase shape. Every other character uses `?`,
including tabs. This is an ASCII-only portable interface: existing backend
UTF-8 byte/character differences still apply. There is no Thai shaping,
Unicode layout, font loading, kerning or antialiasing. Scale is an integer
1..16, and input is limited to1024 characters. Invalid call arguments fail
before pixels change; keep the surface dimensions and storage intact.

This module changes software RGB pixels only. Kernel execution tests prove
its freestanding arithmetic, not display hardware or a graphical terminal.
The framebuffer stage is separate. No desktop, window manager or input loop
is implied by a rendered label.
