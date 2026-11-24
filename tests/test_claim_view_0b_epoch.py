#!/usr/bin/env python3
"""claimview-0b slice 2 step 1: cvgen is an invalidation epoch for the claim-view read-set.
Checks, per command, through the real core respond(): (1) SOUNDNESS: if an independent snapshot
of (rels, aliases, order) changed, cvgen advanced; (2) NO-OP: known no-op commands (repeat
teach, repeat means, reads, unknown forget) leave cvgen unchanged; (3) cvgen moves with an unchanged final snapshot only for teach/overwrite commands (drop+re-add inside one call: mutate-and-revert
within a call advances, by design: an invalidation epoch, not a net-change count);
(4) mutate-then-revert advances twice although the final read-set is identical; (5) cvgen never
decreases; (6) cvinst stays 0 (unassigned) in core; cvgen/cvinst are not in the saved file shape.
Assumption stated: sequential REPL, no view runs mid-call. Random sequences use a small vocabulary."""
import os, random, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
V = ['robin', 'a bird', 'bird', 'นก', 'wings', 'paris', 'france', 'tweety', 'a canary']
def gen(rng, n):
    out = []
    for _ in range(n):
        k = rng.random(); a, b = rng.choice(V), rng.choice(V)
        out.append(rng.choice([
            'remember %s is %s' % (a, b), '%s means %s' % (a, b), 'forget %s' % a, 'what is %s' % a,
            'remember %s has %s' % (a, b), 'remember %s is in %s' % (a, b), 'no, %s is not %s' % (a, b),
            'list', 'remember %s is also %s' % (a, b), 'remember %s is a %s' % (a, b), '%s means %s' % (a, b), 'what does %s mean' % a]))
    return out
fixed = ['remember robin is a bird', 'remember robin is a bird', 'remember robin has wings', 'remember robin has wings', 'bird means animal', 'bird means animal',
         'robin means a bird', 'robin means a bird', 'what is robin', 'list', 'forget zzz', 'remember robin is a canary', 'forget robin', 'forget robin',
         'remember robin is a bird', 'forget robin', 'remember robin is a bird']
lines = fixed + gen(random.Random(7), 400) + ['remember นก is a animal', 'remember นก is a animal', 'forget นก']
tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'e')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'tests/claimview/epoch_driver.holy'), '-o', exe], capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-800:]
out = subprocess.run([exe], input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=300).stdout.strip().split('\n')
rows = [l.split('\t') for l in out if l.startswith('E\t')]
assert len(rows) == len(lines), (len(rows), len(lines))
bad = []
moved = changed = spur = 0
for (_, ch, d, inst, line) in rows:
    ch, d = int(ch), int(d)
    if d < 0: bad.append(('decrease', line))
    if ch and d < 1: bad.append(('unsound: read-set changed, cvgen did not move', line))
    if not ch and d and not line.startswith(('remember', 'no,')): bad.append(('bump on a non-teach command with unchanged read-set', line))
    spur += (not ch and d > 0)
    if inst != '0': bad.append(('cvinst assigned in core', line))
    moved += d > 0; changed += ch
by = {i: rows[i] for i in range(len(fixed))}
for i in (1, 3, 5, 7, 8, 9, 10, 13):
    if int(by[i][2]) != 0 or int(by[i][1]) != 0: bad.append(('no-op moved cvgen', by[i][4]))
for i in (0, 2, 4, 6, 11, 12):
    if int(by[i][2]) < 1: bad.append(('real change did not move cvgen', by[i][4]))
# mutate then revert: add robin, forget robin, add robin (identical snapshot at 14 vs 12 before forget? advances each time)
assert int(by[14][2]) >= 1 and int(by[15][2]) >= 1 and int(by[16][2]) >= 1
assert not bad, bad[:5]
print('ok   %d commands: cvgen sound (%d read-set changes all advanced), %d teach calls advanced with an identical final snapshot (mutate/revert), %d bumped commands, no-ops unchanged, mutate/revert advances each step' % (len(rows), changed, spur, moved))
sav = (ROOT / 'agent/store.holy').read_text()
assert 'cvgen' not in sav and 'cvinst' not in sav
print('ok   cvgen/cvinst never saved (store.holy does not reference them)')
print('0 failures')
