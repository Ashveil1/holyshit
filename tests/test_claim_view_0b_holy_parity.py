#!/usr/bin/env python3
"""claimview-0b slice 2a: differential parity of agent/claimview.holy (through
tests/claimview/cv_driver.holy) against the independent Python Oracle on the 102
draft fixtures (with shuffled variants where flagged) plus generated property
cases. Compares the FULL result (status, basis, level, provenances, every
evidence path, W charged, readings rows), not only the fixture expectations.
Native route and interp here; all 7 routes in test_claim_view_0b_holy_routes.py.
Parity with an Oracle written from the same contract is NOT proof of
correctness and makes no production claim."""
import json, os, random, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests' / 'claimview'))
import oracle_claim_view_0b as O

FIX = json.loads((ROOT / 'tests/claimview/fixtures-0b.json').read_text())
EXV = {'version': 1, 'sources': []}


class Poison:
    accessed = 0
    def __iter__(self): Poison.accessed += 1; raise AssertionError('readings store touched')
    def __getitem__(self, k): Poison.accessed += 1; raise AssertionError('exclusion input touched')
    def get(self, *a): Poison.accessed += 1; raise AssertionError('exclusion input touched')


def tf(*ts): return '\t'.join(a + '\t' + b + '\t' + c + '\t' + ('1' if n else '0') for a, b, c, n in ts)


def norm_case(c, rng=None):
    edges = []
    for e in c['edges']:
        s_, p_, o_, n_ = e
        if p_.startswith('not-'):
            p_, n_ = p_[4:], True
        edges.append((s_, p_, o_, bool(n_)))
    recs = [(a, t) for a, ts in c.get('aliases', {}).items() for t in ts]
    recs += [tuple(r) for r in c.get('alias_records', [])]
    decl = list(O.BUILTINS_DECL)
    if rng:
        rng.shuffle(edges); rng.shuffle(recs); rng.shuffle(decl)
    return {'edges': edges, 'recs': recs, 'facts': list(c.get('fact_keys', [])),
            'builtins': decl if c.get('builtin') else [], 'query': tuple(c['query']),
            'index_state': c.get('index_state'), 'readings': c.get('readings'),
            'readings_store': c.get('readings_store'), 'poison': 'readings_store_access' in c['expect'] or 'exclusion_input_access' in c['expect']}


def ops_for(name, n):
    ops = ['case\t' + name, 'new']
    ops.append('loadall\t%d%s%s' % (len(n['edges']), ('\t' + tf(*n['edges'])) if n['edges'] else '',
                                    ''.join('\t%s\t%s' % r for r in n['recs'])))
    if n['facts']: ops.append('facts\t' + '\t'.join(n['facts']))
    if n['builtins']: ops.append('builtins\t' + '\t'.join('%s\t%s' % b for b in n['builtins']))
    if n['index_state']: ops.append('break\t' + n['index_state'])
    if n['poison'] or n['readings_store'] == 'empty':
        ops += ['readings', 'excl\t1']
    elif n['readings'] is not None:
        ops += ['readings', 'excl\t1']
        for r in n['readings']:
            sides = r.get('sides') or [r.get('side', 'pos')]
            ops.append('reading\t%s\t%s\t%s\t%s\t%s\t%s' % (r['s'], r['p'], r['o'], r['source'], r.get('sentence', ''), ','.join(sides)))
    q = n['query']
    ops.append('view\t%s\t%s\t%s\t%s' % (q[0], q[1], q[2], '1' if q[3] else '0'))
    return ops


def oracle_text(n):
    st = O.Store(); st.load(n['edges']); st.fact_keys = list(n['facts'])
    for a, t in n['recs']: st.add_alias(a, t)
    st.builtins = n['builtins']
    if n['index_state']: st._break(n['index_state'])
    q = n['query']
    if n['poison']:
        ro, ex = Poison(), Poison()
    elif n['readings_store'] == 'empty':
        ro, ex = [], EXV
    else:
        ro, ex = n['readings'], EXV
    try:
        r = O.view(st, q, ro, ex)
    except O.ImplementationError as e:
        code = {'index missing': 'missing', 'generation mismatch': 'generation', 'count mismatch': 'count'}[str(e)]
        return 'R\tABORT\treason=%s\tw=0\nEND\n' % code
    lines = ['R\t' + r['layer']]
    f = lines[0]
    for k, v in (('status', r.get('status')), ('basis', r.get('basis')), ('reason', r.get('reason')), ('level', r.get('level')), ('lines', r.get('lines')),
                 ('w', r.get('w_charged')), ('trunc_s', r.get('truncated', {}).get('support') if 'truncated' in r else None),
                 ('trunc_o', r.get('truncated', {}).get('opposition') if 'truncated' in r else None), ('rtrunc', r.get('readings_truncated'))):
        if v is not None: f += '\t%s=%s' % (k, v)
    if 'provenances' in r: f += '\tprovs=' + ','.join(r['provenances'])
    if r['layer'] == 'COMPLETE' and r.get('status') != 'AMBIGUOUS':
        f += '\trstage=' + ('1' if ro is not None else '0')
    lines[0] = f
    for key, k2 in (('support', 'support'), ('opposition', 'opp')):
        for it in r.get(key, []):
            lines.append('S\t%s\t%s\t%d' % (k2, it['prov'], it['level']) + ''.join('\t%s\t%s\t%s\t%s' % (e[0], e[1], e[2], '1' if e[3] else '0') for e in it['path']))
    if 'candidates' in r: lines.append('C\t' + '\t'.join(r['candidates']))
    for w in r.get('readings', []): lines.append('D\t%s\t%s\t%s' % (w['source'], w['sentence'], w['side']))
    lines.append('END')
    return '\n'.join(lines) + '\n'


NAMES = ['a', 'b', 'c', 'd', 'e', 'a b', 'A  B', 'an e', 'a c', 'Ünï', 'นก', 'a นก']
PREDS = ['is-a', 'has', 'is-in', 'means']
def gen_cases():
    cases = []
    rng = random.Random(20260522)
    for i in range(260):
        pool = NAMES[:rng.randint(4, len(NAMES))]
        edges = []
        for _ in range(rng.randint(0, 16)):
            p = rng.choice(PREDS)
            edges.append((rng.choice(pool), p, rng.choice(pool), p in ('is-a', 'has') and rng.random() < .25))
        recs = [(rng.choice(pool), rng.choice(pool)) for _ in range(rng.randint(0, 3))]
        facts = rng.sample(pool, rng.randint(0, 2))
        p = rng.choice(PREDS)
        q = (rng.choice(pool), p, rng.choice(pool), p in ('is-a', 'has') and rng.random() < .35)
        if rng.random() < .1: q = (q[0], rng.choice(['can', 'uses']), q[2], False)
        if rng.random() < .05: q = (rng.choice(['it', 'He', '  ']), q[1], q[2], q[3])
        if rng.random() < .05 and q[1] in ('is-in', 'means'): q = (q[0], q[1], q[2], True)
        blt = list(O.BUILTINS_DECL) if rng.random() < .25 else []
        if blt and rng.random() < .6: q = (blt[0][0], 'means', rng.choice([b[1] for b in blt]), False)
        cases.append(('gen%03d' % i, {'edges': edges, 'recs': recs, 'facts': facts, 'builtins': blt, 'query': q, 'index_state': None,
                                      'readings': None, 'readings_store': None, 'poison': False}))
    # chains that hit D=8 boundaries for is-a and has, with negative edges at the boundary
    for L in range(5, 13):
        for neg_last in (False, True):
            chain = [('n%d' % i, 'is-a', 'n%d' % (i + 1), False) for i in range(L)]
            if neg_last: chain.append(('n%d' % L, 'is-a', 'target', True))
            for q in (('n0', 'is-a', 'n%d' % L, False), ('n0', 'is-a', 'target', neg_last), ('n0', 'is-a', 'target', not neg_last)):
                cases.append(('chain%d%s' % (L, 'n' if neg_last else 'p'), {'edges': chain, 'recs': [], 'facts': [], 'builtins': [], 'query': q,
                                                                   'index_state': None, 'readings': None, 'readings_store': None, 'poison': False}))
            hc = chain[:L] + [('n%d' % L, 'has', 'wing', neg_last)]
            for q in (('n0', 'has', 'wing', False), ('n0', 'has', 'wing', True)):
                cases.append(('hchain%d%s' % (L, 'n' if neg_last else 'p'), {'edges': hc, 'recs': [], 'facts': [], 'builtins': [], 'query': q,
                                                                    'index_state': None, 'readings': None, 'readings_store': None, 'poison': False}))
    # long is-in chain, cycle
    cases.append(('isin_long', {'edges': [('p%d' % i, 'is-in', 'p%d' % (i + 1), False) for i in range(20)] + [('p20', 'is-in', 'p0', False)], 'recs': [], 'facts': [],
                                'builtins': [], 'query': ('p0', 'is-in', 'p15', False), 'index_state': None, 'readings': None, 'readings_store': None, 'poison': False}))
    # readings rows incl. exclusions of a source and >5 rows
    rd = [{'s': 'zzz', 'p': 'is-a', 'o': 'b', 'source': 's%d' % i, 'sentence': 'x%d' % (i % 3), 'sides': ['pos', 'neg']} for i in range(4)]
    cases.append(('readings_cap', {'edges': [], 'recs': [], 'facts': [], 'builtins': [], 'query': ('zzz', 'is-a', 'b', False), 'index_state': None,
                                   'readings': rd, 'readings_store': None, 'poison': False}))
    return cases


def all_cases():
    out = []
    for c in FIX['cases']:
        out.append((c['name'], norm_case(c)))
        if c.get('shuffle') or c.get('declaration_order_shuffle'):
            for i in range(3):
                out.append((c['name'] + '#s%d' % i, norm_case(c, random.Random(i))))
    out += gen_cases()
    return out


def build():
    ops, exp = [], []
    for name, n in all_cases():
        ops += ops_for(name, n)
        exp.append('### ' + name + '\n' + oracle_text(n))
    return ops, ''.join(exp)


if __name__ == '__main__':
    ops, expected = build()
    DRV = ROOT / 'tests/claimview/cv_driver.holy'
    tmp = tempfile.mkdtemp(); exe = os.path.join(tmp, 'cvdrv')
    r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build', str(DRV), '-o', exe], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    got = subprocess.run([exe], input='\n'.join(ops) + '\n', capture_output=True, text=True, timeout=300).stdout
    ge, ee = got.split('### '), expected.split('### ')
    bad = [e.split('\n')[0] for g, e in zip(ge, ee) if g != e]
    if len(ge) != len(ee): bad.append('count %d vs %d' % (len(ge), len(ee)))
    for b in bad[:6]:
        i = [e.split('\n')[0] for e in ee].index(b) if b in [e.split('\n')[0] for e in ee] else 0
        print('FAIL ' + b); print('  holy  :', ge[i][:700].replace('\n', ' | ')); print('  oracle:', ee[i][:700].replace('\n', ' | '))
    n_fix = len(FIX['cases'])
    if not bad:
        print('ok   %d cases (%d fixtures + shuffled variants + generated) full-result identical Holy vs Oracle (native)' % (len(ee) - 1, n_fix))
        if '--interp' in sys.argv:
            gi = subprocess.run([sys.executable, str(ROOT / 'interp.py'), str(DRV)], input='\n'.join(ops) + '\n', capture_output=True, text=True, timeout=900).stdout
            print(('ok   ' if gi == got else 'FAIL ') + 'interp route output == native output')
            bad = [] if gi == got else ['interp']
    print('0 failures' if not bad else '%d FAILURES' % len(bad))
    sys.exit(1 if bad else 0)
