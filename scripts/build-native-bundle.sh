#!/bin/sh
# Assemble a relocatable native toolchain, without Python/gcc.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'usage: scripts/build-native-bundle.sh NEW_OUTPUT_DIRECTORY' >&2
  exit 2
fi
OUTPUT=$1
case "$OUTPUT" in /*) ;; *) OUTPUT="$(pwd)/$OUTPUT" ;; esac
if [ -e "$OUTPUT" ]; then
  printf '%s\n' "output already exists: $OUTPUT" >&2
  exit 1
fi
PARENT=$(dirname -- "$OUTPUT")
if [ ! -d "$PARENT" ]; then
  printf '%s\n' "parent directory not found: $PARENT" >&2
  exit 1
fi
(cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
WORK=$(mktemp -d "$PARENT/.holyshit-bundle.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
mkdir -p "$WORK/bin" "$WORK/bootstrap"
cp "$ROOT/bootstrap/hs-hosted-x86_64" "$ROOT/bootstrap/SHA256SUMS" "$WORK/bootstrap/"
cp -R "$ROOT/selfhost" "$ROOT/runtime" "$ROOT/std" "$WORK/"
cp "$ROOT/scripts/native-bundle-launcher.sh" "$WORK/bin/hs"
chmod +x "$WORK/bin/hs"
export HSROOT="$WORK"
export HSPATH="$WORK/selfhost:$WORK/selfhost/be:$WORK/std"
"$WORK/bootstrap/hs-hosted-x86_64" "$WORK/selfhost/be/jit_run.hs" "$WORK/bin/hs-eager"
(cd "$WORK" && sha256sum bin/hs-eager > EAGER_SHA256SUMS)
# No pre-existing destination is replaced. Build is staged on the same filesystem.
if [ -e "$OUTPUT" ]; then
  printf '%s\n' "output appeared during build: $OUTPUT" >&2
  exit 1
fi
mv -n -T -- "$WORK" "$OUTPUT"
if [ -d "$WORK" ]; then
  printf '%s\n' "output appeared during publish: $OUTPUT" >&2
  exit 1
fi
trap - EXIT HUP INT TERM
printf '%s\n' "native bundle: $OUTPUT"
