#!/usr/bin/env python3
"""Copy prelude source/dependencies from the semantic reference as hs data."""
from pathlib import Path
import json
import sys
import subprocess
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
import interp
out = '# Prelude source data, generated from interp.py by scripts/mkprelude.py.\n'
out += 'PRELUDE = ' + json.dumps(interp.PRELUDE) + '\n'
out += 'USER = ' + json.dumps(interp._PRELUDE_USER) + '\n'
out += 'RANGE_STEP_SRC = ' + json.dumps(interp._RANGE_STEP_SRC) + '\n'
p = root/'selfhost/be/prelude_data.hs'
p.write_text(out)
subprocess.run([sys.executable, str(root/'hs.py'), 'fmt', str(p), '-w'], check=True)
