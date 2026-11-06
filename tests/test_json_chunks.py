#!/usr/bin/env python3
"""Byte-stable JSON encoding boundaries on the shared runtime backends."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import x64gen
source = ROOT / 'tests/fixtures/json_chunks.holy'
want = source.with_suffix('.expected').read_bytes()
with tempfile.TemporaryDirectory() as tmp:
    commands = [[sys.executable, str(ROOT / 'interp.py'), str(source)]]
    for name, build in [('ir', x64gen.build_x64), ('ast', x64gen.build_x64_ast)]:
        exe = str(Path(tmp) / name)
        with contextlib.redirect_stdout(io.StringIO()):
            assert build(str(source), exe) == 0
        commands.append([exe])
    for command in commands:
        r = subprocess.run(command, capture_output=True, timeout=60)
        assert (r.returncode, r.stdout, r.stderr) == (0, want, b''), (command, r.returncode, r.stdout, r.stderr)
print('3/3 JSON byte-identical encoding boundaries (interp, IR, AST)')
