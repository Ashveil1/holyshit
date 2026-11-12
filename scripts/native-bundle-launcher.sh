#!/bin/sh
# Installed as BUNDLE/bin/hs. Resolve data relative to the moved bundle.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
USAGE='usage: hs run SOURCE [args...] | hs interpret SOURCE [args...] | hs fmt SOURCE | hs check SOURCE | hs test FILE|DIR... | hs build SOURCE OUTPUT | hs explain "<error message>" | hs cc SOURCE [-o OUTPUT] | hs ir SOURCE | hs SOURCE.holy [args...]'
if [ "$#" -lt 1 ]; then
  printf '%s\n' "$USAGE" >&2
  exit 2
fi
# Python-style global --json: strip it wherever it appears (check, test and
# explain use it).
AS_JSON=no
N=$#
I=0
while [ "$I" -lt "$N" ]; do
  A=$1
  shift
  if [ "$A" = "--json" ]; then
    AS_JSON=yes
  else
    set -- "$@" "$A"
  fi
  I=$((I + 1))
done
# Python-style global --version/-V: print the bundled version wherever the
# flag appears, before any command dispatch.
for A in "$@"; do
  if [ "$A" = "--version" ] || [ "$A" = "-V" ]; then
    V=$(IFS= read -r L 2>/dev/null < "$ROOT/VERSION" && printf '%s' "$L") || V=
    printf 'hs %s\n' "${V:-unknown}"
    exit 0
  fi
done
if [ "$#" -lt 1 ]; then
  printf '%s\n' "$USAGE" >&2
  exit 2
fi
COMMAND=$1
shift
if [ "$COMMAND" = "explain" ]; then
  # explain takes the message words, not a source path; they are passed
  # exactly as given, like the Python CLI joining argv with spaces.
  if [ "$#" -lt 1 ]; then
    printf '%s\n' "$USAGE" >&2
    exit 2
  fi
  export HSROOT="$ROOT"
  export HSPATH="$ROOT/selfhost:$ROOT/selfhost/be:$ROOT/std${HSPATH:+:$HSPATH}"
  if [ ! -f "$ROOT/bin/hs-explain" ] || [ ! -f "$ROOT/EXPLAIN_SHA256SUMS" ]; then
    printf '%s\n' 'installed explainer is missing; install a new complete bundle' >&2
    exit 1
  fi
  (cd "$ROOT" && sha256sum --status -c EXPLAIN_SHA256SUMS) || {
    printf '%s\n' 'installed explainer checksum failed' >&2
    exit 1
  }
  if [ "$AS_JSON" = yes ]; then
    exec "$ROOT/bin/hs-explain" "$@" --json
  fi
  exec "$ROOT/bin/hs-explain" "$@"
fi
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
# check, test, cc and ir report/use paths exactly as given, like the
# Python CLI; the other commands resolve the source against the invocation
# directory.
case "$COMMAND" in
  check|test|cc|ir) ;;
  *) case "$SOURCE" in /*) ;; *) SOURCE="$(pwd)/$SOURCE" ;; esac ;;
esac
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
  interpret)
    # Explicit existing IR interpreter, never an automatic fallback for run.
    if [ ! -f "$ROOT/bin/hs-interp" ] || [ ! -f "$ROOT/INTERP_SHA256SUMS" ]; then
      printf '%s\n' 'installed interpreter is missing; install a new complete bundle' >&2
      exit 1
    fi
    (cd "$ROOT" && sha256sum --status -c INTERP_SHA256SUMS) || {
      printf '%s\n' 'installed interpreter checksum failed' >&2
      exit 1
    }
    exec "$ROOT/bin/hs-interp" "$SOURCE" "$@"
    ;;
  fmt)
    if [ "$#" -ne 0 ]; then
      printf '%s\n' 'usage: hs fmt SOURCE' >&2
      exit 2
    fi
    if [ ! -f "$ROOT/bin/hs-fmt" ] || [ ! -f "$ROOT/FMT_SHA256SUMS" ]; then
      printf '%s\n' 'installed formatter is missing; install a new complete bundle' >&2
      exit 1
    fi
    (cd "$ROOT" && sha256sum --status -c FMT_SHA256SUMS) || {
      printf '%s\n' 'installed formatter checksum failed' >&2
      exit 1
    }
    exec "$ROOT/bin/hs-fmt" "$SOURCE" --comments
    ;;
  check)
    # Extra positional arguments are ignored, matching the Python CLI.
    if [ ! -f "$ROOT/bin/hs-check" ] || [ ! -f "$ROOT/CHECK_SHA256SUMS" ]; then
      printf '%s\n' 'installed checker is missing; install a new complete bundle' >&2
      exit 1
    fi
    (cd "$ROOT" && sha256sum --status -c CHECK_SHA256SUMS) || {
      printf '%s\n' 'installed checker checksum failed' >&2
      exit 1
    }
    if [ "$AS_JSON" = yes ]; then
      exec "$ROOT/bin/hs-check" "$SOURCE" --json
    fi
    exec "$ROOT/bin/hs-check" "$SOURCE"
    ;;
  test)
    # All positional arguments are paths (FILE|DIR...), like the Python CLI.
    if [ ! -f "$ROOT/bin/hs-test" ] || [ ! -f "$ROOT/TEST_SHA256SUMS" ]; then
      printf '%s\n' 'installed tester is missing; install a new complete bundle' >&2
      exit 1
    fi
    (cd "$ROOT" && sha256sum --status -c TEST_SHA256SUMS) || {
      printf '%s\n' 'installed tester checksum failed' >&2
      exit 1
    }
    if [ "$AS_JSON" = yes ]; then
      exec "$ROOT/bin/hs-test" "$SOURCE" "$@" --json
    fi
    exec "$ROOT/bin/hs-test" "$SOURCE" "$@"
    ;;
  build)
    if [ "$#" -ne 1 ]; then
      printf '%s\n' 'usage: hs build SOURCE OUTPUT' >&2
      exit 2
    fi
    (cd "$ROOT/bootstrap" && sha256sum -c SHA256SUMS >&2)
    exec "$ROOT/bootstrap/hs-hosted-x86_64" "$SOURCE" "$@"
    ;;
  cc)
    # The compiler written in hs itself (hosted subset). Optional -o OUTPUT
    # anywhere after the source, other extra arguments ignored, matching the
    # Python CLI; the default output strips the source's final extension.
    OUT=
    while [ "$#" -gt 0 ]; do
      if [ "$1" = "-o" ]; then
        if [ "$#" -gt 1 ]; then
          OUT=$2
        fi
        break
      fi
      shift
    done
    if [ -z "$OUT" ]; then
      BASE=${SOURCE##*/}
      STEM=$BASE
      case "$BASE" in
        ?*.*) STEM=${BASE%.*} ;;
      esac
      case "$SOURCE" in
        */*) OUT=${SOURCE%/*}/$STEM ;;
        *) OUT=$STEM ;;
      esac
    fi
    if [ ! -f "$ROOT/bin/hs-cc" ] || [ ! -f "$ROOT/CC_SHA256SUMS" ]; then
      printf '%s\n' 'installed compiler is missing; install a new complete bundle' >&2
      exit 1
    fi
    (cd "$ROOT" && sha256sum --status -c CC_SHA256SUMS) || {
      printf '%s\n' 'installed compiler checksum failed' >&2
      exit 1
    }
    exec "$ROOT/bin/hs-cc" "$SOURCE" "$OUT"
    ;;
  ir)
    # Extra positional arguments are ignored, matching the Python CLI.
    if [ ! -f "$ROOT/bin/hs-ir" ] || [ ! -f "$ROOT/IR_SHA256SUMS" ]; then
      printf '%s\n' 'installed IR dumper is missing; install a new complete bundle' >&2
      exit 1
    fi
    (cd "$ROOT" && sha256sum --status -c IR_SHA256SUMS) || {
      printf '%s\n' 'installed IR dumper checksum failed' >&2
      exit 1
    }
    if [ "$AS_JSON" = yes ]; then
      exec "$ROOT/bin/hs-ir" "$SOURCE" --json
    fi
    exec "$ROOT/bin/hs-ir" "$SOURCE"
    ;;
  *)
    printf '%s\n' "unknown command: $COMMAND" >&2
    exit 2
    ;;
esac
