#!/bin/sh
# Repeat the full hosted native compiler fixed point (no Python after stage0).
set -eu
cd "$(dirname "$0")/.."
ROOT=$(pwd)
export HSPATH="$ROOT/selfhost:$ROOT/selfhost/be"
export HSROOT="$ROOT"
OUT=${1:-/tmp/holyshit-bootstrap}
mkdir -p "$OUT"
python3 hs.py xbuild selfhost/be/compile.hs -o "$OUT/stage1"
"$OUT/stage1" selfhost/be/compile.hs "$OUT/stage2"
cmp "$OUT/stage1" "$OUT/stage2"
"$OUT/stage2" selfhost/be/compile.hs "$OUT/stage3"
cmp "$OUT/stage2" "$OUT/stage3"
printf '%s\n' 'hosted compiler fixed point: stage1 == stage2 == stage3'
