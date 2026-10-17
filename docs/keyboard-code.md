# Kernel keyboard byte codes without Str allocation

`readkey_code()` is a direct-call xkernel-only builtin. It atomically consumes
one existing keyboard FIFO byte and returns its Int code, or null when empty.
It uses the same63-byte/drop-newest/single-CPU queue and IF-preserving dequeue
helper as `readkey`; calls to either API consume from that same queue. It does
not return scancodes or change PS/2 translation, key-up/modifier/ASCII limits.
Zero remains the internal empty sentinel and is not delivered. This API does
not allocate a one-character Str. Existing `readkey()` remains unchanged.
It is not a first-class builtin value or a hosted stdin API.

`kernel/kconsole_fixed.holy` now feeds the integer directly into fixed console
storage, removing its unsafe Str-payload helper. Thus this route no longer
allocates the prior32-byte keyboard Str per consumed byte. The static header
and serial diagnostics still use normal string APIs; do not infer a measured
total-session zero-allocation/indefinite-terminal guarantee. The kernel still
has its16MiB non-reclaiming bump heap, counter overflow/resource failures are
not solved, FIFO bursts can still drop keys and no real-hardware claim is made.

The deterministic queue QEMU gate preserves the original readkey behavior and
burst/wrap/overflow/exact IF checks on IR and retained AST kernels. It also
consumes codes1..63 then null and proves exact16byte marker distance around
the complete polling loop, only the one-byte marker's alignment allocation.
A seed-native kernel driver must produce the complete Python-matching image;
that kernel performs100000 empty polls with the same finite allocation proof.
Both Python and native compilers reject arity errors. The existing actual
GRUB six-submission console gate verifies real PS/2 delivery and unchanged
C/D/E/F/currentG pixels locally (GRUB gate remains optional in stock CI).

Backend port regeneration was rebuilt against the exact mechanical layer,
with prior maintained adaptations preserved and only the new builtin changed
in the maintained emitter. Zero-fuzz forward regeneration must match. The
updated pinned compiler is9,319,480 bytes, SHA256
`1813d93f993fc24a91252f8ae47cb958f43d45c6074bb91b0a55d00a9beb391b`.
It was source-audited before execution and passed seed==stage2==stage3 with no
Python in those later stages. Full CI repeats the audit/bootstrap/image gates.
This is a narrow kernel input/lifetime feature, not a new execution tier.
