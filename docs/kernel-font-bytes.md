# Trusted byte-span framebuffer text

`kfont.draw_bytes(frame,x,y,address,length,color,scale)` is a separate kernel
entrypoint for fixed-buffer text. It does not replace the string draw API.
The caller owns a readable byte span in low memory and a validated/mapped
framebuffer. Address must be positive, length0..1024, and address+length at
most536870911. Coordinates/color and scale1..16 validate before framebuffer
writes; length/address/scale are strict integer operands. This is not memory
mapping validation or protection against malicious pointers/state.

Byte10 starts a new line, ASCII lowercase folds to uppercase, other bytes
use the same5x7 bitmap/fallback layout. Length is bytes, not Unicode characters;
zero bytes do not terminate the span and unknown bytes use '?'. The span is
never copied or modified. It must remain valid for the whole call. Glyph
lookup reads the existing font table without copying glyph Lists. Valid
rendering uses while loops and scalar state only. `fill` now uses explicit
conditional statements instead of ternary expressions whose current parser
lowering constructs temporary singleton Lists. String rendering otherwise
keeps its established behavior and validation.

The raw byte test builds complete matching native/Python kernel images and
checks22 clipped/scaled/newline/case/fallback labels against independent RGB24
and RGB32 byte oracles, preserving outer/pitch/fourth-byte guards. Invalid
arguments leave pixels unchanged. Then1000 actual H/newline/I draws with
framebuffer writes run between raw allocation markers; their addresses differ
by exactly16 bytes, the marker's aligned allocation size. This proves no
intervening bump allocation in that finite kernel path, not performance or
an infinite-lifetime statement. Default CI builds the kernel driver from the
audited seed; --python-bootstrap is a local diagnostic route. Existing font
and console visual gates remain.

This does not yet connect the fixed console byte state to keyboard/rendering.
`readkey`, string APIs, logging and snapshots may allocate. General kernel
heap reclamation, hostile-memory protection and indefinitely usable terminal
sessions remain unresolved. No GC or measured speedup claim.
