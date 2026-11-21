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
Modules overlapping the kernel image, runtime bump arena or boot-info
block, or outside the initial 1GiB mapping are rejected. A module below
the kernel is accepted only within the conservative range4096..655360;
spans through the gap below the1MiB image base are rejected. EFI GRUB
uses this low-module placement. The first page remains forbidden. Invalid
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
stability, multitasking isolation, GPU acceleration and real-machine
keyboard/mouse/display support are not established. UEFI is tested only
with emulated OVMF, as described below. Do not
write the ISO to a physical disk as part of this workflow. Hardware boot
is a separate user decision.

## Multi-window desktop option

```
scripts/build-gui-iso.sh /tmp/hs-desktop.iso desktop
qemu-system-x86_64 -cdrom /tmp/hs-desktop.iso -boot d -m 256M -nic none -serial stdio
```

The default build of the packaging scripts is the shell (see [shell.md](shell.md)); pass `scratchpad` explicitly for the original single-line app. The explicit `desktop`
option packages a different ring-3 app, with two independent note windows
and a persistent launcher window. Both notes open at startup. Click a note
to type at its caret. Left/Right move one source byte, Up/Down move to the
closest column on the adjacent visual row, and Home/End move within the
current visual row. Backspace removes the preceding byte; Delete removes
the following byte. Enter inserts a newline. Each note holds three visual
rows of up to32 printable bytes each, with automatic wrapping. An insertion
that would need a fourth row is ignored without changing the text or caret.
Escape closes the focused note and keeps its text and caret in RAM. Click
the launcher and press 1 or 2 to reopen a closed note; pressing an already-open
note's number does not create a duplicate. Launcher keys3 and4 clear note1
and note2 respectively, including a closed note. Escape in the launcher
exits the session and clears every window. No note is saved to disk.

All three windows belong to one process. This does not add a scheduler,
separate processes, private address spaces or process isolation. Clicks
still choose focus and raise a window; its title strip can be dragged.
Overlapping notes retain their independent contents when raised or moved.
The kernel's new any-window key read preserves the recipient chosen when
the key entered its window queue, even if focus later changes. This avoids
waiting on an inactive note's four-second timeout before serving another.

`tests/test_desktop_session.py` boots both kernel backends and checks literal
RGB glyph pixels, independent edits, overlap/raise/drag, both notes closed
with launcher intact, retained multiline text after reopen, the three-line cap, focus
loss and complete session exit cleanup. Native IR kernel/user image identity
and no-clobber ISO packaging checks apply here too. Full CI runs this as an
explicit required step and collects screenshots on failure.


## Readable desktop text

The desktop option draws labels and editable note text at scale2: each
5x7 glyph becomes10x14 pixels, with12-pixel character advance. The two
440x150 notes keep three-line fields that fit entirely in the640x480 desktop.
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


## Bounded cursor editing

Each note has128 bytes of source storage and128 bytes of reusable rendered
storage. It stores at most98 source bytes: up to96 printable bytes plus two
explicit newline bytes. Automatic wraps are computed rather than stored,
so insertion and deletion in the middle reflow later text. Backspace or
Delete at an explicit newline joins its two rows. Enter on an empty row is
allowed until the third row; no fourth row is created. A proposed insertion
is checked against the complete resulting buffer before any bytes move.

The caret is a source-byte offset, retained across close/reopen and reset
by clear. At a soft-wrap boundary it belongs to the next visual row when
there is another character there. At the end of a full row it may sit after
column32. Vertical movement chooses the nearest available column in the
adjacent row, with the first matching stop winning a tie. It does not retain
a separate preferred column through a shorter row. The blue block marks
the caret. No selection, undo, scrolling, Shift input, Unicode shaping or
disk storage is added. The original default single-line scratchpad is unchanged.

`kernel/unotebuf.holy` owns these bounds independently of the GUI. Its
hosted x86 tests check both compiler backends with45 direct pins, source
storage canaries, spare bytes, independent notes, close/reopen, and30
repeated full edit/reflow cycles. An independent Python model compares
source bytes, caret offset, visual position and rendered bytes after each
of420 deterministic mixed edits on both backends. The required desktop
GRUB test checks every RGB field byte for middle insertion/deletion,
Home/End, cross-line arrows, manual newlines, reflow, full capacity,
retained text/caret on reopen and complete exit cleanup. Event codes128
through135 pass through the existing focused window queues; ASCII input
and legacy Up/Down codes retain their backend meanings.


## Explicit disposable-disk desktop (QEMU only)

The `desktop` and default scratchpad options still do not mount a disk.
A separate `desktop-disk` build opts into the existing primary-IDE KVOL
prototype. Use only a new disposable raw image, never a physical disk,
partition, host block device or an image containing data you need:

```
scripts/build-gui-iso.sh /tmp/hs-desktop-disk.iso desktop-disk
python3 - <<'PYDISK'
with open('/tmp/hs-notes.img', 'xb') as image:
    image.truncate(1024 * 1024)
PYDISK
qemu-system-x86_64 -cdrom /tmp/hs-desktop-disk.iso -boot d -m 256M -nic none -serial stdio -drive file=/tmp/hs-notes.img,if=ide,format=raw
```

Creating an image this way refuses to overwrite an existing file. On later
boots, reuse that same image without recreating it. The application loads
`/note1` and `/note2` automatically. Click the launcher and press5 to save
both notes explicitly. A note footer distinguishes unsaved text, saved
text, failed save and unavailable storage. Navigation alone does not make
saved text dirty. Returning to the last saved text restores its saved
status. Close/reopen retains the current RAM edit and caret; reboot loads
only the last explicit save and puts the caret at its end. Escape exits
without saving. Clearing a note is not a disk deletion until5 saves it.

A missing disk, corrupt recognized volume or invalid saved note leaves the
GUI usable in RAM and refuses saves. A saved note containing control bytes,
high bytes, more than98 source bytes or more than three visual rows is
rejected as a whole, not interpreted as editor keys or silently truncated.
Invalid saved data is not overwritten. An unrecognized non-KVOL disk is
still treated as an empty volume by the existing storage prototype, so
this option is ONLY for the disposable image above. It is not a safe disk
installer or a hardware storage probe.

The disk kernel reloads the trusted app from the boot ramdisk after mounting
the volume, copies its ELF to user pages, then removes that app file from
the VFS before saves. This keeps executable bytes out of the128KiB volume
budget. The application receives storage readiness through a kernel-written
`/desktop-mode` file. It uses existing file syscalls and explicit sync74;
no new syscall, background autosave or hardware controller support is added.
`kguisession` shares boot/display/cleanup logic between the RAM and disk
kernels. ATA IDENTIFY now requires an actual data phase and rejects absent
or ATAPI slots before volume reads, including CD-only QEMU boots.

The KVOL format overwrites its payload in place and has no checksum,
dual-slot commit or ATA cache-flush barrier. A successful save is tested
through ordinary QEMU shutdown/reboot, NOT power-loss or interrupted-save
safety. The allocation-only runtime and whole-tree sync also remain bounded
prototype limits, not a long-running editor guarantee.

`tests/test_desktop_disk.py` boots real GRUB images on both backends, edits
notes through PS/2 input, checks literal field pixels and dirty-status
transitions, explicitly saves, kills QEMU and verifies two later boot
restores. It checks unsaved exit leaves the disk unchanged, a saved empty
note, missing-disk refusal, corrupt volume refusal, and malformed/oversized
note refusal with exact host-side disk-byte equality. The IR packaging
case checks full native-seed kernel and app ELF equality. Full CI requires
this suite and retains screenshots on failure. No real-machine trial is
part of this workflow.


## Opt-in x86-64 UEFI desktop (OVMF only)

BIOS remains the default. A third build argument selects an EFI-only optical
image without changing the kernel compiler or native seed:

```
scripts/build-gui-iso.sh /tmp/hs-uefi.iso desktop uefi
```

This requires GRUB x86-64 EFI modules, `grub-mkimage`, mtools and xorriso in
addition to the normal build tools. On Debian/Ubuntu the extra packages are
`grub-efi-amd64-bin`, `mtools` and `ovmf`. `HS_GRUB_EFI_DIR` overrides the
module directory (default `/usr/lib/grub/x86_64-efi`). The same explicit
firmware argument also packages scratchpad or disposable-disk mode; the
required UEFI GUI gate uses only the no-disk desktop.

`scripts/package-gui-uefi.sh` packages an existing boot tree, embeds the
GRUB modules in `EFI/BOOT/BOOTX64.EFI`, creates a small FAT El Torito image,
and boots the existing Multiboot2 kernel and module. An embedded GRUB
configuration finds the optical boot tree through its marker file. Outputs
are never overwritten. This is not an installer, a signed Secure Boot image,
or a tested bootable USB layout. Do not write it to physical media as part
of this workflow.

Run the required emulator gate with:

```
HS_REQUIRE_GUI=1 HS_REQUIRE_UEFI=1 python3 tests/test_uefi_desktop.py
```

It locates an OVMF code/variables pair, or accepts `HS_OVMF_CODE` and
`HS_OVMF_VARS`. The matching standard variables filename is inferred when
only the code path is supplied. Code is attached read-only and the variables
template is copied to a disposable file. The source files are checked
unchanged afterward; no host firmware or real NVRAM is accessed. Both the
2MiB and4MiB OVMF layouts have been checked locally. Use matching code and
variables files with Secure Boot disabled and no enrolled keys.

EFI GRUB can place the ramdisk below the kernel rather than after it.
`kmb` now accepts only bounded low ranges disjoint from the image, runtime
arena and boot information. `kpmm` explicitly reserves module spans; the
existing low-memory/image reservation also covers low modules. Synthetic
pins exercise both sides of the low-limit/image boundaries and retain all
malformed-chain refusals. The GUI checks both module endpoint pages are
reserved before allocating or running user code.

The UEFI gate verifies an actual EFI El Torito boot catalog, the module
range in serial output, the640x480 framebuffer and every existing desktop
pixel/input case: PS/2 typing, middle edits, caret movement, focus, raise,
drag, close/reopen and full cleanup. A sentinel disk stays byte-identical
and no volume probe occurs. Local OVMF runs exercise the low placement;
other firmware versions may place a valid module above the image. The native IR case uses the actual packaging
script and checks all kernel/app ELF bytes; the AST kernel boots too. Full
CI requires the UEFI gate and retains screenshots on failure.

This establishes an OVMF boot path, not compatibility with Ash's HP. Secure
Boot, USB keyboard/mouse, laptop touchpad buses, actual firmware graphics
modes, storage controllers and hybrid GPU behavior remain unverified. No
HP trial or firmware change is authorized by this emulator test.
