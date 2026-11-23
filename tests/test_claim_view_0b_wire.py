#!/usr/bin/env python3
"""claimview-0b slice 2: agent/cvwire.holy over REAL core states (NOT activated, no respond() integration).
Checks: (1) parity of cv_query through core respond()-built states with the independent Oracle fed the same
authoritative (rels, aliases, order), full-result compare, over random sequences and fixed cases; (2) status/stale
after every mutating command and valid after non-mutating ones; (3) fail-closed rebuild at every stage (unavailable
first, core unchanged, ABORT with no evidence, a later clean rebuild restores); (4) token race at publish and mid-query;
(5) identity: a new identical-content state with the same cvgen is stale for the old holder; ABA; load; corrupted file;
saved file carries no cv fields; (6) simulated writer interruption (invalidate-only, invalidate+partial drop) makes the
holder stale. Disk-loaded duplicate tuples keep physical occurrences (W accounting vs the Oracle on the duplicates).
Limits stated: fault injection inside core writers is not available, (6) simulates the interrupted states; parity with an
Oracle written from the same contract is not proof of correctness."""
import json, os, random, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests')); sys.path.insert(0, str(ROOT / 'tests' / 'claimview'))
import test_claim_view_0b_holy_parity as P
import oracle_claim_view_0b as O

tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'cvw')
r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(ROOT / 'tests/claimview/cvwire_driver.holy'), '-o', exe], capture_output=True, text=True, timeout=300)
assert r.returncode == 0, r.stderr[-800:]
def run(ops):
    return subprocess.run([exe], input='\n'.join(ops) + '\n', capture_output=True, text=True, timeout=300).stdout
def blocks(out):
    res, cur = [], []
    for l in out.split('\n'):
        if not l: continue
        if l.startswith(('B\t', 'T\t', 'D\t', 'BI\t')): res.append(l); continue
        cur.append(l)
        if l == 'END': res.append('\n'.join(cur) + '\n'); cur = []
    return res
def parse_dump(l):
    body = l[2:]
    rp, rest = body.split('|A', 1)
    ap, op = rest.split('|O', 1)
    rels = [tuple(x.split('>', 2)) for x in rp[2:].split('|') if x] if rp.startswith('R|') else []
    als = [tuple(x.split('>', 1)) for x in ap.split('|') if x]
    order = [x for x in op.split('|') if x]
    return rels, als, order
def oracle_for(dump, q):
    rels, als, order = dump
    edges, ex = [], 0
    for s, p, o in rels:
        if p in ('is-a', 'has', 'is-in', 'means'): edges.append((s, p, o, False))
        elif p == 'not-is-a': edges.append((s, 'is-a', o, True))
        else: ex += 1
    n = {'edges': edges, 'recs': als, 'facts': order, 'builtins': list(O.BUILTINS_DECL), 'query': q, 'index_state': None,
         'readings': None, 'readings_store': None, 'poison': False}
    return P.oracle_text(n).replace('\trstage=0', '')
def qop(q): return 'query\t%s\t%s\t%s\t%s' % (q[0], q[1], q[2], '1' if q[3] else '0')
fails = []
def check(c, msg):
    if not c: fails.append(msg)

V = ['robin', 'a bird', 'bird', 'นก', 'wings', 'paris', 'france', 'a canary', 'tweety']
PR = ['is-a', 'has', 'is-in', 'means']
def gen_say(rng):
    a, b = rng.choice(V), rng.choice(V)
    return rng.choice(['remember %s is %s' % (a, b), '%s means %s' % (a, b), 'forget %s' % a, 'what is %s' % a, 'remember %s has %s' % (a, b),
                       'remember %s is in %s' % (a, b), 'no, %s is not %s' % (a, b), 'remember %s is a %s' % (a, b), 'list'])
def queries(rng, k):
    out = []
    for _ in range(k):
        p = rng.choice(PR)
        out.append((rng.choice(V), p, rng.choice(V), p in ('is-a', 'has') and rng.random() < .3))
    return out

# (1)+(2) random sequences
nq = 0
import re, collections
MIX = collections.Counter()
CH = ['c%d' % i for i in range(11)] + ['นก%d' % i for i in range(3)]
for seed in range(60):
    rng = random.Random(900 + seed)
    ops = ['new']; plan = []
    if seed < 40:
        for _ in range(rng.randint(3, 14)): ops.append('say\t' + gen_say(rng))
    else:
        L = rng.randint(3, 10)
        for i in range(L): ops.append('say\tremember %s is a %s' % (CH[i], CH[i + 1]))
        ops.append('say\tremember %s has %s' % (CH[L], 'wings'))
        if seed % 3 == 0: ops.append('say\tno, %s is not %s' % (CH[rng.randint(0, L)], CH[L]))
        if seed % 4 == 0: ops.append('say\t%s means %s' % (CH[0], CH[2]))
        if seed % 5 == 0: ops.append('say\tremember %s is a %s' % (CH[L], CH[0]))
        V = CH + ['wings']
    ops += ['rebuild', 'dump']
    d0 = parse_dump(blocks(run(ops))[1])
    names = sorted({x for r_ in d0[0] for x in (r_[0], r_[2])} | set(d0[2]) | {x for a_ in d0[1] for x in a_}) or V
    qs = []
    for _ in range(25):
        p_ = rng.choice(PR)
        pick = lambda: rng.choice(names) if rng.random() < .8 else rng.choice(V)
        qs.append((pick(), p_, pick(), p_ in ('is-a', 'has') and rng.random() < .3))
    ops += [qop(q) for q in qs]
    out = blocks(run(ops))
    check(out[0].startswith('B\tok\tsame\tvalid'), 'seed %d rebuild: %s' % (seed, out[0]))
    dump = parse_dump(out[1])
    for q, got in zip(qs, out[2:]):
        MIX[(re.search(r'status=\w+', got) or re.search(r'R\t\w+', got)).group(0)] += 1
        exp = oracle_for(dump, q); nq += 1
        check(got == exp, 'seed %d q %s\n holy  %r\n oracle %r' % (seed, q, got, exp))
# status after each command
rng = random.Random(5)
ops = ['new', 'rebuild']
cmds = [gen_say(rng) for _ in range(60)]
for c in cmds: ops += ['say\t' + c, 'status']
got = blocks(run(ops))[1:]
prev = None
# mutating commands must make the holder stale; compare cvgen movement with status
last_gen = None
for i, c in enumerate(cmds):
    t = got[i].split('\t'); st, gen = t[1], int(t[3])
    g0 = 4 if i == 0 else int(got[i - 1].split('\t')[3])  # placeholder, replaced below
res = [l.split('\t') for l in got]
g_prev = None
for i, t in enumerate(res):
    st, gen = t[1], int(t[3])
    if i == 0:
        continue
    if gen == int(res[i - 1][3]) and res[i - 1][1] == 'valid':
        check(st == 'valid', 'unchanged cvgen but status %s after %s' % (st, cmds[i]))
    if gen != int(res[i - 1][3]):
        check(st == 'stale', 'cvgen moved but status %s after %s' % (st, cmds[i]))
print('     status mix:', dict(MIX))
print('ok   parity: %d full-result queries over 60 respond()-built states identical to Oracle; status valid/stale tracks cvgen over 60 commands' % nq)

BASE = ['new', 'say\tremember robin is a bird', 'say\tremember bird has wings', 'say\tremember bird is also an animal', 'rebuild']
Q = ('robin', 'has', 'wings', False)
# (3) rebuild stage faults
for f in ['after-unavailable', 'after-read-core', 'after-rel-index', 'after-key-universe', 'after-validation', 'before-publish',
          'bad-tuple', 'bad-alias', 'count-mismatch', 'mutate-before-publish']:
    out = blocks(run(BASE + ['rebuild\t' + f, 'status', qop(Q), 'rebuild', 'status', qop(Q)]))
    b0, st, qa, b1, st1, q1 = out[1:7] if False else out[1], out[2], out[3], out[4], out[5], out[6]
    first = out[0]
    check(out[0].startswith('B\tok'), f + ': base rebuild')
    fb, st, qa = out[1], out[2], out[3]
    parts = fb.split('\t')
    if f == 'mutate-before-publish':
        check(parts[1].startswith('invalid: token-changed'), f + ': ' + fb)
        check(parts[2] == 'changed', f + ' (the hook mutates core; expected changed)')
    else:
        check(parts[2] == 'same', f + ': core changed ' + fb)
        check(parts[3] in ('rebuilding', 'invalid'), f + ': holder available after fault: ' + fb)
    check(qa.startswith('R\tABORT') and qa.count('\n') == 2, f + ': query not a bare ABORT: %r' % qa)
    check(out[5].endswith('valid') or '\tvalid' in out[5], f + ': clean rebuild did not restore: ' + out[5])
# race mid-query
out = blocks(run(BASE + ['status', qop(Q) + '\tmutate-mid', 'status', qop(Q)]))
check(out[2].startswith('R\tABORT\treason=stale') and out[2].count('\n') == 2, 'mid-query mutation not ABORT stale: %r' % out[2])
check('\tstale\t' in out[3] + '\t' and out[4].startswith('R\tABORT'), 'after mid-query mutation holder must be stale')
# interruption at start leaves a previously valid holder unavailable
out = blocks(run(BASE + ['status', 'rebuild\tafter-unavailable', 'status', qop(Q)]))
check(out[1].startswith('T\tvalid') and out[3].startswith('T\trebuilding') and out[4].startswith('R\tABORT\treason=rebuilding'), 'unavailable-at-start: %r' % out[1:])
print('ok   fail-closed rebuild: 10 fault stages leave the holder unavailable, core unchanged, ABORT with no evidence, clean rebuild restores; token race at publish and mid-query')

# (5) identity
SAYS = ['say\tremember robin is a bird', 'say\tremember bird has wings']
out = blocks(run(['new'] + SAYS + ['rebuild', 'status', 'new'] + SAYS + ['status', qop(Q)]))
check(out[1].startswith('T\tvalid'), 'identity base')
a = out[2].split('\t'); 
check(a[1] == 'stale', 'new identical-content state must be stale for the old holder, got %r' % out[2])
check(out[3].startswith('R\tABORT\treason=stale'), 'identity: view served a different state')
out = blocks(run(['new'] + SAYS + ['rebuild', 'say\tremember zq is a zr', 'say\tforget zq', 'status']))
check(out[1].startswith('T\tstale'), 'ABA (mutate+revert) must be stale: %r' % out[1])
# unassigned
out = blocks(run(['newholder', 'status']))
# load / corrupted / saved file shape
sf = os.path.join(tmp, 'saved.json'); bad = os.path.join(tmp, 'bad.json'); dupf = os.path.join(tmp, 'dup.json')
Path(bad).write_text('{"facts": {"a": ["b"]}, "order": ["a"], "aliases": ')
out = blocks(run(['new'] + SAYS + ['rebuild', 'savefile\t' + sf, 'status', 'loadfile\t' + sf, 'status', 'rebuild', 'status', 'loadfile\t' + bad, 'status', 'dump']))
check(out[1].startswith('T\tvalid') and out[2].startswith('T\tstale') and out[3].startswith('B\tok') and out[4].startswith('T\tvalid'), 'load path: %r' % out[1:5])
check(out[5].startswith('T\tstale'), 'corrupted load must leave old holder stale: %r' % out[5])
check(parse_dump(out[6]) == ([], [], []), 'corrupted file did not load as a fresh empty state: %r' % out[6])
txt = Path(sf).read_text()
check('cvgen' not in txt and 'cvinst' not in txt, 'saved file carries cv fields')
# disk duplicates keep physical occurrences
Path(dupf).write_text(json.dumps({"facts": {"robin": ["a bird"], "bird": ["has wings"]}, "order": ["robin", "bird"], "aliases": {},
                                  "rels": [["robin", "is-a", "a bird"], ["robin", "is-a", "a bird"], ["bird", "has", "wings"], ["bird", "has", "wings"]], "forgotten": []}))
dq = [('robin', 'is-a', 'a bird', False), ('robin', 'has', 'wings', False), ('robin', 'has', 'wings', True)]
out = blocks(run(['new', 'loadfile\t' + dupf, 'rebuild', 'dump'] + [qop(q) for q in dq]))
check(out[0].startswith('B\tok'), 'dup rebuild: ' + out[0])
dd = parse_dump(out[1])
check(len(dd[0]) == 4, 'core did not keep disk duplicates')
for q, got in zip(dq, out[2:]):
    check(got == oracle_for(dd, q), 'duplicates parity %s\n %r\n %r' % (q, got, oracle_for(dd, q)))
# builtins equal core
out = blocks(run(['builtins']))
check(out[0] == 'BI\t1', 'wire builtins differ from core _BUILTIN_RELS')
# (6) simulated interrupted writers
for name, extra in (('invalidate-only (after-touch before first mutation)', ['inval']),
                    ('invalidate + partial (drop rels, aliases untouched)', ['inval', 'droprels\trobin']),
                    ('partial without further bump (drop only)', ['droprels\trobin'])):
    out = blocks(run(BASE + extra + ['status', qop(Q)]))
    check(out[1].startswith('T\tstale') and out[2].startswith('R\tABORT') and out[2].count('\n') == 2, 'simulated %s: %r' % (name, out[1:]))
print('ok   identity (new identical state, ABA, load, corrupted load), no cv fields in saved file, disk duplicates keep occurrences, builtins equal core, simulated interrupted writers stale')
for f in fails[:8]: print('FAIL', f[:700])
print('0 failures' if not fails else '%d FAILURES' % len(fails))
sys.exit(1 if fails else 0)
