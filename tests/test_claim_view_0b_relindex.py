#!/usr/bin/env python3
"""claimview-0b slice 1: exact-keyed relation index lifecycle (agent/relindex.holy).

Runs the module through tests/claimview/relindex_driver.holy on the native
route and the interp route, and compares every state with the independent
Oracle lifecycle model (oracle_claim_view_0b.Store) by FULL index comparison
(every bucket, every tuple, original strings). Not a claim-view test: no view
exists yet. Fault injection is in the driver, never in the module."""
import os, random, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests' / 'claimview'))
import oracle_claim_view_0b as O

fails = 0


def check(name, cond, detail=''):
    global fails
    print(('ok   ' if cond else 'FAIL ') + name + ('' if cond else ' ' + str(detail)[:600]))
    fails += 0 if cond else 1


DRV = ROOT / 'tests' / 'claimview' / 'relindex_driver.holy'
tmp = tempfile.mkdtemp()
exe = os.path.join(tmp, 'ridrv')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(DRV), '-o', exe],
                   capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-800:]


def run_native(lines):
    p = subprocess.run([exe], input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=120)
    return p.stdout


def run_interp(lines):
    p = subprocess.run([sys.executable, str(ROOT / 'interp.py'), str(DRV)], input='\n'.join(lines) + '\n',
                       capture_output=True, text=True, timeout=300)
    return p.stdout


def blocks(out):
    """split driver output into per-command results; a dump becomes a dict."""
    res, cur = [], None
    for ln in out.split('\n'):
        if cur is not None:
            if ln == 'END':
                res.append(cur); cur = None
            else:
                cur.append(ln)
        elif ln.startswith('M\t'):
            cur = [ln]
        elif ln:
            res.append(ln)
    return res


def parse_dump(d):
    m = d[0].split('\t')
    st = {'g': int(m[1]), 'ig': int(m[2]), 'xn': int(m[3]), 'wc': int(m[4]), 'T': [], 'X': {}}
    for ln in d[1:]:
        f = ln.split('\t')
        t = (f[-4], f[-3], f[-2], f[-1] == 'true') if f[0] == 'T' else None
        if f[0] == 'T':
            st['T'].append((f[1], f[2], f[3], f[4] == 'true'))
        elif f[0] == 'X':
            st['X'].setdefault(f[1], []).append((f[2], f[3], f[4], f[5] == 'true'))
    return st


def model_equal(st, model):
    """full comparison against the Oracle model, independent of ri_check."""
    if st['T'] != [tuple(t) for t in model.authoritative()]:
        return False
    want = {}
    for t in model.authoritative():
        want.setdefault(O.canon(t[0]), []).append(tuple(t))
    got = {k: v for k, v in st['X'].items() if v}
    return got == want and st['xn'] == len(model.authoritative())


def tf(*ts):
    return '\t'.join(a + '\t' + b + '\t' + c + '\t' + ('1' if n else '0') for a, b, c, n in ts)


# 1. scripted lifecycle with full comparison after every step
M = O.Store()
script = ['new']
steps = []
def step(cmd, fn):
    script.append(cmd); script.append('dump'); steps.append(fn)
step('load\t' + tf(('a robin', 'is-a', 'a bird', False), ('robin', 'is-a', 'bird', False), ('robin', 'is-a', 'bird', False)),
     lambda: M.load([('a robin', 'is-a', 'a bird', False), ('robin', 'is-a', 'bird', False), ('robin', 'is-a', 'bird', False)]))
step('add\tRobin\thas\twings\t0', lambda: M.add_tuple(('Robin', 'has', 'wings', False)))
step('add\tนก\tis-a\tสัตว์\t0', lambda: M.add_tuple(('นก', 'is-a', 'สัตว์', False)))
step('add\t  นก   ตัว \tis-a\tสัตว์\t1', lambda: M.add_tuple(('  นก   ตัว ', 'is-a', 'สัตว์', True)))
step('remove\trobin\tis-a\tbird\t0', lambda: M.remove_tuple(('robin', 'is-a', 'bird', False)))
step('rebuild', lambda: M.rebuild())
out = blocks(run_native(script))
ok = True
detail = ''
di = 1  # out[0] is 'ok' for new
for i, fn in enumerate(steps):
    fn()
    res, d = out[1 + 2 * i], out[2 + 2 * i]
    st = parse_dump(d)
    if res != 'ok' or not model_equal(st, M) or st['g'] != st['ig']:
        ok = False; detail = (i, res, st)
        break
check('lifecycle load/add/remove/rebuild: full index equals Oracle model after every step (duplicates individually, non-ASCII, case, spacing)', ok, detail)
st = parse_dump(out[2 + 2 * 0])
check('duplicates are counted individually (3 loaded, xn 3) and robin vs a robin are distinct keys',
      st['xn'] == 3 and set(st['X']) == {'a robin', 'robin'} and len(st['X']['robin']) == 2, st)

# 2. canonical form parity with the Oracle
samples = ['  A  Robin', 'ROBIN', 'a   bird', 'นก  ตัว', 'Ünï  X', '', '   ', 'a  b  c']
got = run_native(['canon\t' + s for s in samples]).split('\n')
check('ri_canon equals Oracle canon (ASCII lowercase, whitespace runs, non-ASCII unchanged)',
      all(got[i] == '[' + O.canon(s) + ']' for i, s in enumerate(samples)), got)

# 3. random sequences: native vs interp vs Oracle model, full compare each op
VOC = ['a robin', 'robin', 'Robin', '  ROBIN ', 'นก', 'นก  ตัว', 'bird', 'A Bird']
PRE = ['is-a', 'has', 'is-in', 'means']
def rnd_script(seed, n):
    rng = random.Random(seed)
    cmds, model_ops = ['new'], []
    for _ in range(n):
        k = rng.random()
        t = (rng.choice(VOC), rng.choice(PRE), rng.choice(VOC), rng.random() < .3)
        if k < .45:
            cmds.append('add\t' + tf(t)); model_ops.append(('add', t))
        elif k < .65:
            cmds.append('remove\t' + tf(t)); model_ops.append(('remove', t))
        elif k < .75:
            cmds.append('drop\t' + t[0]); model_ops.append(('drop', t[0]))
        elif k < .85:
            ts = [(rng.choice(VOC), rng.choice(PRE), rng.choice(VOC), rng.random() < .3) for _ in range(rng.randint(0, 6))]
            cmds.append('load\t' + tf(*ts) if ts else 'load'); model_ops.append(('load', ts))
        else:
            cmds.append('rebuild'); model_ops.append(('rebuild', None))
        cmds.append('dump')
    return cmds, model_ops

allok = True
for seed in range(8):
    cmds, mops = rnd_script(seed, 60)
    on, oi = run_native(cmds), run_interp(cmds) if seed < 2 else None
    if oi is not None and on != oi:
        check('native and interp routes byte-identical, seed %d' % seed, False, 'differs')
        allok = False
        break
    o = blocks(on)
    Mo = O.Store()
    for i, (op, a) in enumerate(mops):
        exp = 'ok'
        if op == 'add': Mo.add_tuple(a)
        elif op == 'remove': exp = 'ok' if Mo.remove_tuple(a) else 'absent'
        elif op == 'drop':
            n0 = len(Mo.authoritative())
            keep = [t for t in Mo.authoritative() if t[0] != a]
            exp = 'n=%d' % (n0 - len(keep)); Mo.load(keep) if n0 != len(keep) else None
        elif op == 'load': Mo.load(a)
        else: Mo.rebuild()
        res, st = o[1 + 2 * i], parse_dump(o[2 + 2 * i])
        if res != exp or not model_equal(st, Mo) or st['g'] != st['ig']:
            allok = False
            check('random seed %d op %d %s' % (seed, i, op), False, (res, exp))
            break
    if not allok: break
check('8 random lifecycle sequences x 60 ops: full index equals Oracle after every op, markers move together; seeds 0-1 native == interp', allok)

# 4. fail closed
base = ['new', 'load\t' + tf(('a robin', 'is-a', 'a bird', False), ('robin', 'has', 'wings', False))]
for kind, code in (('missing', 'missing'), ('stale', 'generation'), ('count', 'count'), ('droptuple', 'count')):
    o = blocks(run_native(base + ['break\t' + kind, 'check', 'dump', 'add\tx\tis-a\ty\t0', 'remove\trobin\thas\twings\t0',
                                  'drop\trobin', 'dump', 'rebuild', 'check']))
    # o: ok ok ok code dump c1 c2 c3 dump ok ok
    chk, d1, a, rm, dr, d2, rb, ck = o[3], o[4], o[5], o[6], o[7], o[8], o[9], o[10]
    check('fail closed on %s: check=%s, add/remove/drop refuse with the same code and change nothing' % (kind, code),
          chk == code and a == code and rm == code and dr == code and d1 == d2, (chk, a, rm, dr))
    check('  %s: only ri_rebuild replaces the index and then check is clean' % kind, rb == 'ok' and ck == 'ok', (rb, ck))
o = blocks(run_native(base + ['break\tmissing', 'load\t' + tf(('z', 'is-a', 'y', False)), 'check']))
check('load also replaces a broken index', o[3] == 'ok' and o[4] == 'ok', o)

# known limit stays honest: same-count wrong tuple evades ri_check but not the full comparison
o = blocks(run_native(base + ['break\tswap\trobin', 'check', 'dump']))
M2 = O.Store(); M2.load([('a robin', 'is-a', 'a bird', False), ('robin', 'has', 'wings', False)])
check('known limit: a same-count wrong tuple passes ri_check but the full comparison catches it',
      o[3] == 'ok' and not model_equal(parse_dump(o[4]), M2), o[3])

# 5. failed mutation leaves state unchanged
o = blocks(run_native(base + ['dump', 'loadbad\tq\tw\te', 'dump']))
check('invalid load (3-field tuple) is refused and state is byte-identical',
      o[2] == o[4] and o[3] == 'invalid', o[3])
o = blocks(run_native(base + ['dump', 'remove\tnope\tis-a\tnone\t0', 'drop\tnope', 'dump']))
check('absent remove/drop change nothing (no generation bump)', o[2] == o[5] and o[3] == 'absent' and o[4] == 'n=0', o[3:5])

# 6. readers never write (B17)
o = blocks(run_native(base + ['dump', 'reads\trobin', 'bucket\trobin', 'count', 'dump']))
check('readers (check, count, bucket) leave the whole state including the write counter unchanged',
      o[2] == o[7], (o[2][0], o[7][0]))
check('bucket returns exactly the exact-keyed tuples', o[4] == 'B\t1' and o[5] == 'T\trobin\thas\twings\tfalse', o[4:6])
o = blocks(run_native(['new', 'check', 'bucket\trobin', 'dump']))
check('a fresh state is sound and empty buckets read empty without creating keys',
      o[1] == 'ok' and o[2] == 'B\t0' and parse_dump(o[3])['X'] == {}, o)
o = blocks(run_native(base + ['break\tmissing', 'reads\trobin', 'check']))
check('a reader on a missing index does not initialize or repair it', o[4] == 'missing', o)

# 7. structural write-boundary gate (source-level, not language-level)
bad = []
for f in sorted((ROOT / 'agent').glob('*.holy')):
    if f.name == 'relindex.holy':
        continue
    txt = f.read_text(encoding='utf-8')
    if re.search(r'\[\s*"(xn|ig|wc)"\s*\]', txt) or 'relindex' in txt:
        bad.append(f.name)
check('write-boundary gate: no other agent/*.holy names the index keys or imports relindex (source-level gate only)', not bad, bad)
mod = (ROOT / 'agent' / 'relindex.holy').read_text(encoding='utf-8')
wr = re.findall(r'^(def [a-z_0-9]+)\(|ri\["(?:t|x|xn|g|ig|wc)"\]\s*=|\]\s*=', mod, re.M)
funcs, cur, writers = [], None, set()
for ln in mod.split('\n'):
    m = re.match(r'def (\w+)\(', ln)
    if m: cur = m.group(1)
    elif re.search(r'ri\["(t|x|xn|g|ig|wc)"\](\[[^\]]+\])?\s*=[^=]', ln) or re.search(r'append\(ri\["t"\]', ln):
        writers.add(cur)
check('inside the module only the mutation functions write state: %s' % sorted(writers),
      writers <= {'_ri_commit', 'ri_add', 'ri_remove', 'ri_drop_subject'} and 'ri_check' not in writers and 'ri_bucket' not in writers, writers)

print('0 failures' if not fails else '%d FAILURES' % fails)
sys.exit(1 if fails else 0)
