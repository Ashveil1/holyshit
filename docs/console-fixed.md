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

The [kernel integer input extension](keyboard-code.md) now switches this demo
to `readkey_code()`, eliminating the32-byte input Str and unsafe payload read.
This supersedes the readkey-per-byte limitation above only for this new demo.
Logging/static string initialization and general bump-heap limits remain; no
total interactive allocation or indefinite lifetime guarantee is inferred.

The fixed demo now draws an eight-by-two-pixel underline after the active input
text. It is steady, not blinking, and moves with accepted edits, backspace and
submission reset. The final 42-character position fits inside the cleared input
strip. It does not add navigation, selection, focus switching or command
execution. Raw fill calls keep the measured render loop's 16-byte marker gap
unchanged over 1000 submissions. The graphical boot gate checks the cursor
pixels after G and absence of a stale underline at the old position. The
640x480 guest screenshot was visually inspected with the four retained lines
and G followed by the underline.

The boot regression also checks the cursor at empty input, all 42 characters,
one ignored over-capacity character, backspace to 41 and Enter reset to zero.
Each check reads the full cleared cursor strip so stale markers are detected.
The original C/D/E/F transcript and G input are then restored and checked.

Full CI installs GRUB/xorriso and runs the fixed-console boot regression with
`HS_REQUIRE_GUI=1` before the full suite. Missing tools fail that required step
instead of silently skipping. Local runs without the flag still skip when
optional dependencies are absent. This changes CI coverage, not hardware support.

The ELF32 wrapper includes an explicit NULL section table after its loadable
segments. Modern GRUB treats a zero section count as an extended-count marker
and rejects the older sectionless wrapper. The hs and Python linkers retain
identical load addresses and complete image bytes, including this metadata.

The graphical demo and guarded RAM-frame allocation proof now call the same
`kconsole_view` text/history/cursor helpers. The view is a trusted internal
layout record created once, not a validated public widget API. Redraws read
opaque fixed-buffer state directly without snapshots. The 1000-submission
proof therefore measures the actual shared redraw path, retaining the same
16-byte allocation-marker gap and independently checked pixels/outer guards.
The real GRUB keyboard gate retains the original layout and cursor checks.
