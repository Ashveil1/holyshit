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
    st = {'g': int(m[1]), 'ig': int(m[2]), 'xn': int(m[3]), 'wc': int(m[4]), 'an': int(m[5]),
          'T': [], 'X': {}, 'A': [], 'AX': {}}
    for ln in d[1:]:
        f = ln.split('\t')
        if f[0] == 'T':
            st['T'].append((f[1], f[2], f[3], f[4] == 'true'))
        elif f[0] == 'X':
            st['X'].setdefault(f[1], []).append((f[2], f[3], f[4], f[5] == 'true'))
        elif f[0] == 'A':
            st['A'].append((f[1], f[2]))
        elif f[0] == 'AX':
            st['AX'].setdefault(f[1], []).append((f[2], f[3]))
    return st


class AliasModel:
    """independent alias-record model: records in order, canonical buckets."""
    def __init__(self): self.recs = []
    def add(self, a, t): self.recs.append((a, t))
    def remove(self, a, t):
        if (a, t) in self.recs:
            self.recs.remove((a, t)); return True
        return False
    def drop_target(self, t): self.recs = [r for r in self.recs if r[1] != t]
    def load(self, rs): self.recs = [tuple(r) for r in rs]


def model_equal(st, model, am=None):
    """full comparison against the Oracle model, independent of ri_check."""
    if st['T'] != [tuple(t) for t in model.authoritative()]:
        return False
    want = {}
    for t in model.authoritative():
        want.setdefault(O.canon(t[0]), []).append(tuple(t))
    got = {k: v for k, v in st['X'].items() if v}
    if not (got == want and st['xn'] == len(model.authoritative())):
        return False
    if am is not None:
        aw = {}
        for r in am.recs:
            aw.setdefault(O.canon(r[0]), []).append(r)
        ag = {k: v for k, v in st['AX'].items() if v}
        if not (st['A'] == am.recs and ag == aw and st['an'] == len(am.recs)):
            return False
    return True


def tf(*ts):
    return '\t'.join(a + '\t' + b + '\t' + c + '\t' + ('1' if n else '0') for a, b, c, n in ts)


# 1. scripted lifecycle with full comparison after every step (relations + alias records)
M = O.Store(); AM = AliasModel()
script = ['new']
steps = []
def step(cmd, fn):
    script.append(cmd); script.append('dump'); steps.append(fn)
T0 = [('a robin', 'is-a', 'a bird', False), ('robin', 'is-a', 'bird', False), ('robin', 'is-a', 'bird', False)]
step('loadall\t3\t' + tf(*T0) + '\tRobin\ta robin\tbird\trobin', lambda: (M.load(T0), AM.load([('Robin', 'a robin'), ('bird', 'robin')])))
step('add\tRobin\thas\twings\t0', lambda: M.add_tuple(('Robin', 'has', 'wings', False)))
step('add\tนก\tis-a\tสัตว์\t0', lambda: M.add_tuple(('นก', 'is-a', 'สัตว์', False)))
step('add\t  นก   ตัว \tis-a\tสัตว์\t1', lambda: M.add_tuple(('  นก   ตัว ', 'is-a', 'สัตว์', True)))
step('remove\trobin\tis-a\tbird\t0', lambda: M.remove_tuple(('robin', 'is-a', 'bird', False)))
step('aadd\tROBIN\ta robin', lambda: AM.add('ROBIN', 'a robin'))
step('aremove\tbird\trobin', lambda: AM.remove('bird', 'robin'))
step('rebuild', lambda: M.rebuild())
def _replace():
    keep = [t for t in M.authoritative() if t[0] != 'นก']
    M.load(keep + [('นก', 'has', 'ปีก', False)])
step('replace\tนก\tนก\thas\tปีก\t0', _replace)
def _forget():
    M.load([t for t in M.authoritative() if t[0] != 'a robin']); AM.drop_target('a robin')
step('forget\ta robin', _forget)
out = blocks(run_native(script))
ok = True; detail = ''
for i, fn in enumerate(steps):
    fn()
    res, d = out[1 + 2 * i], out[2 + 2 * i]
    st = parse_dump(d)
    if res != 'ok' or not model_equal(st, M, AM) or st['g'] != st['ig']:
        ok = False; detail = (i, res, st); break
check('lifecycle load_all/add/remove/alias add+remove/rebuild/replace/forget: full relation+alias index equals model after every step', ok, detail)
st = parse_dump(out[2])
check('duplicates counted individually (3 loaded, xn 3), robin vs a robin distinct keys, several alias records per canonical alias key',
      st['xn'] == 3 and set(st['X']) == {'a robin', 'robin'} and len(st['X']['robin']) == 2, st)

# 2. canonical form parity with the Oracle
samples = ['  A  Robin', 'ROBIN', 'a   bird', 'นก  ตัว', 'Ünï  X', '', '   ', 'a  b  c']
got = run_native(['canon\t' + s for s in samples]).split('\n')
check('ri_canon equals Oracle canon (ASCII lowercase, whitespace runs, non-ASCII unchanged)',
      all(got[i] == '[' + O.canon(s) + ']' for i, s in enumerate(samples)), got)

# 3. random sequences: native vs interp vs model, full compare each op, audit clean at the end
VOC = ['a robin', 'robin', 'Robin', '  ROBIN ', 'นก', 'นก  ตัว', 'bird', 'A Bird']
PRE = ['is-a', 'has', 'is-in', 'means']
def rtup(rng): return (rng.choice(VOC), rng.choice(PRE), rng.choice(VOC), rng.random() < .3)
def rnd_script(seed, n):
    rng = random.Random(seed)
    cmds, mops = ['new'], []
    for _ in range(n):
        k = rng.random(); t = rtup(rng)
        if k < .30: cmds.append('add\t' + tf(t)); mops.append(('add', t))
        elif k < .42: cmds.append('remove\t' + tf(t)); mops.append(('remove', t))
        elif k < .50: cmds.append('drop\t' + t[0]); mops.append(('drop', t[0]))
        elif k < .58:
            ts = [rtup(rng) for _ in range(rng.randint(0, 6))]
            cmds.append('load\t' + tf(*ts) if ts else 'load'); mops.append(('load', ts))
        elif k < .66:
            a, b = rng.choice(VOC), rng.choice(VOC)
            cmds.append('aadd\t%s\t%s' % (a, b)); mops.append(('aadd', (a, b)))
        elif k < .72:
            a, b = rng.choice(VOC), rng.choice(VOC)
            cmds.append('aremove\t%s\t%s' % (a, b)); mops.append(('aremove', (a, b)))
        elif k < .82:
            sub = rng.choice(VOC)
            ts = [(sub, rng.choice(PRE), rng.choice(VOC), rng.random() < .3) for _ in range(rng.randint(0, 3))]
            cmds.append('replace\t' + sub + ('\t' + tf(*ts) if ts else '')); mops.append(('replace', (sub, ts)))
        elif k < .90: cmds.append('forget\t' + t[0]); mops.append(('forget', t[0]))
        else: cmds.append('rebuild'); mops.append(('rebuild', None))
        cmds.append('dump')
        cmds.append('audit')
    return cmds, mops

allok = True
for seed in range(8):
    cmds, mops = rnd_script(seed, 60)
    on = run_native(cmds)
    oi = run_interp(cmds) if seed < 2 else None
    if oi is not None and on != oi:
        check('native and interp routes byte-identical, seed %d' % seed, False, 'differs'); allok = False; break
    o = blocks(on)
    Mo = O.Store(); Am = AliasModel()
    for i, (op, a) in enumerate(mops):
        exp = 'ok'
        auth = Mo.authoritative()
        if op == 'add': Mo.add_tuple(a)
        elif op == 'remove': exp = 'ok' if Mo.remove_tuple(a) else 'absent'
        elif op == 'drop':
            keep = [t for t in auth if t[0] != a]
            exp = 'n=%d' % (len(auth) - len(keep))
            if len(keep) != len(auth): Mo.load(keep)
        elif op == 'load': Mo.load(a)
        elif op == 'aadd': Am.add(*a)
        elif op == 'aremove': exp = 'ok' if Am.remove(*a) else 'absent'
        elif op == 'replace': Mo.load([t for t in auth if t[0] != a[0]] + list(a[1]))
        elif op == 'forget':
            Mo.load([t for t in auth if t[0] != a]); Am.drop_target(a)
        else: Mo.rebuild()
        res, st, aud = o[1 + 3 * i], parse_dump(o[2 + 3 * i]), o[3 + 3 * i]
        if res != exp or not model_equal(st, Mo, Am) or st['g'] != st['ig'] or aud != 'ok':
            allok = False
            check('random seed %d op %d %s' % (seed, i, op), False, (res, exp, aud)); break
    if not allok: break
check('8 random lifecycle sequences x 60 ops incl. alias, replace, forget: full relation+alias index equals model after every op, ri_audit clean, markers together; seeds 0-1 native == interp', allok)

# 4. fail closed
base = ['new', 'load\t' + tf(('a robin', 'is-a', 'a bird', False), ('robin', 'has', 'wings', False)), 'aadd\tRobin\ta robin']
for kind, code in (('missing', 'missing'), ('amissing', 'missing'), ('stale', 'generation'), ('count', 'count'), ('droptuple', 'count')):
    o = blocks(run_native(base + ['break\t' + kind + '\trobin', 'check', 'dump', 'add\tx\tis-a\ty\t0', 'remove\trobin\thas\twings\t0',
                                  'drop\trobin', 'aadd\tq\tr', 'aremove\tRobin\ta robin', 'replace\trobin', 'forget\trobin',
                                  'plan_replace\trobin', 'plan_forget\trobin', 'bucket\trobin', 'abucket\trobin', 'keys', 'dump', 'rebuild', 'check', 'audit']))
    # idx: new0 load1 aadd2 break3 check4 dump5 add6 remove7 drop8 aadd9 aremove10 replace11 forget12 plan_r13 plan_f14 B15 AB16 K17 dump18 rebuild19 check20 audit21
    chk, d1 = o[4], o[5]
    refusals = o[6:15]
    reads = (o[15], o[16], o[17])
    d2 = o[18]
    check('fail closed on %s: check=%s; all 9 mutations/plans refuse with that code; 3 readers return the code; state byte-identical' % (kind, code),
          chk == code and all(r == code for r in refusals) and d1 == d2 and reads[0].startswith('B\t' + code) and reads[1].startswith('AB\t' + code) and reads[2].startswith('K\t' + code), (chk, refusals, reads))
    check('  %s: only rebuild replaces the index; then check and audit are clean' % kind, o[19] == 'ok' and o[20] == 'ok' and o[21] == 'ok', o[19:22])
o = blocks(run_native(base + ['break\tmissing', 'loadall\t1\t' + tf(('z', 'is-a', 'y', False)), 'check', 'audit']))
check('load_all also replaces a broken index', o[4] == 'ok' and o[5] == 'ok' and o[6] == 'ok', o)

# Q4: same-count corruption matrix. ri_check misses these; ri_audit must catch ALL of them.
matrix = [('swap', 'robin', 'wrong tuple replacing a correct one'), ('place', 'a robin', 'tuple in the wrong bucket'),
          ('alter', 'robin', 'altered endpoint string'), ('extra', 'robin', 'extra tuple in a bucket'),
          ('awrong', 'robin', 'wrong alias record')]
for kind, key, what in matrix:
    o = blocks(run_native(base + ['break\t%s\t%s' % (kind, key), 'check', 'audit']))
    check('corruption "%s" (%s): ri_audit catches it (%s); ri_check says %s' % (kind, what, o[4 + 1], o[3 + 1]), o[5] not in ('ok', ''), o)
o = blocks(run_native(base + ['break\tswap\trobin', 'check', 'dump']))
M2 = O.Store(); M2.load([('a robin', 'is-a', 'a bird', False), ('robin', 'has', 'wings', False)])
check('known limit: a same-count wrong tuple passes ri_check but the model comparison catches it',
      o[4] == 'ok' and not model_equal(parse_dump(o[5]), M2), o[4])
o = blocks(run_native(base + ['break\temptybucket', 'check', 'audit', 'keys', 'break\tbump', 'check', 'audit']))
check('empty buckets are inert (audit ok, not a subject key); a bare generation bump with no data change is consistent by definition',
      o[4] == 'ok' and o[5] == 'ok' and o[6].startswith('K\t\t') and 'zzz' not in o[6] and o[8] == 'ok' and o[9] == 'ok', o[4:10])

# 5. failed mutation / plan phase leaves state unchanged; plan staleness
o = blocks(run_native(base + ['dump', 'loadbad\tq\tw\te', 'dump']))
check('invalid load (3-field tuple) refused, state byte-identical', o[3] == o[5] and o[4] == 'invalid', o[4])
o = blocks(run_native(base + ['dump', 'remove\tnope\tis-a\tnone\t0', 'drop\tnope', 'aremove\tx\ty', 'dump']))
check('absent remove/drop/aremove change nothing (no generation bump)', o[3] == o[7] and o[4] == 'absent' and o[5] == 'n=0' and o[6] == 'absent', o[4:7])
o = blocks(run_native(base + ['dump', 'plan_replace\trobin\tother\tis-a\tx\t0', 'dump', 'plan_forget\trobin', 'dump']))
check('plan phase writes nothing: a plan (even a bad one) leaves the whole state byte-identical',
      o[3] == o[5] == o[7] and o[4] == 'invalid' and o[6] == 'ok', o[4:7])
o = blocks(run_native(base + ['plan_replace\trobin\trobin\tis-a\tx\t0', 'add\tq\tis-a\tr\t0', 'dump', 'commit', 'dump']))
check('a plan made before another mutation is refused as stale_plan and changes nothing', o[4] == 'ok' and o[6] == 'stale_plan' and o[5] == o[7], o[4:8])
o = blocks(run_native(base + ['plan_replace\trobin\trobin\tis-a\tx\t0', 'commit', 'dump', 'check', 'audit']))
st = parse_dump(o[5])
check('commit installs tuples+index+count+markers in one generation step (replace: robin has wings -> is-a x)',
      o[4] == 'ok' and st['g'] == st['ig'] and st['g'] == 3 and ('robin', 'is-a', 'x', False) in st['T'] and ('robin', 'has', 'wings', False) not in st['T'] and o[6] == 'ok' and o[7] == 'ok', (st, o[6:]))
o = blocks(run_native(base + ['dump', 'replace\trobin\trobin\tis-a\tx\t0', 'dump']))
a0, a1 = parse_dump(o[3]), parse_dump(o[5])
check('atomic replace and forget move the generation by exactly one (no intermediate state)', a1['g'] == a0['g'] + 1, (a0['g'], a1['g']))
o = blocks(run_native(base + ['dump', 'forget\ta robin', 'dump']))
a0, a1 = parse_dump(o[3]), parse_dump(o[5])
check('forget drops relations of the key and alias records targeting it in one generation step; unrelated rows stay',
      a1['g'] == a0['g'] + 1 and a1['A'] == [] and ('robin', 'has', 'wings', False) in a1['T'] and all(t[0] != 'a robin' for t in a1['T']), a1)

# 6. readers: copies, never writes (B17)
o = blocks(run_native(base + ['dump', 'reads\trobin', 'mutcopy\trobin', 'bucket\trobin', 'count', 'dump']))
check('readers and a caller mutating a returned copy leave the whole state including the write counter unchanged',
      o[3] == o[len(o) - 1], (o[3][0], o[-1][0]))
check('ri_read returns exactly the exact-keyed tuples (a copy)', o[6] == 'B\t\t1' and o[7] == 'T\trobin\thas\twings\tfalse', o[6:8])
o = blocks(run_native(['new', 'check', 'bucket\trobin', 'abucket\trobin', 'dump']))
check('a fresh state is sound, empty buckets read empty and no key is created',
      o[1] == 'ok' and o[2] == 'B\t\t0' and o[3] == 'AB\t\t0' and parse_dump(o[4])['X'] == {}, o)
o = blocks(run_native(base + ['break\tmissing', 'reads\trobin', 'check']))
check('readers on a missing index do not initialize or repair it', o[5] == 'missing', o)
o = blocks(run_native(base + ['keys']))
check('subject keys = canonical subjects with non-empty buckets (alias-only and object-only names are not keys)', o[3] == 'K\t\ta robin|robin', o[3])

# 7. structural write-boundary gate (audited single-writer invariant, not enforcement)
# Post-approval (A24.0b approved 2026-11-23; same lane-side guard miss as the
# PR #444 kickback): the approved 0b reader modules below may import relindex
# and call exactly the pinned public functions (checked reads / whole-index
# build); they must never name a raw index key. Every other agent/*.holy must
# not reference relindex or the index keys at all. The single writer of index
# internals stays relindex.holy itself.
READERS = {'cvsort.holy': {'ri_canon'},
           'claimview.holy': {'ri_canon', 'ri_check', 'ri_read', 'ri_read_alias'},
           'cvwire.holy': {'ri_audit', 'ri_canon', 'ri_check', 'ri_load_all', 'ri_new'}}
bad = []
for f in sorted((ROOT / 'agent').glob('*.holy')):
    txt = f.read_text(encoding='utf-8')
    if f.name == 'relindex.holy':
        continue
    if f.name in READERS:
        if set(re.findall(r'agent\.relindex\.(\w+)', txt)) - READERS[f.name] or re.search(r'\[\s*"(t|x|xn|at|ax|an|g|ig|wc)"\s*\]', txt):
            bad.append(f.name + ' (unpinned relindex call or raw index key)')
        continue
    if re.search(r'\[\s*"(xn|ig|wc|an|ax|at)"\s*\]', txt) or 'relindex' in txt:
        bad.append(f.name)
cs = (ROOT / 'agent' / 'cvsort.holy').read_text(encoding='utf-8')
check('cvsort.holy uses only ri_canon from relindex and names no index key', set(re.findall(r'agent\.relindex\.(\w+)', cs)) == {'ri_canon'} and not re.search(r'\[\s*"(t|x|xn|at|ax|an|g|ig|wc)"\s*\]', cs))
for name in READERS:
    check('approved 0b reader module present: ' + name, (ROOT / 'agent' / name).is_file())
check('write-boundary gate: only relindex.holy writes index internals; approved 0b readers use pinned calls and name no raw key; no other agent/*.holy references relindex (audited invariant, not enforcement)', not bad, bad)
mod = (ROOT / 'agent' / 'relindex.holy').read_text(encoding='utf-8')
cur, writers = None, set()
for ln in mod.split('\n'):
    m = re.match(r'def (\w+)\(', ln)
    if m: cur = m.group(1)
    elif re.search(r'ri\["(t|x|xn|at|ax|an|g|ig|wc)"\](\[[^\]]+\])?\s*=[^=]', ln) or re.search(r'append\(ri\["(t|at)"\]', ln):
        writers.add(cur)
allowed = {'_ri_install', 'ri_add', 'ri_remove', 'ri_drop_subject', 'ri_alias_add', 'ri_alias_remove', 'ri_commit'}
check('inside the module only these functions write state: %s' % sorted(writers), writers <= allowed and not any(w.startswith(('ri_read', 'ri_check', 'ri_audit', 'ri_plan', 'ri_subject')) for w in writers), writers)
check('no public raw-bucket accessor exists (ri_bucket removed)', 'def ri_bucket' not in mod)

print('0 failures' if not fails else '%d FAILURES' % fails)
sys.exit(1 if fails else 0)
