#!/usr/bin/env python3
"""Check a proposed seed against source bootstrap and a second generation.
This tool does not install, download or trust an unverified external seed.
"""
import argparse
import contextlib
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from x64gen import build_x64
p = argparse.ArgumentParser()
p.add_argument('seed', type=Path)
a = p.parse_args()
seed = a.seed.resolve()
env = dict(os.environ, HSPATH=str(ROOT/'selfhost')+':'+str(ROOT/'selfhost/be'), HSROOT=str(ROOT))
with tempfile.TemporaryDirectory() as d:
    stage1 = Path(d)/'stage1'
    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = build_x64(str(ROOT/'selfhost/be/compile.hs'), str(stage1))
    finally:
        if old is None:
            os.environ.pop('HSPATH', None)
        else:
            os.environ['HSPATH'] = old
    if rc or stage1.read_bytes() != seed.read_bytes():
        raise SystemExit('Seed does not equal the source-built compiler; not executing it.')
    output = Path(d)/'stage2'
    subprocess.run([str(seed), str(ROOT/'selfhost/be/compile.hs'), str(output)], env=env, check=True, timeout=600)
    if output.read_bytes() != seed.read_bytes():
        raise SystemExit('Seed self-compilation differs.')
    print('verified', len(seed.read_bytes()), hashlib.sha256(seed.read_bytes()).hexdigest())
