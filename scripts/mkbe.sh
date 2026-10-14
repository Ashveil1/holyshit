#!/bin/sh
# regenerate the raw translation (first pass only; the maintained source is
# selfhost/be/be.hs once hand-fixed)
cd "$(dirname "$0")/.." && python3 scripts/py2hs.py x64gen.py,irx64.py /tmp/all.hs && python3 - <<'PY'
import re
s=open('/tmp/all.hs').read()
s=re.sub(r'\bpy_(\w+)\(',r'pyrt.py_\1(',s)
open('selfhost/be/be.hs','w').write("import pyrt\nimport asm\n\n"+s)
PY
python3 hs.py check selfhost/be/be.hs
