#!/usr/bin/env python3
"""claimview-0b slice 2a bench: cv_view latency and peak RSS over a loaded index (dev box, NOT 4 GB hardware,
no resource-fit claim). Load time is reported separately from view time."""
import os, random, resource, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'drv')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'tests/claimview/cv_driver.holy'), '-o', exe], capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-500:]
def run(n, nv):
    rng = random.Random(n); names = ['n%d' % i for i in range(max(10, n // 3))]
    fl = []
    for _ in range(n):
        p = rng.choice(['is-a', 'has', 'is-in'])
        fl += [rng.choice(names), p, rng.choice(names), '1' if p != 'is-in' and rng.random() < .1 else '0']
    base = 'new\nloadall\t%d\t%s\n' % (n, '\t'.join(fl))
    views = ''.join('view\t%s\t%s\t%s\t0\n' % (rng.choice(names), rng.choice(['is-a', 'has', 'is-in']), rng.choice(names)) for _ in range(nv))
    out = {}
    for label, text in (('load', base), ('load+views', base + views)):
        code = 'import resource,subprocess,sys;subprocess.run([%r],stdin=open(%r),stdout=subprocess.DEVNULL);print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)' % (exe, tmp + '/in.txt')
        open(tmp + '/in.txt', 'w').write(text)
        t = time.time(); p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=600)
        out[label] = (time.time() - t, int(p.stdout.strip()) / 1024)
    return out
for n in (1000, 10000, 50000):
    o = run(n, 2000)
    print('n=%-6d load %.2fs; 2000 views %.2fs (%.2f ms/view); peak RSS %.0f MB' % (n, o['load'][0], o['load+views'][0] - o['load'][0], (o['load+views'][0] - o['load'][0]) / 2000 * 1000, o['load+views'][1]))
