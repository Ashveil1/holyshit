#!/usr/bin/env python3
"""claimview-0b slice 1c: agent/cvsort.holy byte-wise stable merge sort against
Python's bytes ordering (the Oracle's bkey order) on native and interp, Thai,
mixed ASCII/Thai, combining marks, Latin-1, equal-canonical ties, duplicates.
All 7 routes are covered by test_claim_view_0b_relindex_routes.py."""
import os, random, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests' / 'claimview'))
import oracle_claim_view_0b as O
fails = 0
def check(name, cond, detail=''):
    global fails
    print(('ok   ' if cond else 'FAIL ') + name + ('' if cond else ' ' + str(detail)[:500]))
    fails += 0 if cond else 1
DRV = ROOT / 'tests/claimview/relindex_driver.holy'
tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'drv')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(DRV), '-o', exe], capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-800:]
def native(lines): return subprocess.run([exe], input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=120).stdout.split('\n')
def interp(lines): return subprocess.run([sys.executable, str(ROOT / 'interp.py'), str(DRV)], input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=300).stdout.split('\n')
bk = O.bkey
STR = ['ก', 'ข', 'นก', 'นกแก้ว', 'นก ตัว', 'a', 'A', 'b', 'bird', 'Bird', 'é', 'e\u0301', 'ü', 'ๆ', 'กิ', 'ก\u0e34', 'ก\u0e38', 'z', 'ข้าว', 'ข้า', 'ก้', 'a robin', 'robin']
def exp_str(xs): return sorted(xs, key=bk)
def exp_tuple(ts): return sorted(ts, key=lambda t: (bk(t[1]), t[3], bk(O.canon(t[2])), bk(t[2]), bk(t[0])))
def exp_alias(rs): return sorted(rs, key=lambda r: (bk(O.canon(r[1])), bk(r[0]), bk(r[1])))
rng = random.Random(7)
ok_n = ok_i = True
for case in range(6):
    xs = [rng.choice(STR) for _ in range(rng.randint(0, 25))]
    ts = [(rng.choice(STR), rng.choice(['is-a', 'has', 'is-in', 'means']), rng.choice(STR), rng.random() < .4) for _ in range(rng.randint(0, 25))]
    rs = [(rng.choice(STR), rng.choice(STR)) for _ in range(rng.randint(0, 25))]
    cmd = ['new', 'sort\tstr\t' + '\t'.join(xs) if xs else 'sort\tstr',
           'sort\ttuple\t' + '\t'.join(a + '\t' + b + '\t' + c + '\t' + ('1' if n else '0') for a, b, c, n in ts) if ts else 'sort\ttuple',
           'sort\talias\t' + '\t'.join(a + '\t' + b for a, b in rs) if rs else 'sort\talias']
    want = ['ok'] + ['S\t' + x for x in exp_str(xs)] + ['ok'] + ['S\t%s\t%s\t%s\t%s' % (a, b, c, 'true' if n else 'false') for a, b, c, n in exp_tuple(ts)] + ['ok'] + \
           ['S\t%s\t%s' % r for r in exp_alias(rs)] + ['ok']
    got = native(cmd)[:len(want)]
    ok_n = ok_n and got == want
    if case < 2:
        ok_i = ok_i and interp(cmd)[:len(want)] == want
    if got != want:
        print(case, got[:8], want[:8])
check('merge sort (str, tuple, alias kinds) equals Python bytes ordering on 6 random cases incl. Thai, combining marks, Latin-1, ties (native)', ok_n)
check('same on the interp route (2 cases)', ok_i)
# stability and byte-order facts
o = native(['new', 'sort\talias\tB\tx\tb\tx\tb\ty', 'sort\tstr\tก\tข\tA\ta\tz'])
check('equal canonical target and alias spelling: original strings break ties; Thai sorts after ASCII by bytes',
      o[1:4] == ['S\tB\tx', 'S\tb\tx', 'S\tb\ty'] and o[5:10] == ['S\tA', 'S\ta', 'S\tz', 'S\tก', 'S\tข'], o)
big = ['sort\tstr\t' + '\t'.join(('k%05d' % ((i * 7919) % 5003)) for i in range(5000))]
o = native(['new'] + big)
keys = [l[2:] for l in o if l.startswith('S\t')]
check('5000 strings sorted in order (O(n log n), no insertion-sort blowup)', keys == sorted(keys) and len(keys) == 5000)
print('0 failures' if not fails else '%d FAILURES' % fails)
sys.exit(1 if fails else 0)
