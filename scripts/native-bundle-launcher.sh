#!/bin/sh
# Installed as BUNDLE/bin/hs. Resolve data relative to the moved bundle.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -lt 2 ]; then
  printf '%s\n' 'usage: hs run SOURCE [args...] | hs build SOURCE OUTPUT' >&2
  exit 2
fi
COMMAND=$1
shift
SOURCE=$1
shift
case "$SOURCE" in /*) ;; *) SOURCE="$(pwd)/$SOURCE" ;; esac
export HSROOT="$ROOT"
export HSPATH="$ROOT/selfhost:$ROOT/selfhost/be:$ROOT/std${HSPATH:+:$HSPATH}"
case "$COMMAND" in
  run)
    (cd "$ROOT" && sha256sum -c EAGER_SHA256SUMS >&2)
    exec "$ROOT/bin/hs-eager" "$SOURCE" "$@"
    ;;
  build)
    if [ "$#" -ne 1 ]; then
      printf '%s\n' 'usage: hs build SOURCE OUTPUT' >&2
      exit 2
    fi
    (cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
    exec "$ROOT/bootstrap/hs-hosted-x86_64" "$SOURCE" "$@"
    ;;
  *)
    printf '%s\n' "unknown command: $COMMAND" >&2
    exit 2
    ;;
esac
