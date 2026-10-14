#!/bin/sh
# Source -> IR kernel ELF using only the verified native toolchain.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 2 ]; then
  printf '%s\n' 'usage: scripts/build-kernel-native.sh source.hs kernel.elf' >&2
  exit 2
fi
SOURCE=$1
OUTPUT=$2
case "$SOURCE" in /*) ;; *) SOURCE="$(pwd)/$SOURCE" ;; esac
if [ ! -f "$SOURCE" ]; then
  printf '%s\n' "source not found: $SOURCE" >&2
  exit 1
fi
(cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
export HSROOT="$ROOT"
export HSPATH="$ROOT:$ROOT/kernel:$ROOT/selfhost:$ROOT/selfhost/be${HSPATH:+:$HSPATH}"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/holyshit-kernel.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
"$ROOT/bootstrap/hs-hosted-x86_64" "$ROOT/selfhost/be/kernel_ir.hs" "$WORK/compiler"
"$WORK/compiler" "$SOURCE" "$WORK/kernel.elf"
# Leave an existing output untouched if parsing or compilation failed.
mv -- "$WORK/kernel.elf" "$OUTPUT"
