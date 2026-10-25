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

At the input's 42-character limit, the underline changes from dark blue to
red (`#b42318`). Ignored over-capacity keys keep that state; backspace restores
the normal underline, and Enter clears the old marker. This gives visible
capacity feedback without changing FIFO/drop behavior or input semantics.
The real graphical gate checks exact full/backspace/reset pixels, and the
shared RAM-frame proof exercises full/redraw/backspace/reset on every one of
1000 cycles with unchanged 16-byte marker gap. The full-input guest screenshot
was visually inspected. The underline is still steady, not a blinking cursor.

The required graphical gate also fills the retained history with empty
submissions after visible text, checks every text-row pixel for stale glyphs,
and verifies an empty backspace leaves the cursor at zero. The blank guest
screen was visually inspected; the original C/D/E/F/G layout is then restored
and checked again. This adds regression coverage without changing behavior.

A test-only instrumented copy of the real demo now measures the first 16
actual PS/2 events (ten edits and six submissions) across dequeue, fixed
storage, shared redraw and serial diagnostics. The required graphical gate
pins a 576-byte bump-pointer gap, including the ready diagnostic and marker
alignment. Native and reference compilers must produce the same complete
instrumented kernel. The final guest pixels were visually inspected.

This is deliberately not the renderer-only 16-byte proof: freestanding string
constants in diagnostics allocate through `x_str_at`. The whole interactive
session is not allocation-free. The measured finite budget is not a bound on
all event sequences, an indefinite-lifetime guarantee or a new heap/GC policy.

The demo now creates the edit/submission diagnostic label strings once before
its loop and reuses them, rather than reconstructing the same string for every
event. With identical input/serial output and pixels, the measured first16-event
gap drops from576 to64bytes: READY's48bytes plus16bytes of marker alignment.
The two retained labels initialize before the measurement. The gate still
includes actual serial printing and does not establish all-session zero
allocation, source-independent heap lifetime or GC.

After the first16-event checkpoint, the graphical gate measures256 further
paced real PS/2 events, including edits, backspace, empty submissions and
history wrap. The retained-label path's bump-pointer gap is16bytes, solely
the marker alignment in this finite sequence. Serial printing and actual
shared redraw remain inside the measured interval. The original transcript
and capacity/empty-history checks run afterward; final pixels were visually
inspected. This is not a proof for unbounded sessions, FIFO bursts, arbitrary
input sequences, counter overflow or real hardware.

`kconsole_buffer.recall(state,index)` copies one retained line into the active
edit, with the same oldest-first index convention as history accessors. It
validates the index before changing the edit; history order, lengths and
submission count stay unchanged. The copy uses existing raw storage and does
not create a string/list. Empty lines replace the edit with empty input.
This is a storage primitive, not keyboard navigation: the display-only demo
has no new shortcut and PS/2 translation is unchanged.

The independent hosted model checks wrapped-history recall, empty lines and
invalid indexes without mutation on interpreter/GCC/x64/native-seed routes.
The native/reference-identical kernel stress includes recall/backspace/reset
in100000 cycles and retains its16-byte marker gap. A visible recall binding
and draft-preserving navigation need their own interaction design/test.

`kconsole_recall` adds separate trusted navigation state with one fixed draft
buffer allocated at creation. `previous` visits newest-to-oldest retained lines;
`next` moves toward newer lines and then restores the saved draft. Reaching an
end returns false without changing input. Empty history is a no-op. Before
editing, submitting or resetting, callers must `detach` so the current line
becomes the draft; bypassing that contract while navigation is active is not
supported. History content/count stay unchanged. There is still no keyboard
binding or change to the existing display-only demo.

Hosted checks exercise wrapped history, empty entries, both ends, draft
restoration and detach/edit on interpreter/GCC/x64/native-seed paths. The
native/reference kernel stress includes previous/next/detach in100000 cycles
with the same16-byte marker gap. This is navigation state, not a public widget
API, a concurrent aliasing contract or an indefinite-session guarantee.

The fixed demo now consumes only `readkey_event()` for input. Extended Up and
Down browse retained history in accepted IRQ order with ASCII edits. The first
Up saves the current draft, Down past the newest entry restores it, and typing,
backspace or Enter detaches the recalled line before changing/submitting it.
Both ends are no-ops; empty recalled entries clear the active row. This
supersedes the earlier no-keyboard-binding limitation for this demo only.

The real GRUB gate retains complete native/reference image equality, existing
finite ASCII allocation checks, cursor/capacity checks and original transcript
pixels. It additionally verifies mixed ASCII/arrow ordering and full active-row
glyph/background pixels through both history ends, draft restoration, editing
a recalled line, submission/reset and an empty recalled entry. Guest screenshots
were visually inspected. This remains display-only input, never command
execution; no cursor-left/right, selection, terminal emulation or hardware
keyboard support is added.

The real GRUB gate now also measures256 paced Up/Down events through the actual
production binding, with full active-row/cursor pixels checked after every key.
Each pair recalls an empty newest entry and restores G. Test-only X/Y markers
bracket dequeue, storage, redraw and serial diagnostics; the finite bump-pointer
gap is16bytes, solely the final allocation marker. Test-only legacy-navigation
logging retains its label before the interval rather than allocating a label
per event. Complete native/reference instrumented images must match. The final
restored-draft guest screen was visually inspected. This bounded sequence does
not prove arbitrary input allocation, burst losslessness, indefinite session
lifetime or real-hardware behavior.
