#!/usr/bin/env python3
"""ORACLE SELF-CONFORMANCE for tests/claimview/oracle_claim_view_0b.py (DRAFT).

Not a production test. Runs the DRAFT fixtures-0b.json and generated
formula-derived cases against the independent Oracle. Passing shows the
Oracle and the draft fixtures agree; it proves nothing about any Holy
implementation. Fixtures marked independent_review_required are reported
separately and are not promoted by passing here.
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'claimview'))
import oracle_claim_view_0b as o

FIX = json.loads((HERE / 'claimview' / 'fixtures-0b.json').read_text())
# The expected OUT_OF_SCOPE in these two draft cases assumes the 'robin' bucket
# is inspected. Under rev14 section 3/5 it is never returned or examined, so no
# colliding identity is inspected and the Oracle answers COMPLETE. Fixture fix
# needed (make the colliding tuple or alias target actually examined).
KNOWN_FIXTURE_DEFECTS = set()
fails = 0
SHUF = 6


EXV = {'version': 1, 'sources': []}


class Poison:
    accessed = 0

    def __iter__(self):
        Poison.accessed += 1
        raise AssertionError('readings store touched')

    def __getitem__(self, k):
        Poison.accessed += 1
        raise AssertionError('exclusion input touched')

    def get(self, *a):
        Poison.accessed += 1
        raise AssertionError('exclusion input touched')


def check(name, cond, detail=''):
    global fails
    print(('ok   ' if cond else 'FAIL ') + name + ('' if cond else ' ' + str(detail)[:600]))
    if not cond:
        fails += 1


def build(c, rng=None):
    edges = []
    for e in c['edges']:   # fixture encoding: stored name may be 'not-<pred>'
        s_, p_, o_, n_ = e
        if p_.startswith('not-'):
            p_, n_ = p_[4:], True
        edges.append((s_, p_, o_, bool(n_)))
    recs = [(a, t) for a, ts in c.get('aliases', {}).items() for t in ts]
    recs += [tuple(r) for r in c.get('alias_records', [])]
    decl = list(o.BUILTINS_DECL)
    if rng:
        rng.shuffle(edges)
        rng.shuffle(recs)
        rng.shuffle(decl)
    st = o.Store()
    st.load(edges)
    st.fact_keys = list(c.get('fact_keys', []))
    for a, t in recs:
        st.add_alias(a, t)
    st.builtins = decl if c.get('builtin') else []
    b = c.get('bucket')
    if b == 'explicit_empty_for_non_universe_key':
        st.add_explicit_empty_bucket(o.canon(c['query'][0]))
    if b == 'explicit_empty_fact_key':
        for k in st.fact_keys:
            st.add_explicit_empty_bucket(o.canon(k))
    if c.get('index_state'):
        st._break(c['index_state'])
    return st


def compare(exp, res):
    bad = []
    for k in ('layer', 'status', 'basis', 'reason', 'level'):
        if k in exp and res.get(k) != exp[k]:
            bad.append((k, exp[k], res.get(k)))
    if 'provenance' in exp and res.get('provenances') != [exp['provenance']]:
        bad.append(('provenance', exp['provenance'], res.get('provenances')))
    if 'lines' in exp and res.get('lines') != exp['lines']:
        bad.append(('lines', exp['lines'], res.get('lines')))
    if 'w_charged' in exp and res.get('w_charged') != exp['w_charged']:
        bad.append(('w_charged', exp['w_charged'], res.get('w_charged')))
    return bad


def run_case(c, rng=None):
    st = build(c, rng)
    q = tuple(c['query'])
    exp = c['expect']
    readings = c.get('readings')
    ro, ex = readings, EXV
    if 'readings_store_access' in exp or 'exclusion_input_access' in exp:
        ro, ex = Poison(), Poison()
    elif c.get('readings_store') == 'empty':
        ro = []
    try:
        res = o.view(st, q, ro, ex)
    except o.ImplementationError:
        return st, {'abort': 'implementation_error'}
    return st, res


def fixture_run():
    rev, ok = [], 0
    for c in FIX['cases']:
        exp = c['expect']
        variants = [None] + ([random.Random(i) for i in range(SHUF)] if c.get('shuffle') or c.get('declaration_order_shuffle') else [])
        outs = []
        for r in variants:
            st, res = run_case(c, r)
            if 'abort' in exp:
                outs.append([] if res.get('abort') == exp['abort'] else [('abort', exp['abort'], res)])
            else:
                outs.append(compare(exp, res))
        bad = next((b for b in outs if b), [])
        if 'readings' in exp and not bad:
            q = c['query']
            rows = res.get('readings', [])
            if exp['readings'] == 'none':
                if rows:
                    bad = [('readings', 'none', rows)]
            else:
                want = [r for r in c.get('readings', []) if o.canon(r['s']) == o.canon(q[0]) and r['p'] == q[1] and o.canon(r['o']) == o.canon(q[2])]
                if sorted(x['source'] for x in rows) != sorted(r['source'] for r in want) or not rows:
                    bad = [('readings', 'exact_match_only', rows)]
        if 'assert_untouched_alias_records' in c:
            st, res = run_case(c)
            touched = len(st.alias_touched)
            matching = sum(1 for a, t in st.alias_records if o.canon(a) == o.canon(c['query'][0]))
            if touched != matching:
                bad = bad or [('alias_touched', matching, touched)]
        if exp.get('readings_store_access') is False and Poison.accessed:
            bad = bad or [('poison', 0, Poison.accessed)]
        tag = ' [independent_review_required]' if c.get('independent_review_required') else ''
        if bad and c['name'] in KNOWN_FIXTURE_DEFECTS:
            print('DISAGREE (fixture defect against rev14 text, reported) ' + c['name'] + ' ' + str(bad)[:200])
            continue
        check(c['name'] + tag, not bad, bad)
        ok += not bad
    return ok


def mk(edges, aliases=(), facts=(), builtins=False):
    st = o.Store()
    st.load(edges)
    st.fact_keys = list(facts)
    for a, t in aliases:
        st.add_alias(a, t)
    if builtins:
        st.builtins = list(o.BUILTINS_DECL)
    return st


def vw(st, q):
    try:
        return o.view(st, q, [], EXV)
    except o.ImplementationError:
        return {'abort': True}


def generated_formula_cases():
    """Expectations from closed-form arithmetic in the contract, written
    here without calling the Oracle to decide them."""
    # is-a object n hops away: level n for n<=8, depth_limit for n>=9
    for n in range(1, 13):
        e = [('n%d' % i, 'is-a', 'n%d' % (i + 1), False) for i in range(n - 1)]
        e.append(('n%d' % (n - 1), 'is-a', 'goal', False))
        r = vw(mk(e), ('n0', 'is-a', 'goal', False))
        ok = (r.get('level') == n and r['status'] == 'SUPPORTED') if n <= 8 else \
            (r['layer'] == 'INCOMPLETE' and r['reason'] == 'depth_limit')
        check('gen is-a object %d hops' % n, ok, r)
    # has evidence on the node k is-a hops away
    for k in range(0, 12):
        e = [('n%d' % i, 'is-a', 'n%d' % (i + 1), False) for i in range(k)]
        e.append(('n%d' % k, 'has', 'x', False))
        r = vw(mk(e), ('n0', 'has', 'x', False))
        ok = (r.get('level') == k and r['status'] == 'SUPPORTED') if k <= 8 else \
            (r['layer'] == 'INCOMPLETE' and r['reason'] == 'depth_limit')
        check('gen has evidence %d hops' % k, ok, r)
    # no evidence, is-a chain of m edges: UNKNOWN for m<=8, depth_limit for m>=9 (is-a query)
    for m in range(0, 12):
        e = [('n%d' % i, 'is-a', 'n%d' % (i + 1), False) for i in range(m)]
        r = vw(mk(e, facts=['n0']), ('n0', 'is-a', 'goal', False))
        ok = r['status'] == 'UNKNOWN' if m <= 8 else (r['layer'] == 'INCOMPLETE' and r['reason'] == 'depth_limit')
        check('gen is-a no evidence chain %d' % m, ok, r)
    # W: N irrelevant tuples in one bucket
    for n in (1, 499, 500, 501, 502):
        e = [('s', 'has', 'j%04d' % i, False) for i in range(n)]
        r = vw(mk(e), ('s', 'is-a', 't', False))
        ok = (r['status'] == 'UNKNOWN' and r['w_charged'] == n) if n <= 500 else (r['layer'] == 'INCOMPLETE' and r['reason'] == 'work_limit')
        check('gen W %d irrelevant tuples' % n, ok, r)
    # collision as the LAST tuple of a bucket of N: seen iff N<=500
    for n in range(2, 504):
        e = [('root', 'has', 'a x', False)] + [('root', 'has', 'm%04d' % i, False) for i in range(n - 2)] + [('root', 'has', 'x', False)]
        rng = random.Random(n)
        rng.shuffle(e)
        r = vw(mk(e), ('root', 'has', 'q', False))
        ok = (r['layer'] == 'OUT_OF_SCOPE' and r['reason'] == 'identity_collision') if n <= 500 else (r['layer'] == 'INCOMPLETE' and r['reason'] == 'work_limit')
        if not ok or n in (2, 499, 500, 501, 503):
            check('gen collision at last item of %d' % n, ok, r)


def naive(edges, q):
    """Naive set-based reference for small collision-free is-a/has graphs:
    BFS distance table, then nearest level. No W, no ordering."""
    s, p, o_, neg = q
    dist = {s: 0}
    todo = [s]
    while todo:
        n = todo.pop(0)
        for (a, pr, b, ng) in edges:
            if a == n and pr == 'is-a' and not ng and b not in dist:
                dist[b] = dist[n] + 1
                todo.append(b)
    ev = []
    for (a, pr, b, ng) in edges:
        if a in dist and pr == p and b == o_:
            lvl = dist[a] + (1 if p == 'is-a' else 0)
            ev.append((lvl, ng == neg))
    if p == 'is-a':
        if any(l > 8 for l, _ in ev) or max(dist.values()) >= 9:
            ev = [x for x in ev if x[0] <= 8]
    if not ev:
        return ('UNKNOWN', None)
    m = min(l for l, _ in ev)
    sup = any(x for l, x in ev if l == m)
    opp = any((not x) for l, x in ev if l == m)
    return ('CONTRADICTED' if opp and sup else 'SUPPORTED' if sup else 'CONTRADICTED', m)


def property_cases(n=400):
    rng = random.Random(20260601)
    names = ['n%d' % i for i in range(7)] + ['goal']
    bad = 0
    for i in range(n):
        e = []
        for _ in range(rng.randint(0, 14)):
            a, b = rng.choice(names[:7]), rng.choice(names)
            pr = rng.choice(['is-a', 'is-a', 'has'])
            if pr == 'has':
                b = rng.choice(['goal', 'x'])
            e.append((a, pr, b, rng.random() < 0.25))
        p = rng.choice(['is-a', 'has'])
        q = ('n0', p, 'goal', rng.random() < 0.3)
        want = naive(e, q)
        got = None
        for v in range(3):
            ee = list(e)
            random.Random(v).shuffle(ee)
            r = vw(mk(ee, facts=['n0']), q)
            g = (r['status'], r.get('level')) if r['layer'] == 'COMPLETE' else (r['layer'], None)
            if got is not None and g != got:
                bad += 1
                print('FAIL order-dependent', e, q, g, got)
            got = g
        if got[0] in ('SUPPORTED', 'CONTRADICTED', 'UNKNOWN'):
            if got != want and not (want[0] == 'UNKNOWN' and got[0] == 'UNKNOWN'):
                bad += 1
                print('FAIL naive differs', e, q, got, want)
    check('property: %d random small graphs agree with naive set model, order independent' % n, bad == 0, bad)


def lifecycle_cases():
    st = o.Store()
    st.load([('a robin', 'is-a', 'a bird', False), ('robin', 'has', 'wings', False)])
    check('index equals authoritative after load', st.full_index_equal())
    check('robin and a robin are distinct buckets', len(st._index) == 2)
    st.add_tuple(('a robin', 'has', 'legs', False))
    st.add_tuple(('a robin', 'has', 'legs', False))
    check('duplicates kept individually', len(st.authoritative()) == 4 and st.full_index_equal())
    st.remove_tuple(('a robin', 'has', 'legs', False))
    check('forget keeps index equal', st.full_index_equal() and len(st.authoritative()) == 3)
    st.rebuild()
    check('rebuild keeps index equal', st.full_index_equal())
    st.add_explicit_empty_bucket('zz')
    check('empty bucket inert for comparison', st.full_index_equal())
    snap = (list(st._tuples), {k: list(v) for k, v in st._index.items()}, st._gen, st._index_gen)
    vw(st, ('a robin', 'has', 'wings', False))
    check('view leaves tuples, index, generation byte-identical', snap == (list(st._tuples), {k: list(v) for k, v in st._index.items()}, st._gen, st._index_gen))
    for mode in ('missing', 'stale', 'count'):
        s2 = mk([('a robin', 'is-a', 'a bird', False)], facts=['a robin'])
        s2._break(mode)
        r = vw(s2, ('zzz', 'is-a', 'b', False))
        check('integrity %s aborts valid NONE query' % mode, r.get('abort') is True, r)
        r = vw(s2, ('a', 'can', 'b', False))
        check('integrity %s: unsupported predicate stays OUT_OF_SCOPE, no check' % mode, r.get('reason') == 'predicate_unsupported', r)
        if mode == 'missing':
            vw(s2, ('a robin', 'is-a', 'a bird', False))
            check('no lazy init or repair in the view', s2._index is None)


def families_cases():
    base = [('a robin', 'is-a', 'a bird', False)]
    q = ('zzz', 'is-a', 'b', False)    # NONE subject: COMPLETE, readings stage runs

    def rd(src, sent='x', o_='b', side='pos'):
        return {'s': 'zzz', 'p': 'is-a', 'o': o_, 'source': src, 'sentence': sent, 'side': side}

    def run(readings, ex, qq=q, st=None):
        return o.view(st or mk(base, facts=['a robin']), qq, readings, ex)

    ex0 = {'version': 1, 'sources': []}
    r = run([rd('s2'), rd('s1'), rd('s1', 'a', side='neg')], ex0)
    check('privacy: rows ordered by source, sentence, side', [(x['source'], x['sentence'], x['side']) for x in r['readings']] == [('s1', 'a', 'neg'), ('s1', 'x', 'pos'), ('s2', 'x', 'pos')], r)
    r = run([rd('s1'), rd('s2')], {'version': 1, 'sources': ['s1']})
    check('privacy: excluded source silent (no row, no hidden count)', [x['source'] for x in r['readings']] == ['s2'] and set(r) <= {'layer', 'status', 'basis', 'w_charged', 'readings', 'readings_truncated'}, r)
    r = run([rd('s1')], {'version': 1, 'sources': ['s1']})
    check('privacy: all excluded gives no readings section at all', 'readings' not in r and 'readings_truncated' not in r, r)
    r = run([rd('s%d' % i) for i in range(7)], {'version': 1, 'sources': ['s0', 's1']})
    check('privacy: eligibility before cap and count (7 rows, 2 excluded: 5 shown, 0 over)', len(r['readings']) == 5 and r['readings_truncated'] == 0, r)
    r = run([rd('s%d' % i) for i in range(8)], ex0)
    check('readings cap 5 with overflow count 3', len(r['readings']) == 5 and r['readings_truncated'] == 3, r)
    r = run([rd('s1', o_='c'), rd('s2', o_='B')], ex0)
    check('readings: exact canonical s,p,o selection only', [x['source'] for x in r['readings']] == ['s2'], r)
    r1 = run([rd('s1', side='neg')], ex0)
    r2 = run([rd('s1', side='neg')], ex0, ('zzz', 'is-a', 'b', True))
    check('readings: same rows for either query polarity, status unchanged', r1['readings'] == r2['readings'] and r1['status'] == r2['status'] == 'UNKNOWN')
    bads = [None, 'x', [], {'version': 2, 'sources': []}, {'sources': []}, {'version': 1}, {'version': 1, 'sources': 'a'},
            {'version': 1, 'sources': [1]}, {'version': 1, 'sources': ['']}, {'version': 1, 'sources': ['ok', None]}]
    for i, b in enumerate(bads):
        r = run([rd('s1')], b)
        check('malformed exclusion %d fails closed: section absent, status unchanged' % i, 'readings' not in r and r['status'] == 'UNKNOWN', r)
    r = run([rd('')], ex0)
    check('reading with empty source is ineligible', 'readings' not in r, r)
    # poison: readings and exclusion input never touched outside COMPLETE non-AMBIGUOUS
    Poison.accessed = 0
    big = [('root', 'is-a', 'h%d' % i, False) for i in range(501)]
    cases = [
        ('INCOMPLETE work_limit', mk(big), ('root', 'has', 'x', False)),
        ('OUT_OF_SCOPE', mk(base), ('a', 'can', 'b', False)),
        ('OUT_OF_SCOPE collision', mk([('s', 'has', 'a z', False), ('s', 'has', 'z', False)]), ('s', 'has', 'q', False)),
        ('AMBIGUOUS', mk([('k1', 'is-a', 't', False), ('k2', 'is-a', 't', False)], aliases=[('al', 'k1'), ('al', 'k2')]), ('al', 'is-a', 't', False)),
    ]
    for name, st, qq in cases:
        res = o.view(st, qq, Poison(), Poison())
        check('poisoned readings/exclusions untouched: %s (%s)' % (name, res['layer']), Poison.accessed == 0 and 'readings' not in res, res)
    # alias-record scale (B44, B50, B52)
    for m in (1, 499, 500, 501):
        recs = [('z' + ' ' * (i % 7 + 1) + 'zeb', 'k') for i in range(m)]   # all canonical 'z zeb'
        st = mk([('k', 'has', 'w', False)], aliases=recs + [('other%d' % j, 'k') for j in range(600)], facts=['k'])
        r = o.view(st, ('z zeb', 'has', 'x', False), [], EXV)
        total = m + 1
        want = ('COMPLETE', total) if total <= 500 else ('INCOMPLETE', 500)
        check('alias scale: %d matching + 600 nonmatching, %d examinations' % (m, total), (r['layer'], r['w_charged']) == want and len(st.alias_touched) == m, (r, len(st.alias_touched)))
    st = mk([('k', 'has', 'w', False)], aliases=[('o%d' % j, 'k') for j in range(600)] + [('al', 'k')], facts=['k'])
    r = o.view(st, ('al', 'has', 'w', False), [], EXV)
    check('alias scale: nonmatching never touched, charged only 1 alias + 1 tuple', r['w_charged'] == 2 and st.alias_touched == [('al', 'k')], r)
    # display caps
    e = [('s', 'is-a', 'm%d' % i, False) for i in range(7)] + [('s', 'is-a', 'o%d' % i, False) for i in range(6)]
    e += [('m%d' % i, 'has', 'x', False) for i in range(7)] + [('o%d' % i, 'has', 'x', True) for i in range(6)]
    r = o.view(mk(e), ('s', 'has', 'x', False), [], EXV)
    check('caps: 7 support lines show 5, 6 opposition show 5, overflow counts 2 and 1, still COMPLETE both_sides',
          r['layer'] == 'COMPLETE' and r['basis'] == 'both_sides' and len(r['support']) == 5 and len(r['opposition']) == 5
          and r['truncated'] == {'support': 2, 'opposition': 1} and r['lines'] == 13 and r['level'] == 1, r)
    r = o.view(mk(e), ('s', 'has', 'x', False), [], EXV)
    e2 = [('s', 'is-a', 'm', False), ('s', 'is-a', 'm', False), ('m', 'has', 'x', False), ('m', 'has', 'x', False)]
    r = o.view(mk(e2), ('s', 'has', 'x', False), [], EXV)
    check('caps: duplicate tuples collapse to one derived line, charged 4', r['lines'] == 1 and r['w_charged'] == 4 and r['basis'] == 'derived_only', r)
    st = mk([('k%d' % i, 'is-a', 't', False) for i in range(7)], aliases=[('al', 'k%d' % i) for i in range(7)])
    r = o.view(st, ('al', 'is-a', 't', False), Poison(), Poison())
    check('caps: ambiguous candidates capped at 5, no readings access', r['status'] == 'AMBIGUOUS' and len(r['candidates']) == 5 and 'readings' not in r, r)


if __name__ == '__main__':
    n = fixture_run()
    generated_formula_cases()
    property_cases()
    lifecycle_cases()
    families_cases()
    print('fixtures-0b: %d/%d agree with the Oracle (DRAFT, self-conformance only)' % (n, len(FIX['cases'])))
    print('%d failures' % fails)
    sys.exit(1 if fails else 0)
