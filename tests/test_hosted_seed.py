#!/usr/bin/env python3
"""Pinned native seed equals source and repeats the native fixed point."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory() as d:
    subprocess.run([sys.executable,str(ROOT/'scripts/verify-hosted-seed.py'),str(ROOT/'bootstrap/hs-hosted-x86_64')],check=True,timeout=600)
    subprocess.run(['sh',str(ROOT/'scripts/bootstrap-seed.sh'),d],check=True,timeout=1200)
print('2/2 hosted seed audit and Python-free bootstrap gates')
