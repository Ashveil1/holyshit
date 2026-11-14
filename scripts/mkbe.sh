#!/bin/sh
set -e
# regenerate selfhost/be/be.holy: translate, then apply selfhost/be/patches.py
# C2.4: the translation step runs the hs port of py2hs (selfhost/py/pygen.holy
# via interp); byte-identical to the old scripts/py2hs.py pipeline (gate:
# tests/test_pygen.py), so be.holy does not change and the seed is untouched.
# C2.6: the hosted seed compiles the translator (no Python in this step) and
# the native binary runs the translate; same bytes out (gates:
# tests/test_pygen_native.py + tests/test_pygen_seed_build.py).
cd "$(dirname "$0")/.." && bootstrap/hs-hosted-x86_64 selfhost/py/pygen_run.holy /tmp/hs_pygen_native && /tmp/hs_pygen_native x64gen.py,irx64.py /tmp/all.holy x64.py && python3 - <<'PY'
import re, sys
sys.path.insert(0, "selfhost/be")
from patches import PATCHES
s = open('/tmp/all.holy').read()
s = re.sub(r'\bpy_(\w+)\(', r'pyrt.py_\1(', s)
s = "import pyrt\nimport asm\nimport gcrt\nimport elf\n\n" + s
s = re.sub(r'pyrt\.py_open\(([^,()]+)\)', r'pyrt.py_open(\1, null)', s)
# One tuple-loop scratch name is recorded in the mechanical patch list.
match = re.search(r'for (_f[0-9]+_0), label in pyrt.py_sorted\(pyrt.py_items\(self.bi_stubs\)', s)
if match:
    s = s.replace(match.group(1), '_f5833_0')
for old, new in PATCHES:
    if old not in s:
        print("PATCH MISSING:", old[:70]); sys.exit(1)
    s = s.replace(old, new)
open('selfhost/be/be.holy', 'w').write(s)
PY
python3 hs.py fmt selfhost/be/be.holy -w
# Maintained port adaptations after the mechanical translation/format pass.
patch --forward --batch --no-backup-if-mismatch --fuzz=0 -p1 < selfhost/be/postport.patch
