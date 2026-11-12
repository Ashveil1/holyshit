#!/usr/bin/env python3
"""`hs run` auto chain: a broken gcc must not stop the program.

The auto backend walks JIT -> x64 -> gcc -> (reference interpreter). A gcc
that exists but cannot build (missing libgc headers, a broken toolchain)
used to be a dead end: the build error surfaced and the program never ran,
even though the interpreter could run it. A fake gcc that always fails
stands in for that environment here. Explicit `--backend native` and
`hs build` stay strict: they asked for the native artifact itself.
"""
from pathlib import Path
import os, stat, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent

passed = failed = 0
def check(ok, label, detail=''):
    global passed, failed
    passed += int(ok); failed += int(not ok)
    print(('ok  ' if ok else 'FAIL'), label, ('' if ok else detail), flush=True)

with tempfile.TemporaryDirectory(prefix='hs auto fallback ') as temp:
    d = Path(temp)
    fakegcc = d / 'gcc'
    fakegcc.write_text('#!/bin/sh\nexit 1\n')
    fakegcc.chmod(fakegcc.stat().st_mode | stat.S_IXUSR)
    env = dict(os.environ, PATH=str(d) + os.pathsep + os.environ.get('PATH', ''),
               PYTHONDONTWRITEBYTECODE='1')
    big = d / 'big.holy'
    big.write_text('n = int(argv()[0])\nr = 1\nfor i in range(2, n + 1):\n'
                   '  r = r * i\nprint r\n')

    def run(args):
        return subprocess.run([sys.executable, str(ROOT / 'hs.py')] + args,
                              capture_output=True, text=True, timeout=120, env=env)

    r = run(['run', str(big), '20'])
    check((r.returncode, r.stdout) == (0, '2432902008176640000\n'),
          'auto falls back to the interpreter when gcc cannot build',
          repr((r.returncode, r.stdout, r.stderr[-200:])))
    check('62-bit' not in r.stderr and 'compile failed' not in r.stderr,
          'the failing native route stays silent after fallback',
          repr(r.stderr[-200:]))

    err = d / 'err.holy'
    err.write_text('print 1 / 0\n')
    r = run(['run', str(err)])
    check(r.returncode == 1 and 'division by zero' in r.stderr,
          'a program error still surfaces truthfully after fallback',
          repr((r.returncode, r.stderr[-200:])))

    r = run(['run', str(big), '--backend', 'native', '20'])
    check(r.returncode != 0 and '2432902008176640000' not in r.stdout,
          'explicit native backend does not fall back',
          repr((r.returncode, r.stdout, r.stderr[-200:])))

    out = d / 'big-bin'
    r = run(['build', str(big), '-o', str(out)])
    check(r.returncode != 0 and not out.exists(),
          'hs build stays strict under a broken gcc',
          repr((r.returncode, r.stderr[-200:])))

print(passed, 'passed,', failed, 'failed')
sys.exit(1 if failed else 0)
