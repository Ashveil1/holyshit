# Separate PS/2 navigation input experiment

`readkey_nav()` is a direct-call xkernel-only builtin returning1 for extended
Up,2 for extended Down, or null when empty. It consumes an independent63-event
FIFO, with drop-newest overflow and caller-IF-preserving dequeue. It does not
allocate a string. Existing `readkey`/`readkey_code` continue sharing their
ASCII byte FIFO and do not receive these navigation events.

IRQ1 retains an E0 prefix until the next non-E0 byte. Only E0 48 and E0 50
make sequences produce navigation events; their release sequences and other
extended bytes are ignored. Repeated E0 prefixes remain pending. Ordinary
ASCII map behavior is unchanged, with no shift/keypad/Unicode/USB/SMP support.
The two queues do not preserve ordering between ASCII and navigation input;
callers needing a unified ordered event stream cannot infer it from this API.
E1/Pause handling is not implemented. An incomplete prefix has no timeout.

The generated translation helper is tested directly on IR and retained AST
kernels for prefix/make/release/unknown/repeated-prefix cases, queue isolation,
overflow and exact IF preservation for empty/nonempty dequeue. Native/reference
complete images must match;100000 empty polls of both APIs retain a16-byte
marker gap. Both compilers reject argument-count errors. The actual GRUB
keyboard gate injects Up/Down, requires exactly one event each and unchanged
ASCII edit/submission counts, then checks original guest text/cursor pixels.
The production GUI is still display-only and has no history keyboard binding.

The maintained hs emitter was regenerated with a refreshed mechanical-layer
patch and zero-fuzz forward replay checked. The pinned compiler was rebuilt,
independently source-audited, and verified seed==stage2==stage3. This is a
bounded BIOS/QEMU input experiment, not real-hardware validation.
