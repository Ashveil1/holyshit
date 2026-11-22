#!/usr/bin/env python3
"""claimview-0b slice 2a: cv_view is read-only. The full index state dump is byte-identical
before and after every view of every parity case (including fail-closed index states and
queries that hit the work/depth limits), and a view on a never-loaded index does not
lazily initialise it."""
import os, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_claim_view_0b_holy_parity as P

ops = ['new', 'dump', 'view\ta\tis-a\tb\t0', 'dump']
marks = [('E0', 0)]
for name, n in P.all_cases():
    o = P.ops_for(name, n)
    vi = max(i for i, x in enumerate(o) if x.startswith('view\t'))
    ops += o[:vi] + ['dump', o[vi], o[vi], 'dump']
tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'drv')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'tests/claimview/cv_driver.holy'), '-o', exe], capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-800:]
out = subprocess.run([exe], input='\n'.join(ops) + '\n', capture_output=True, text=True, timeout=300).stdout
# split into dump blocks and view blocks in order
blocks, cur, kinds = [], [], []
for line in out.split('\n'):
    cur.append(line)
    if line == 'END':
        blocks.append('\n'.join(cur)); cur = []
dumps = [b for b in blocks if b.startswith('M\t') or b.startswith('###') is False and b.split('\n')[0].startswith('M\t')]
dumps = [b[b.index('M\t'):] for b in blocks if '\nM\t' in '\n' + b.split('\nR\t')[0] and 'R\t' not in b.split('\n')[0] + b.split('\n')[-2][:2] or b.startswith('M\t')]
dumps = [b for b in blocks if b.lstrip('#').split('\n')[-1] == 'END' and '\nM\t' in ('\n' + b) and '\nR\t' not in ('\n' + b)]
assert len(dumps) >= 2 and len(dumps) % 2 == 0, len(dumps)
bad = [i for i in range(0, len(dumps), 2) if dumps[i].split('M\t', 1)[1] != dumps[i + 1].split('M\t', 1)[1]]
assert not bad, bad[:5]
first = dumps[0].split('M\t', 1)[1]; second = dumps[1].split('M\t', 1)[1]
assert first == second, 'view on a never-loaded index changed it (lazy init)'
print('ok   %d state dumps before/after views identical; no lazy init on an unloaded index' % (len(dumps) // 2))
print('0 failures')
