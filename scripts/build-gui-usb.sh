#!/bin/sh
# Native hs kernel/user compilation plus a raw GPT/ESP USB image for x86-64
# UEFI firmware. The output is a disk image, not an ISO: write it to a USB
# stick with dd (or attach it as usb-storage in QEMU).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  printf '%s\n' 'usage: scripts/build-gui-usb.sh OUTPUT.img [shell|shell-usb|scratchpad|desktop|desktop-disk|desktop-usb]' >&2
  exit 2
fi
APP=${2:-shell}
KERNEL=kgui
case "$APP" in shell) SOURCE=uush; KERNEL=kshell ;; shell-usb) SOURCE=uush; KERNEL=kshellusb ;; scratchpad) SOURCE=uunote ;; desktop) SOURCE=uudesk ;; desktop-disk) SOURCE=uudesk; KERNEL=kguidisk ;; desktop-usb) SOURCE=uudesk; KERNEL=kguiusb ;; *) printf '%s\n' 'unknown GUI app' >&2; exit 2 ;; esac
OUTPUT=$1
case "$OUTPUT" in /*) ;; *) OUTPUT="$(pwd)/$OUTPUT" ;; esac
if [ -e "$OUTPUT" ]; then
  printf '%s\n' "output already exists: $OUTPUT" >&2
  exit 1
fi
WORK=$(mktemp -d "${TMPDIR:-/tmp}/hs-gui.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/tree/boot/grub" "$WORK/stage/bin"
(cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
export HSROOT="$ROOT"
export HSPATH="$ROOT:$ROOT/kernel:$ROOT/selfhost:$ROOT/selfhost/be${HSPATH:+:$HSPATH}"
"$ROOT/bootstrap/hs-hosted-x86_64" "$ROOT/selfhost/be/compile.holy" "$WORK/compiler"
if [ "$APP" = shell ] || [ "$APP" = shell-usb ]; then
  cp -R "$ROOT/kernel/ramdisk/." "$WORK/stage/"
  "$WORK/compiler" "$ROOT/kernel/uush.holy" "$WORK/stage/bin/uush"
  "$WORK/compiler" "$ROOT/kernel/uuhi.holy" "$WORK/stage/bin/hi"
else
  "$WORK/compiler" "$ROOT/kernel/$SOURCE.holy" "$WORK/stage/bin/uunote"
fi
"$ROOT/scripts/build-kernel-native.sh" "$ROOT/kernel/$KERNEL.holy" "$WORK/tree/boot/kernel.elf"
python3 "$ROOT/scripts/mkramdisk.py" "$WORK/stage" "$WORK/tree/boot/ramdisk.krfs"
cat > "$WORK/tree/boot/grub/grub.cfg" <<'GRUB'
set timeout=0
set default=0
insmod all_video
set gfxmode=640x480x32
set gfxpayload=keep
terminal_output gfxterm
menuentry hs {
  multiboot2 /boot/kernel.elf
  module2 /boot/ramdisk.krfs
  boot
}
GRUB
"$ROOT/scripts/package-gui-usb.sh" "$WORK/tree" "$WORK/gui.img"
(set -C; cat "$WORK/gui.img" > "$OUTPUT")
printf '%s\n' "$APP session USB image: $OUTPUT"
