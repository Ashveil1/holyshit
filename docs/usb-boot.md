# Bootable USB image (UEFI)

`scripts/build-gui-usb.sh` builds the same GUI desktop as
`scripts/build-gui-iso.sh` but packages it as a raw disk image instead of an
ISO: protective MBR, GPT, and one FAT32 EFI System Partition holding GRUB as
`/EFI/BOOT/BOOTX64.EFI` plus the kernel, ramdisk and `grub.cfg` under
`/boot`. Write the image to a USB stick with `dd` and UEFI firmware boots it
as removable media. There is no El Torito and no optical emulation anywhere
in this path.

    scripts/build-gui-usb.sh out.img desktop
    dd if=out.img of=/dev/sdX bs=4M conv=fsync    # pick the right device!

Supported here:

- x86-64 UEFI firmware with the standard removable-media fallback path
  (`\EFI\BOOT\BOOTX64.EFI`), the same contract the UEFI ISO already relies
  on;
- GPT written by `scripts/mkgpt.py` (deterministic, no loop devices or
  root), FAT32 written by mtools at the partition offset;
- the same app modes as the ISO builder
  (`shell|shell-usb|scratchpad|desktop|desktop-disk|desktop-usb`); with no
  app argument the image boots the shell (see [shell.md](shell.md)), so
  pass an explicit desktop mode for the GUI.

This does not provide a legacy BIOS boot path, Secure Boot signing, an
installer, persistence, or any claim about specific machines. The image is
verified by booting it in QEMU as a USB mass-storage device on qemu-xhci
under OVMF (`tests/test_usb_boot.py`, both kernel backends): OVMF's own
XHCI, USB mass-storage, GPT and FAT drivers load GRUB off the ESP, the
desktop reaches its ready state, the OVMF boot log names the USB harddrive
as the boot entry, and the image, firmware ROM and variables template are
byte-identical afterwards. That is firmware-emulated USB boot. It is not
tested on an HP or any physical stick, controller or firmware, and it makes
no statement about real-hardware quirks (boot-order menus, stick geometry,
controller behavior). The kernel's own xHCI driver scope is separate; see
[xHCI scope and gates](xhci.md).

The packaging identity gate extracts `kernel.elf` and the ramdisk back out
of the image and compares them against reference builds, so the shipped
script output is what the tests reviewed, not a lookalike.
