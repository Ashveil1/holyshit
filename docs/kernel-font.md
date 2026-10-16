# Direct framebuffer bitmap text

`kernel/kfont.holy` draws the existing ASCII bitmap labels directly through
`kframebuffer.pixel`, without constructing a software RGB surface or copying
its full pixel list onto the framebuffer. `draw(frame,x,y,text,color,scale)`
uses the existing font glyphs, lowercase folding, fallback, newline layout,
scale1..16, text1024-character cap and coordinate/color validation.
`fill(frame,x,y,width,height,color)` fills a clipped rectangle using while
loops, without materializing per-row/per-column range lists. Arguments validate
before writes; nonpositive widths/heights write nothing.

The caller must provide a validated, mapped RGB24/32 framebuffer descriptor,
as for `kframebuffer.pixel`. This is kernel memory access, not a safe boundary
for arbitrary user-provided addresses or corrupted frame descriptors. Pitch,
channel offsets and fourth/padding bytes retain the descriptor's semantics.

The multi-submission console uses this direct route for the header, panel and
text rows, instead of allocating header/entry software surfaces and copying
every pixel for each redraw. Its layout and visible text are unchanged.
The software `std.font`/`std.gfx` APIs and original console demo stay intact.

This removes those surface allocations/copy loops, not all allocations.
Glyph lookup still copies small glyph lists, strings/iteration can allocate,
and editing/history still use the non-reclaiming16MiB kernel bump heap. Long
sessions may still OOM; this is not a GC, allocator replacement, zero-allocation
renderer, indefinite-terminal guarantee or a measured speedup claim.

`tests/test_kfont.py` runs actual generated native/Python-matching kernels in
QEMU against independent byte oracles for RGB24 and RGB32. It checks22 clipped,
scaled/newline/case/fallback labels, padding/fourth-byte/outer guards and
no writes after invalid arguments. The existing GRUB multi-submission test
checks real framebuffer text pixels with this renderer. GRUB/xorriso remain
optional, while the raw-memory QEMU oracle needs only QEMU.
