# Experimental kernel framebuffer

The hs kernel can draw a static panel into a Multiboot2 RGB framebuffer.
The boot header makes an optional640x480x32 request; GRUB provides the mode.
The kernel validates the returned geometry, channel positions and pitch, then
maps the physical buffer as supervisor-writable with cache-disable/write-through
flags. Unsupported/missing modes fail rather than guessing an address.

On Linux with GRUB tools and xorriso installed:

```
scripts/build-framebuffer-iso.sh /tmp/hs-screen.iso
qemu-system-x86_64 -cdrom /tmp/hs-screen.iso -boot d -m 256M -serial stdio
```

The ISO build uses the pinned native hs compiler, not Python/gcc/as/ld. GRUB
and xorriso are external packaging dependencies. Do not write the ISO over a
real disk. Real-machine boot, UEFI and hardware compatibility are untested.
The demo stays in a busy loop after drawing; it has no power-management path.

`kernel/kframebuffer.holy` offers `descriptor()`, `map(frame)`, `pixel(...)` and
`rect(...)`. Descriptors come only from validated boot data; do not mutate
or fabricate them. Current supported modes have24/32bpp, distinct byte-aligned
8-bit RGB channels, dimensions at most4096, buffer size at most64MiB, and a
physical address range within1GiB..4GiB. This range deliberately avoids the
initial low-memory identity mapping. No palette/16bpp/high-address support.

The pictured panel is drawn directly by the kernel, but it is not a desktop:
no fonts, mouse, event loop, window manager, applications or persistence.
`std.gfx` software surfaces are a separate stage; the framebuffer prototype
uses its own direct clipped rectangles, with no dependency on an unmerged PR.

Validation: `tests/test_fbinfo.py` rejects malformed tags on four hosted
backends. `tests/test_framebuffer_kernel.py` requires native/Python kernel ELF
identity, boots the ISO in QEMU, waits for the serial ready marker and checks
actual screendump RGB pixels. The current full CI installs QEMU but not GRUB/xorriso, so this specific
boot-pixel test skips there until those optional dependencies are configured.
It has been run locally with all three tools. Existing full kernel/QEMU gates
still apply. This proves the emulated BIOS/GRUB route only.

Protocol layout source:
https://raw.githubusercontent.com/rhboot/grub2/master/include/multiboot2.h
