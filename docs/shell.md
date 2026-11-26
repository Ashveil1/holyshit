# Shell-first boot

The default image boots straight into an interactive text shell, Arch-style:
no boot menu, no desktop, GRUB hands the kernel to the ring3 shell (`uush`)
and the boot framebuffer is its console. What you type echoes on screen,
output renders on screen, and the serial line keeps the raw byte log.

    scripts/build-gui-iso.sh out.iso            # shell is the default app
    scripts/build-gui-usb.sh out.img            # same, as a UEFI USB image
    scripts/build-gui-iso.sh out.iso desktop    # the desktop, explicitly

Supported here:

- the `shell` app mode of both packaging scripts, and it is the default when
  no app argument is given; the desktop modes (`scratchpad|desktop|
  desktop-disk|desktop-usb`) are unchanged and remain explicitly selectable;
- commands: `help echo cat ls mkdir rm write edit run sync exit`, served by the
  kernel syscall layer over the ramdisk VFS (`run` execs an ELF from the VFS
  and is one-shot: the new program replaces the shell until it exits);
- `edit FILE` is a line editor: typed text appends a line; `.list`,
  `.del N`, `.save` and `.quit` (discard) are the commands. It loads an
  existing file's lines, and save rewrites the whole file;
- `run PROG` replaces the shell until PROG exits; the kernel then prints
  `[PROG exited CODE]` and respawns the shell (same line on serial as
  `program exit PROG CODE`);
- `exit` respawns the shell getty-style, so a fresh prompt follows normal exit;
- PS/2 keyboard input with echo and backspace on the framebuffer console
  (48 columns x 16 retained lines, scrolling), 640x480 and up;
- the `shell-usb` variant (`scripts/build-gui-iso.sh out.iso shell-usb`)
  takes keyboard input from a USB keyboard over xHCI instead of PS/2 (the
  kernel never reads PS/2 in this mode); the default image stays the PS/2
  shell.

- the `shell-disk` variant (`scripts/build-gui-iso.sh out.iso shell-disk`,
  ISO only) mounts a KVOL volume from the primary IDE disk at boot and
  restores its files before the packaged `/bin` is loaded; `sync` saves
  them back (`/bin` is never written to the volume, so the 128 KiB cap
  counts user files only). It reports `volume: restored files`, `blank` or
  `no disk` on the console. QEMU disposable disks only: `sync` writes sector
  0 of the primary IDE disk, is not an atomic commit, and there is no
  real-hardware disk support. The default image never touches a disk;
- `cat` and `ls` end their output with a newline so the next prompt starts
  on its own line.

This does not provide a USB keyboard at the shell (the desktop's xHCI path
is a separate target), a scripting language, pipes or redirection, disk
writes beyond the existing kvfs semantics, networking, or any claim about
specific machines. The desktop stays in the tree and its gates unchanged.

Verified by `tests/test_shell_boot.py` on both kernel backends: the
packaging script's no-argument default build is proven byte-identical to the
reference kernel/user builds, then the image boots as a BIOS El Torito ISO
and as OVMF USB mass storage, a typed session (help, ls, cat, write, rm,
exit) is asserted on the serial log, the framebuffer screendump proves the
console rendered it, and `exit` is followed by a fresh shell prompt.
