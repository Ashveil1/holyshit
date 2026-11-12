#!/usr/bin/env python3
"""The AI-coding eval suite stays green on its reference solutions.

evals/run.py scores evals/ref/<task>.holy against evals/tasks.json exactly
the way an AI-written solution is scored (default `hs run`, exact stdout).
A regression in the default run route fails here before an eval report
silently degrades.
"""
from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parent.parent

import re
r = subprocess.run([sys.executable, str(ROOT / 'evals' / 'run.py'), '--reference'],
                   capture_output=True, text=True, timeout=600,
                   env=dict(__import__('os').environ, PYTHONDONTWRITEBYTECODE='1'))
m = re.search(r'(\d+)/(\d+) passed', r.stdout)
ok = r.returncode == 0 and m is not None and m.group(1) == m.group(2) != '0'
print(('ok  ' if ok else 'FAIL'), 'evals reference suite all passed',
      '' if ok else repr((r.returncode, r.stdout[-200:], r.stderr[-200:])))
print(1 if ok else 0, 'passed,', 0 if ok else 1, 'failed')
sys.exit(0 if ok else 1)
