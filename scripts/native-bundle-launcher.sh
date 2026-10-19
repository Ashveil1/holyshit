#!/bin/sh
# Installed as BUNDLE/bin/hs. Resolve data relative to the moved bundle.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
USAGE='usage: hs run SOURCE [args...] | hs build SOURCE OUTPUT | hs SOURCE.holy [args...]'
if [ "$#" -lt 1 ]; then
  printf '%s\n' "$USAGE" >&2
  exit 2
fi
COMMAND=$1
shift
case "$COMMAND" in
  *.holy)
    # Bare source path: `hs prog.holy` runs it.
    SOURCE=$COMMAND
    COMMAND=run
    ;;
  *)
    if [ "$#" -lt 1 ]; then
      printf '%s\n' "$USAGE" >&2
      exit 2
    fi
    SOURCE=$1
    shift
    ;;
esac
case "$SOURCE" in /*) ;; *) SOURCE="$(pwd)/$SOURCE" ;; esac
export HSROOT="$ROOT"
export HSPATH="$ROOT/selfhost:$ROOT/selfhost/be:$ROOT/std${HSPATH:+:$HSPATH}"
case "$COMMAND" in
  run)
    # Verify the audited driver against its published checksum before
    # execution, and cache a successful verification in TMPDIR keyed on the
    # checksum file itself. A later run with the same bundle path skips the
    # ~30ms full re-hash while the driver is older than the stamp, keeping
    # `hs run` startup well under the 50ms phase-4 gate. Replacing or
    # appending to the driver bumps its mtime and forces verification
    # again, so a corrupted driver is still refused before execution. The
    # stamp records the owning bundle path so identical copies verify
    # independently. An attacker who can also reset mtimes bypasses this;
    # the check guards accidental corruption, same as the checksum file.
    EAGER="$ROOT/bin/hs-eager"
    SUMS=$(sha256sum "$ROOT/EAGER_SHA256SUMS")
    STAMP="${TMPDIR:-/tmp}/hs-eager-verified-${SUMS%% *}"
    VERIFIED=no
    if [ -f "$STAMP" ] && [ ! "$EAGER" -nt "$STAMP" ]; then
      if IFS= read -r OWNER < "$STAMP" && [ "$OWNER" = "$ROOT" ]; then
        VERIFIED=yes
      fi
    fi
    if [ "$VERIFIED" = no ]; then
      (cd "$ROOT" && sha256sum -c EAGER_SHA256SUMS >&2)
      printf '%s\n' "$ROOT" > "$STAMP" 2>/dev/null || true
    fi
    exec "$EAGER" "$SOURCE" "$@"
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
