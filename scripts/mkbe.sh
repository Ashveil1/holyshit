#!/bin/sh
set -e
# regenerate selfhost/be/be.holy: translate, patch, format.
# C2.4: the translation step runs the hs port of py2hs (selfhost/py/pygen.holy
# via interp); byte-identical to the old scripts/py2hs.py pipeline (gate:
# tests/test_pygen.py), so be.holy does not change.
# C2.6: the hosted seed compiles the translator (no Python in this step) and
# the native binary runs the translate; same bytes out (gates:
# tests/test_pygen_native.py + tests/test_pygen_seed_build.py).
# C2.7: the patch and format steps move onto the seed too; the whole pipeline
# is Python-free. selfhost/be/bepatch.holy carries the patch data formerly in
# selfhost/be/patches.py; fmt runs the native build of selfhost/fmt.holy with
# --comments (byte-identical to hs.py fmt -w). The seed itself is pinned by
# bootstrap/SHA256SUMS and regenerated when compiler sources change (gate:
# scripts/verify-hosted-seed.py).
cd "$(dirname "$0")/.."
TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT
bootstrap/hs-hosted-x86_64 selfhost/py/pygen_run.holy "$TMPD/hs_pygen_native" && "$TMPD/hs_pygen_native" x64gen.py,irx64.py "$TMPD/all.holy" x64.py && bootstrap/hs-hosted-x86_64 selfhost/be/bepatch.holy "$TMPD/hs_bepatch" && "$TMPD/hs_bepatch" "$TMPD/all.holy" selfhost/be/be.holy && bootstrap/hs-hosted-x86_64 selfhost/fmt.holy "$TMPD/hs_fmt" && "$TMPD/hs_fmt" selfhost/be/be.holy --comments > "$TMPD/be_fmt.holy" && mv "$TMPD/be_fmt.holy" selfhost/be/be.holy
# Maintained port adaptations after the mechanical translation/format pass.
patch --forward --batch --no-backup-if-mismatch --fuzz=0 -p1 < selfhost/be/postport.patch
