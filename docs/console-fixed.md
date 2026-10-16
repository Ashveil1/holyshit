# Fixed edit/history + byte-rendered console experiment

`kernel/kconsole_fixed.holy` is a separate experimental framebuffer demo. The
older string-based demos remain unchanged. It connects `kconsole_buffer`
fixed byte storage to `kfont.draw_bytes`, keeps four submitted42-byte ASCII
lines and a current line, redraws text rows and continues after Enter. Input
is display-only: never command execution, filesystem action or agent request.
It has no model, networking, cursor/navigation, Unicode or terminal emulation.

The keyboard is still the existing single-CPU63-byte FIFO/drop-newest path.
`readkey` returns a newly allocated32-byte one-character Str for each consumed
byte. The demo reads its first payload byte through a trusted internal helper;
it is not an API accepting arbitrary strings/pointers. No raw span outlives
its owner. Fixed literal/scalar serial diagnostics replace JSON/string history
snapshots. The static header/labels initialize through the existing string API.

After initialization, storage mutation/history addressing and raw font drawing
avoid per-key strings/Lists/slices/ranges on their own valid paths. This does
not make the entire interactive session allocation-free: readkey alone grows
the bump heap, and no general collection/reclamation was added. The finite
proof below excludes readkey/logging/initialization/snapshots. The existing
16MiB heap can still exhaust in a sufficiently long interactive session. No
indefinite usability, GC, byte-perfect total heap budget or speed claim.

`tests/test_console_render.py` runs1000 edit/submission/redraw cycles in an
actual QEMU kernel, including backspace and full history eviction. The same
fixed buffer/font calls used by the demo run against a guarded RGB32 RAM frame.
Allocation markers around the loop differ by16bytes, solely the marker's
aligned allocation; snapshots/printing follow the measured loop. Independent
A/C glyph/background bytes verify all four retained rows, empty active row
and untouched outer guards. Complete native/Python kernel image equality is
required; full CI builds the native driver from the audited seed.

`tests/test_console_fixed.py` boots the actual graphical demo through GRUB,
enters six submissions and a seventh editable line, checks C/D/E/F/G pixels
and a complete matching native/Python kernel image. GRUB/xorriso are optional
local dependencies and that gate skips without them. The raw-frame integration
gate only requires QEMU. `--python-bootstrap` builds the kernel driver with
Python for local diagnostics, not a seed claim. The displayed screenshot was
visually checked at640x480 with the original console layout, four retained
lines and current G. Neither gate is a real-hardware/UEFI proof.
