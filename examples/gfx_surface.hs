# Software drawing preview. Print dimensions and a deterministic RGB checksum.
import std.gfx
screen = std.gfx.surface(160, 100, 0x16324f)
std.gfx.rect(screen, 12, 12, 136, 76, 0x0b1726)
std.gfx.rect(screen, 10, 10, 136, 76, 0xe8edf2)
std.gfx.rect(screen, 10, 10, 136, 14, 0x386fa4)
std.gfx.rect(screen, 18, 33, 42, 43, 0x43aa8b)
std.gfx.rect(screen, 69, 34, 65, 5, 0x8093a7)
std.gfx.rect(screen, 69, 45, 51, 5, 0xb1becb)
std.gfx.rect(screen, 69, 56, 60, 5, 0xb1becb)
std.gfx.rect(screen, 69, 67, 32, 10, 0x386fa4)
print screen[0], screen[1], sum(screen[2])
