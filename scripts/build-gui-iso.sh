#!/bin/sh
# Native hs kernel/user compilation plus GRUB BIOS ISO packaging.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'usage: scripts/build-gui-iso.sh OUTPUT.iso' >&2
  exit 2
fi
OUTPUT=$1
case "$OUTPUT" in /*) ;; *) OUTPUT="$(pwd)/$OUTPUT" ;; esac
if [ -e "$OUTPUT" ]; then
  printf '%s\n' "output already exists: $OUTPUT" >&2
  exit 1
fi
command -v grub-mkrescue
command -v xorriso
WORK=$(mktemp -d "${TMPDIR:-/tmp}/hs-gui.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/tree/boot/grub" "$WORK/stage/bin"
(cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
export HSROOT="$ROOT"
export HSPATH="$ROOT:$ROOT/kernel:$ROOT/selfhost:$ROOT/selfhost/be${HSPATH:+:$HSPATH}"
"$ROOT/bootstrap/hs-hosted-x86_64" "$ROOT/selfhost/be/compile.holy" "$WORK/compiler"
"$WORK/compiler" "$ROOT/kernel/uunote.holy" "$WORK/stage/bin/uunote"
"$ROOT/scripts/build-kernel-native.sh" "$ROOT/kernel/kgui.holy" "$WORK/tree/boot/kernel.elf"
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
if [ -n "${HS_TEST_GRUB_DIR:-}" ]; then
  grub-mkrescue -d "$HS_TEST_GRUB_DIR" -o "$WORK/gui.iso" "$WORK/tree"
else
  grub-mkrescue -o "$WORK/gui.iso" "$WORK/tree"
fi
(set -C; cat "$WORK/gui.iso" > "$OUTPUT")
printf '%s\n' "GUI session ISO: $OUTPUT"
