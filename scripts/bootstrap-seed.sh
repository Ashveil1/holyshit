#!/bin/sh
# Verify the pinned seed before execution, then repeat the compiler fixed point.
set -eu
cd "$(dirname "$0")/.."
ROOT=$(pwd)
export HSPATH="$ROOT/selfhost:$ROOT/selfhost/be"
export HSROOT="$ROOT"
if [ ! -f bootstrap/hs-hosted-x86_64 ] || [ ! -f bootstrap/SHA256SUMS ]; then
  printf '%s\n' 'No verified seed installed. Use scripts/bootstrap-hosted.sh for source bootstrap.' >&2
  exit 1
fi
(cd bootstrap && sha256sum -c SHA256SUMS)
OUT=${1:-/tmp/holyshit-seeded-bootstrap}
mkdir -p "$OUT"
bootstrap/hs-hosted-x86_64 selfhost/be/compile.hs "$OUT/stage2"
cmp bootstrap/hs-hosted-x86_64 "$OUT/stage2"
"$OUT/stage2" selfhost/be/compile.hs "$OUT/stage3"
cmp "$OUT/stage2" "$OUT/stage3"
printf '%s\n' 'seeded compiler fixed point: seed == stage2 == stage3 (no Python)'
