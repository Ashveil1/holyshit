# Experimental keyboard screen

`kernel/kconsole_demo.holy` combines the RGB framebuffer, software bitmap labels
and bounded keyboard line state. It accepts one line, redraws it after each
key and stops after submission. It executes no commands. Lowercase keyboard
input displays uppercase because the original boot font has uppercase shapes.

The test boots BIOS/GRUB in QEMU, checks native/Python kernel image equality,
injects a/b/backspace/c/enter, requires guest result ac, then checks the actual
screendump against independent A/C bitmap foreground and background pixels.
QEMU, GRUB tools and xorriso are optional dependencies; without them this
specific test skips. It does not prove real hardware, UEFI or Unicode input.

The prototype has no scrollback, multi-line history, general event queue, model runtime,
agent subsystem, filesystem commands or applications. Redraw is synchronous;
the keyboard FIFO retains up to 63 translated ASCII bytes during redraw,
then drops newest bytes on overflow. This is not lossless input or a
terminal event system. See [kernel.md](kernel.md) for the queue boundary.
This is a proof of screen-plus-keyboard, not a usable daily terminal.

A separate [multi-submission experiment](console-session.md) now keeps four
recent input lines and returns to editing after Enter. It still executes
nothing and has an explicit finite bump-heap lifetime limit. The original
single-line demo and its test remain unchanged.
