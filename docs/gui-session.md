# Emulated ring-3 GUI session

This prototype joins the existing Multiboot2 framebuffer, compositor,
window syscalls and ramdisk loader into one bootable session. It starts one
ring-3 scratchpad, not a shell or a general desktop. Input is display-only:
no commands execute, no files are saved, and no disk or network is needed.

On Linux with GRUB BIOS modules, xorriso, Python 3 and QEMU:

```
scripts/build-gui-iso.sh /tmp/hs-gui.iso
qemu-system-x86_64 -cdrom /tmp/hs-gui.iso -boot d -m 256M -nic none -serial stdio
```

The build checks the pinned native hs compiler hash and compiles both
kernel and user code with native hs tools. Python only packs the KRFS
ramdisk; it is not used as a language compiler in this build. GRUB/xorriso
package the ISO. An existing output is never overwritten. The ISO contains
only the scratchpad app, not the example shell or sample ramdisk files.
Set `HS_TEST_GRUB_DIR` to the BIOS module directory when GRUB cannot find
it, for example `/usr/lib/grub/i386-pc`.

- Click the window body to focus it. Keyboard focus is not hover-driven.
- Type using the existing unshifted PS/2 key map. The 5x7 font displays
  lowercase letters as uppercase. This is not a Unicode editor.
- Up to 60 printable bytes fit on the single line. Extra bytes are ignored.
- Backspace removes a byte; Enter clears the line; Down closes the app.
- Drag the six-pixel title strip to move the window. Pointer movement,
  focus changes and dragging repaint during the kernel's input wait,
  without needing a key press.
- On exit the window and its input queues are removed, and the kernel
  remains alive on an empty desktop. There is no launcher or restart key.

## Boot and display contracts

GRUB supplies one `module2` KRFS ramdisk. The new MB2 decoder validates the
whole bounded tag chain, module endpoints, command-string termination,
end marker and initial identity-map range before exposing any module.
Modules below the kernel image, overlapping the runtime bump arena or
boot-info block, or outside the initial 1GiB mapping are rejected. Invalid
module indexes return zero endpoints. Existing QEMU/spec module layouts
remain supported. The GUI requires exactly one module and verifies the
PMM reserved both endpoints before allocating its heap or loading the app.

The kernel accepts the framebuffer module's validated RGB24/32 descriptor
and requires at least 640x480. The compositor still repaints the full scene;
this is not incremental damage composition. Surface rectangle fills,
blits and channel-aware flushes now keep their inner pixel loops in raw
integer code, retaining clipping and the unused fourth byte. The GUI does
not change syscall numbers or let user code choose framebuffer addresses.

## Evidence and limits

`tests/test_gui_session.py` boots real GRUB ISOs on both kernel backends.
The IR case exercises the actual packaging script and verifies the shipped
native kernel and user ELF bytes against independent Python-compiled
images. Real PS/2 input drives focus, typing, deletion, clear, the 60-byte
cap, drag, desktop focus loss, refocus and exit. Independent literal glyph
rows check every RGB byte of the input field. Body pixels must survive a
move, and exit must clear all non-cursor pixels. `HS_REQUIRE_GUI=1` makes
missing boot dependencies a failure. `HS_GUI_EVIDENCE` retains serial logs
and guest screenshots. Full CI has an explicit required invocation.
`tests/test_mbmodules.py` checks malformed/bounded MB2 parsing on both
kernel backends. Adjacent surface/window suites check RGB24/32 behavior.

Local edit-to-present timings are printed as diagnostics, not a hardware
performance promise. This remains a single-app experimental session with
an allocation-only language runtime and busy waits. Long-running memory
stability, multitasking isolation, storage, GPU acceleration, UEFI and
real-machine keyboard/mouse/display support are not established. Do not
write the ISO to a physical disk as part of this workflow. Hardware boot
is a separate user decision.
