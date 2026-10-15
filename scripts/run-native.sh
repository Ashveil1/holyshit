#!/bin/sh
# Run a source program through the verified native compiler. No Python/gcc.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -lt 1 ]; then
  printf '%s\n' 'usage: scripts/run-native.sh program.holy [args...]' >&2
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
WORK=$(mktemp -d "${TMPDIR:-/tmp}/holyshit-native.XXXXXXXX")
trap 'rm -rf -- "$WORK"' EXIT HUP INT TERM
"$ROOT/bootstrap/hs-hosted-x86_64" "$SOURCE" "$WORK/program"
set +e
"$WORK/program" "$@"
RESULT=$?
set -e
exit "$RESULT"
