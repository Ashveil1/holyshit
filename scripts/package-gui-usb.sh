#!/bin/sh
# Package an existing boot tree as a raw GPT/ESP image for x86-64 UEFI USB
# boot: protective MBR, GPT, one FAT32 EFI System Partition holding GRUB as
# /EFI/BOOT/BOOTX64.EFI plus the kernel, ramdisk and grub.cfg under /boot.
# Write it to a USB stick with dd; firmware boots it as removable media.
# No host disks, firmware settings or NVRAM are changed.
set -eu
if [ "$#" -ne 2 ]; then
  printf '%s\n' 'usage: scripts/package-gui-usb.sh TREE OUTPUT.img' >&2
  exit 2
fi
TREE=$1
OUTPUT=$2
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULES=${HS_GRUB_EFI_DIR:-/usr/lib/grub/x86_64-efi}
if [ -e "$OUTPUT" ]; then
  printf '%s\n' 'USB output already exists' >&2
  exit 1
fi
for file in "$TREE/boot/kernel.elf" "$TREE/boot/ramdisk.krfs" "$TREE/boot/grub/grub.cfg" "$MODULES/modinfo.sh"; do
  test -f "$file" || { printf '%s\n' "missing USB input: $file" >&2; exit 1; }
done
for program in grub-mkimage mformat mmd mcopy; do command -v "$program"; done
WORK=$(mktemp -d "${TMPDIR:-/tmp}/hs-usb.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/esp/EFI/BOOT" "$WORK/esp/boot/grub"
cp "$TREE/boot/kernel.elf" "$TREE/boot/ramdisk.krfs" "$WORK/esp/boot/"
cp "$TREE/boot/grub/grub.cfg" "$WORK/esp/boot/grub/"
printf '%s\n' 'HS GUI EFI BOOT TREE' > "$WORK/esp/boot/hs-gui.marker"
cat > "$WORK/embedded.cfg" <<'GRUB'
search --file --set=root /boot/hs-gui.marker
set prefix=($root)/boot/grub
configfile /boot/grub/grub.cfg
GRUB
grub-mkimage -d "$MODULES" -O x86_64-efi -c "$WORK/embedded.cfg" -p /boot/grub \
  -o "$WORK/esp/EFI/BOOT/BOOTX64.EFI" part_gpt part_msdos fat iso9660 \
  search search_fs_file normal configfile multiboot2 all_video gfxterm echo boot
OFFSET=$(python3 "$ROOT/scripts/mkgpt.py" "$WORK/usb.img" 52)
mformat -i "$WORK/usb.img@@$OFFSET" -F ::
mmd -i "$WORK/usb.img@@$OFFSET" ::/EFI ::/EFI/BOOT ::/boot ::/boot/grub
mcopy -i "$WORK/usb.img@@$OFFSET" "$WORK/esp/EFI/BOOT/BOOTX64.EFI" ::/EFI/BOOT/
mcopy -i "$WORK/usb.img@@$OFFSET" "$WORK/esp/boot/kernel.elf" "$WORK/esp/boot/ramdisk.krfs" ::/boot/
mcopy -i "$WORK/usb.img@@$OFFSET" "$WORK/esp/boot/grub/grub.cfg" ::/boot/grub/
mcopy -i "$WORK/usb.img@@$OFFSET" "$WORK/esp/boot/hs-gui.marker" ::/boot/
(set -C; cat "$WORK/usb.img" > "$OUTPUT")
