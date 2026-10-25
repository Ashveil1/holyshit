# Ordered PS/2 keyboard events

`readkey_event()` is a direct-call xkernel-only builtin returning ASCII byte
codes,128 for extended Up,129 for extended Down, or null when empty. IRQ1
publishes these events into one independent63-event FIFO in translation order.
The queue drops newest input when full and dequeue preserves the caller's IF.
Empty and nonempty polls do not allocate strings.

The existing ASCII and navigation queues remain unchanged. Their consumers do
not drain this stream, and this stream does not drain them. Choose one stream
for a consumer needing ordered mixed input. Each queue can overflow separately;
ordering applies to accepted events, not to dropped input. Direct diagnostic
calls to legacy enqueue helpers do not publish unified events.

The production GUI remains display-only and does not yet bind arrow history.
Deterministic IR/AST tests cover mixed order, wrap, overflow, legacy isolation
and exact IF preservation. Native/reference complete images match;100000 empty
polls of all three integer APIs retain a16-byte allocation marker gap. A real
GRUB session injects mixed ASCII/Up/Down/backspace/Enter input and checks the
exact ordered event sequence while retaining console pixel and allocation gates.

This is a bounded BIOS/QEMU experiment. It does not add real-hardware validation,
USB, shift handling, Unicode, E1/Pause, prefix timeouts, or SMP support.
