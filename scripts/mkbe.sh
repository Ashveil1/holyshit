#!/bin/sh
# regenerate selfhost/be/be.hs: translate, then apply selfhost/be/patches.py
cd "$(dirname "$0")/.." && python3 scripts/py2hs.py x64gen.py,irx64.py /tmp/all.hs && python3 - <<'PY'
import re, sys
sys.path.insert(0, "selfhost/be")
from patches import PATCHES
s = open('/tmp/all.hs').read()
s = re.sub(r'\bpy_(\w+)\(', r'pyrt.py_\1(', s)
s = "import pyrt\nimport asm\nimport gcrt\nimport elf\n\n" + s
for old, new in PATCHES:
    if old not in s:
        print("PATCH MISSING:", old[:70]); sys.exit(1)
    s = s.replace(old, new)
open('selfhost/be/be.hs', 'w').write(s)
PY
