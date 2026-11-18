#!/bin/sh
# Package an existing boot tree as an x86-64 EFI-only optical image.
# No host disks, firmware settings or NVRAM are changed.
set -eu
if [ "$#" -ne 2 ]; then
  printf '%s\n' 'usage: scripts/package-gui-uefi.sh TREE OUTPUT.iso' >&2
  exit 2
fi
TREE=$1
OUTPUT=$2
MODULES=${HS_GRUB_EFI_DIR:-/usr/lib/grub/x86_64-efi}
if [ -e "$OUTPUT" ]; then
  printf '%s\n' 'UEFI output already exists' >&2
  exit 1
fi
for file in "$TREE/boot/kernel.elf" "$TREE/boot/ramdisk.krfs" "$TREE/boot/grub/grub.cfg" "$MODULES/modinfo.sh"; do
  test -f "$file" || { printf '%s\n' "missing UEFI input: $file" >&2; exit 1; }
done
for program in grub-mkimage mformat mmd mcopy xorriso; do command -v "$program"; done
WORK=$(mktemp -d "${TMPDIR:-/tmp}/hs-efi.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/tree/EFI/BOOT"
cp -R "$TREE/boot" "$WORK/tree/boot"
printf '%s\n' 'HS GUI EFI BOOT TREE' > "$WORK/tree/boot/hs-gui.marker"
cat > "$WORK/embedded.cfg" <<'GRUB'
search --file --set=root /boot/hs-gui.marker
set prefix=($root)/boot/grub
configfile /boot/grub/grub.cfg
GRUB
grub-mkimage -d "$MODULES" -O x86_64-efi -c "$WORK/embedded.cfg" -p /boot/grub \
  -o "$WORK/tree/EFI/BOOT/BOOTX64.EFI" part_gpt part_msdos fat iso9660 \
  search search_fs_file normal configfile multiboot2 all_video gfxterm echo boot
dd if=/dev/zero of="$WORK/tree/boot/efi.img" bs=1048576 count=8
mformat -i "$WORK/tree/boot/efi.img" ::
mmd -i "$WORK/tree/boot/efi.img" ::/EFI ::/EFI/BOOT
mcopy -i "$WORK/tree/boot/efi.img" "$WORK/tree/EFI/BOOT/BOOTX64.EFI" ::/EFI/BOOT/
xorriso -as mkisofs -R -J -e boot/efi.img -no-emul-boot -o "$WORK/efi.iso" "$WORK/tree"
(set -C; cat "$WORK/efi.iso" > "$OUTPUT")
