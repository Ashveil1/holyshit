#!/bin/sh
set -e
# regenerate selfhost/be/be.hs: translate, then apply selfhost/be/patches.py
cd "$(dirname "$0")/.." && python3 scripts/py2hs.py x64gen.py,irx64.py /tmp/all.hs && python3 - <<'PY'
import re, sys
sys.path.insert(0, "selfhost/be")
from patches import PATCHES
s = open('/tmp/all.hs').read()
s = re.sub(r'\bpy_(\w+)\(', r'pyrt.py_\1(', s)
s = "import pyrt\nimport asm\nimport gcrt\nimport elf\n\n" + s
s = re.sub(r'_f[0-9]+_0', '_f5833_0', s) if False else s
s = re.sub(r'pyrt\.py_open\(([^,()]+)\)', r'pyrt.py_open(\1, null)', s)
# One tuple-loop scratch name is recorded in the mechanical patch list.
match = re.search(r'for (_f[0-9]+_0), label in pyrt.py_sorted\(pyrt.py_items\(self.bi_stubs\)', s)
if match:
    s = s.replace(match.group(1), '_f5833_0')
for old, new in PATCHES:
    if old not in s:
        print("PATCH MISSING:", old[:70]); sys.exit(1)
    s = s.replace(old, new)
open('selfhost/be/be.hs', 'w').write(s)
PY
python3 hs.py fmt selfhost/be/be.hs -w
# Maintained port adaptations after the mechanical translation/format pass.
patch --forward --batch --no-backup-if-mismatch --fuzz=0 -p1 < selfhost/be/postport.patch
