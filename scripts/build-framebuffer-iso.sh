#!/bin/sh
# Build the experimental GRUB framebuffer demo using the pinned hs toolchain.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'usage: scripts/build-framebuffer-iso.sh OUTPUT.iso' >&2
  exit 2
fi
OUTPUT=$1
case "$OUTPUT" in /*) ;; *) OUTPUT="$(pwd)/$OUTPUT" ;; esac
if [ -e "$OUTPUT" ]; then
  printf '%s\n' "output already exists: $OUTPUT" >&2
  exit 1
fi
command -v grub-mkrescue >/dev/null
command -v xorriso >/dev/null
WORK=$(mktemp -d "${TMPDIR:-/tmp}/hs-framebuffer.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/tree/boot/grub"
"$ROOT/scripts/build-kernel-native.sh" "$ROOT/kernel/kframebuffer_demo.holy" "$WORK/tree/boot/kernel.elf"
cat > "$WORK/tree/boot/grub/grub.cfg" <<'GRUB'
set timeout=0
set default=0
insmod all_video
set gfxmode=640x480x32
set gfxpayload=keep
terminal_output gfxterm
menuentry hs {
  multiboot2 /boot/kernel.elf
  boot
}
GRUB
grub-mkrescue -o "$WORK/demo.iso" "$WORK/tree"
# Copy to a newly-created output, never replace an existing file.
(set -C; cat "$WORK/demo.iso" > "$OUTPUT")
printf '%s\n' "framebuffer demo ISO: $OUTPUT"
