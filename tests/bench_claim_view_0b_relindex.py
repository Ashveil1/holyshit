#!/usr/bin/env python3
"""Informational RAM/latency measurement for agent/relindex.holy on the native
route (claimview-0b slice 1). Not a gate: prints wall time and peak RSS of the
driver process per size. No clock builtin is used; time is measured outside."""
import os, resource, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
exe = os.path.join(tempfile.mkdtemp(), 'ridrv')
subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'tests/claimview/relindex_driver.holy'), '-o', exe],
               check=True, capture_output=True, timeout=300)

def run(lines):
    t = time.time()
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    out, _ = p.communicate('\n'.join(lines) + '\n')
    wall = time.time() - t
    return out, wall

def peak_rss_kb(lines):
    code = ("import resource,subprocess,sys;"
            "p=subprocess.run(['%s'],input=sys.stdin.read(),capture_output=True,text=True);"
            "print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)" % exe)
    p = subprocess.run([sys.executable, '-c', code], input='\n'.join(lines) + '\n', capture_output=True, text=True)
    return int(p.stdout.strip())

print('%7s %12s %14s %16s %12s' % ('tuples', 'load (s)', '+10k lookups', '+200 add/remove', 'peak RSS MB'))
for n in (1000, 10000, 50000):
    _, t0 = run(['gen\t%d\t0' % n])
    o1, t1 = run(['gen\t%d\t10000' % n])
    ops = []
    for i in range(200):
        ops += ['add\tThing %d\tis-a\textra %d\t0' % (i, i), 'remove\tThing %d\tis-a\textra %d\t0' % (i, i)]
    _, t2 = run(['gen\t%d\t0' % n] + ops)
    assert 'chk=[]' in o1, o1
    print('%7d %12.3f %14.3f %16.3f %12.1f' % (n, t0, t1 - t0, t2 - t0, peak_rss_kb(['gen\t%d\t10000' % n]) / 1024))
