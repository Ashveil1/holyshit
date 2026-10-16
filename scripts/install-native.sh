#!/bin/sh
# Install a self-contained native toolchain into a new explicit directory.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'usage: sh scripts/install-native.sh NEW_INSTALL_DIRECTORY' >&2
  exit 2
fi
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) ;;
  *) printf '%s\n' 'Native install requires Linux x86-64; use the development tools on other hosts.' >&2; exit 1 ;;
esac
# Builder checks the audited seed and stages publication. Never overwrite,
# remove, edit shell profiles, change PATH, use sudo or create global links.
exec /bin/sh "$ROOT/scripts/build-native-bundle.sh" "$1"
