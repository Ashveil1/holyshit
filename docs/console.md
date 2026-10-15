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

The prototype has no scrollback, multi-line history, event queue, model runtime,
agent subsystem, filesystem commands or applications. Redraw is synchronous;
the existing one-slot keyboard backend can drop input typed during redraw.
This is a proof of screen-plus-keyboard, not a usable daily terminal.
