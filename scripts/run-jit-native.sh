#!/bin/sh
# Experimental eager in-process execution. No Python/gcc at runtime.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -lt 1 ]; then
  printf '%s\n' 'usage: scripts/run-jit-native.sh program.holy [args...]' >&2
  exit 2
fi
SOURCE=$1
shift
case "$SOURCE" in
  /*) ;;
  *) SOURCE="$(pwd)/$SOURCE" ;;
esac
if [ ! -f "$SOURCE" ]; then
  printf '%s\n' "source not found: $SOURCE" >&2
  exit 1
fi
(cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
export HSROOT="$ROOT"
export HSPATH="$ROOT/selfhost:$ROOT/selfhost/be${HSPATH:+:$HSPATH}"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/holyshit-jit.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
"$ROOT/bootstrap/hs-hosted-x86_64" "$ROOT/selfhost/be/jit_run.holy" "$WORK/jit"
set +e
"$WORK/jit" "$SOURCE" "$@"
RESULT=$?
set -e
exit "$RESULT"
