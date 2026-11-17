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

## Multi-window desktop option

```
scripts/build-gui-iso.sh /tmp/hs-desktop.iso desktop
qemu-system-x86_64 -cdrom /tmp/hs-desktop.iso -boot d -m 256M -nic none -serial stdio
```

The default build remains the original scratchpad. The explicit `desktop`
option packages a different ring-3 app, with two independent note windows
and a persistent launcher window. Both notes open at startup. Click a note
to type; Backspace deletes, Enter clears and Down closes that note. Each
note holds up to 32 bytes. Closing retains its text in the app's RAM.
Click the launcher and press 1 or 2 to reopen a closed note. Pressing an
already-open note's number does not create a duplicate. Down in the launcher
exits the whole session and clears every window. No note is saved to disk.

All three windows belong to one process. This does not add a scheduler,
separate processes, private address spaces or process isolation. Clicks
still choose focus and raise a window; its title strip can be dragged.
Overlapping notes retain their independent contents when raised or moved.
The kernel's new any-window key read preserves the recipient chosen when
the key entered its window queue, even if focus later changes. This avoids
waiting on an inactive note's four-second timeout before serving another.

`tests/test_desktop_session.py` boots both kernel backends and checks literal
RGB glyph pixels, independent edits, overlap/raise/drag, both notes closed
with launcher intact, retained text after reopen, the 32-byte cap, focus
loss and complete session exit cleanup. Native IR kernel/user image identity
and no-clobber ISO packaging checks apply here too. Full CI runs this as an
explicit required step and collects screenshots on failure.


## Readable desktop text

The desktop option draws labels and editable note text at scale2: each
5x7 glyph becomes10x14 pixels, with12-pixel character advance. The two
440x150 notes keep32-byte fields that fit entirely in the640x480 desktop.
The launcher uses the same larger text. The default scratchpad retains
its original scale1 layout and60-byte field; the scale change is only
for the explicit desktop option. The title drag strip remains six pixels.

Scaled drawing uses the new syscall100; legacy syscall98 remains fixed
at scale1. `tests/test_winscale.py` verifies all4096 RGB pixels of a real
ring3 drawing on both kernel backends, with all four scales, legacy98 in
the same image, lowercase/fallback/newline, left/right/bottom clipping,
invalid styles and user span rejection. Desktop tests independently
check each expanded glyph pixel in real GRUB screenshots, retaining the
existing edit/focus/overlap/reopen/cap/exit coverage. This is pixel scaling
of the existing font, not a new font engine or Unicode text shaping.
