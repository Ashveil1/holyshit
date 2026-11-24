#!/usr/bin/env python3
"""claimview-0b slice 2 bench: cv_rebuild and cv_query on a core state with n synthetic relations
(through the real core writer), peak RSS and time, under address-space caps. This is a DEV-CPU
SIMULATION of a memory budget (ulimit -v), NOT a measurement on 4 GB hardware, and no resource-fit
claim. Cap failure behavior is reported as observed."""
import os, random, resource, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'w')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'tests/claimview/cvwire_driver.holy'), '-o', exe], capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-500:]
def go(n, cap_mb, label):
    rng = random.Random(n); m = n // 3 + 10
    ops = ['new', 'bulk\t%d' % n, 'rebuild', 'status'] + ['query\tn%d\t%s\tn%d\t0' % (rng.randrange(m), rng.choice(['is-a', 'has', 'is-in']), rng.randrange(m)) for _ in range(300)]
    inp = Path(tmp) / 'in.txt'; inp.write_text('\n'.join(ops) + '\n')
    code = ('import resource,subprocess,sys,time\n'
            'cap=%d\nif cap: resource.setrlimit(resource.RLIMIT_AS,(cap<<20,cap<<20))\n'
            't=time.time();p=subprocess.run([%r],stdin=open(%r),capture_output=True,text=True)\n'
            'o=p.stdout.split("\\n");b=[l for l in o if l.startswith(("B\\t","T\\t"))]\n'
            'print(round(time.time()-t,2),resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss//1024,p.returncode,b[:2],(p.stderr or "")[-80:].strip())') % (cap_mb, exe, str(inp))
    p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=900)
    print('n=%-6d cap=%-5s %s -> %s' % (n, str(cap_mb) + 'MB' if cap_mb else 'none', label, p.stdout.strip() or p.stderr[-200:]))
for n in (1000, 5000, 10000):
    go(n, 0, 'time(s) peakRSS(MB) rc [rebuild, status]')
for cap in (4096, 128, 48, 24):
    go(10000, cap, 'time(s) peakRSS(MB) rc [rebuild, status]')
