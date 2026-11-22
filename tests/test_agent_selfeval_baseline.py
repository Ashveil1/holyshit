#!/usr/bin/env python3
"""A23.2: frozen/rolling baselines, comparability, regression reporting,
operational snapshot. T-SE2, SE8, SE9, SE10, SE18 (+ SE15 non-interference).
Hashes are re-derived here with the same poly62 so crafted reports pass
the harness's own integrity check."""
import copy, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_agent_shadow import run
from test_agent_selfeval import suite_file, SUITE, mem

REP, LED = 'agent-selfeval-report.json', 'agent-selfeval-ledger.json'
FRZ, ROL = 'agent-selfeval-baseline-frozen.json', \
    'agent-selfeval-baseline-rolling.json'
ITEMS = [{'id': 'q', 'category': 'x', 'input': 'who is zed',
          'expect': {'action': 'abstain'}}]


def ph(s):
    h1, h2 = 7, 11
    for x in s.encode():
        h1 = (h1 * 131 + x) % 2147483647
        h2 = (h2 * 257 + x) % 2147483629
    return '%08x%08x' % (h1, h2)


def rehash_report(r):
    r.pop('report_hash', None)
    r['report_hash'] = ph(json.dumps(r))
    return r


def rehash_entry(e):
    e.pop('entry_hash', None)
    e['entry_hash'] = ph(json.dumps(e))
    return e


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        d = td / 'w'
        d.mkdir()
        rd = lambda n: (d / n).read_text()
        S2 = suite_file(td, 'other', ITEMS, version=2)
        R = lambda *l: run(argv, list(l) + ['quit'], d, env)
        # no baseline is ever created by a run alone (SE18)
        o = R('selfeval run ' + SUITE, 'selfeval baseline')
        assert 'frozen: none' in o and 'rolling: 0' in o
        assert not (d / FRZ).exists() and not (d / ROL).exists()
        assert 'owner-attested (unauthenticated convention' in o  # SE10
        # owner only, report required, unfrozen refused
        assert 'usage `selfeval freeze NOTE... owner`' in R('selfeval freeze x')
        assert 'no report yet' in run(argv, ['selfeval freeze x owner',
                                             'quit'], td, env)
        unf = suite_file(td, 'unf', ITEMS, frozen=False)
        o = R('selfeval run ' + unf, 'selfeval freeze x owner')
        assert 'every suite must be frozen' in o and not (d / FRZ).exists()
        # accept before frozen / before two reports
        o = R('selfeval run ' + SUITE, 'selfeval accept x owner')
        assert 'no valid frozen release baseline' in o
        o = R('selfeval freeze release one owner')
        assert 'frozen release baseline written' in o and 'immutable' in o
        fz = (d / FRZ).read_bytes()
        assert 'already exists and is immutable' in R(
            'selfeval freeze again owner')
        f2 = td / 'f2'
        f2.mkdir()
        o = run(argv, ['selfeval run ' + SUITE, 'selfeval freeze a owner',
                       'selfeval run ' + SUITE, 'selfeval accept x owner',
                       'quit'], f2, env)
        assert 'at least two distinct release reports' in o
        assert not (f2 / ROL).exists()
        # comparable, unchanged
        o = R('selfeval compare')
        assert 'frozen verdict: UNCHANGED' in o and 'overall: UNCHANGED' in o
        # rolling needs 2 distinct reports: run another suite then restore
        R('selfeval run ' + S2)
        R('selfeval run ' + SUITE)
        o = R('selfeval accept second owner')
        assert 'rolling baseline entry appended' in o
        assert (d / FRZ).read_bytes() == fz, 'frozen changed (SE9)'
        assert 'rolling: 1 owner-accepted' in R('selfeval baseline')
        ro = json.loads(rd(ROL))
        assert ro['entries'][0]['prev'] == '0' and \
            ro['entries'][0]['vs_frozen'] == 'UNCHANGED'
        # SE8: different suite => NOT_DIRECTLY_COMPARABLE, not a regression
        o = R('selfeval run ' + S2, 'selfeval compare')
        assert 'NOT_DIRECTLY_COMPARABLE (suite missing' in o
        assert 'REVIEW_REQUIRED' not in o.split('selfeval compare')[1]
        # contamination state differs, same suite hash
        k = td / 'k'
        k.mkdir()
        (k / 'own.json').write_text(json.dumps(
            [{'text': 'a hawk owns a nest', 'subject': 'hawk',
              'predicate': 'has', 'object': 'nest'}]))
        # SE8 via crafted reports (same suite, changed metric inputs)
        R('selfeval run ' + SUITE)
        cur = json.loads(rd(REP))
        base_frz = json.loads(rd(FRZ))

        def craft(fn):
            c = copy.deepcopy(cur)
            fn(c)
            (d / REP).write_text(json.dumps(rehash_report(c)))
            return R('selfeval compare').split('selfeval compare', 1)[1]

        def dim(c, n):
            x = c['suites'][0]['categories']['recall']['dims']['action']
            x['num'] = n
        o = craft(lambda c: dim(c, 0))
        assert 'recall / action: 1/1 -> 0/1 TOO_FEW_TO_JUDGE ' \
            'REVIEW_THIN_DATA' in o, o
        assert 'overall: REVIEW_THIN_DATA' in o
        # >=30 denominator regression is REVIEW_REQUIRED (edit frozen too)
        big = copy.deepcopy(base_frz)
        x = big['report']['suites'][0]['categories']['recall']['dims'][
            'action']
        x['num'], x['den'], x['label'] = 40, 40, 'PRELIMINARY'
        rehash_report(big['report'])
        (d / FRZ).write_text(json.dumps(rehash_entry(big)))

        def dim40(c):
            y = c['suites'][0]['categories']['recall']['dims']['action']
            y['num'], y['den'], y['label'] = 35, 40, 'PRELIMINARY'
        o = craft(dim40)
        assert '40/40 -> 35/40 PRELIMINARY REVIEW_REQUIRED' in o, o
        assert 'overall: REVIEW_REQUIRED' in o
        # improvement is not auto-accepted
        low = copy.deepcopy(base_frz)
        low['report']['suites'][0]['categories']['recall']['dims'][
            'action']['num'] = 0
        rehash_report(low['report'])
        (d / FRZ).write_text(json.dumps(rehash_entry(low)))
        o = craft(lambda c: None)
        assert '0/1 -> 1/1 TOO_FEW_TO_JUDGE improved (not auto-accepted)' \
            in o and 'overall: IMPROVED_NOT_ACCEPTED' in o, o
        assert not (d / 'agent-selfeval-baseline-new.json').exists()
        # metric definition / harness change => not comparable
        (d / FRZ).write_text(json.dumps(base_frz))
        o = craft(lambda c: c.__setitem__('harness', 'selfeval-9'))
        assert 'harness differs' in o and 'NOT_DIRECTLY_COMPARABLE' in o
        assert 'REVIEW_REQUIRED' not in o.replace(
            'REVIEW_* means', '')
        o = craft(lambda c: c['suites'][0].__setitem__('hash', 'f' * 16))
        assert 'suite hash differs' in o
        o = craft(lambda c: c['suites'][0].__setitem__(
            'retired', ['a2']) or c['suites'][0].__setitem__(
            'retired_reasons', {'a2': 'x'}))
        assert 'contamination state differs' in o
        # baseline tamper detected (hash is not authentication)
        t = json.loads(json.dumps(base_frz))
        t['note'] = 'edited'
        (d / FRZ).write_text(json.dumps(t))
        (d / REP).write_text(json.dumps(cur))
        o = R('selfeval compare')
        assert 'CHANGED OR UNREADABLE (change detected)' in o
        (d / FRZ).write_text(json.dumps(base_frz))
        # altered current report refused
        t = copy.deepcopy(cur)
        t['suites'][0]['scored'] = 99
        (d / REP).write_text(json.dumps(t))
        assert 'altered' in R('selfeval compare')
        (d / REP).write_text(json.dumps(cur))
        # rolling can never hide a frozen regression
        reg = copy.deepcopy(cur)
        reg['suites'][0]['categories']['recall']['dims']['action']['num'] = 0
        (d / REP).write_text(json.dumps(rehash_report(reg)))
        o = R('selfeval accept regressed owner')
        assert 'rolling baseline entry appended' in o, o
        o = R('selfeval compare')
        fr, rl = o.split('-- vs latest owner-accepted ROLLING')
        assert 'frozen verdict: REVIEW_THIN_DATA' in fr
        assert 'rolling verdict: UNCHANGED' in rl
        assert 'overall: REVIEW_THIN_DATA' in rl
        ro = json.loads(rd(ROL))
        assert [e['n'] for e in ro['entries']] == [1, 2]
        assert ro['entries'][1]['prev'] == ro['entries'][0]['entry_hash']
        assert ro['entries'][1]['vs_frozen'] == 'REVIEW_THIN_DATA'
        assert (d / FRZ).read_bytes() == json.dumps(base_frz).encode()
        # corrupt rolling fails closed
        good_roll = rd(ROL)
        t = json.loads(good_roll)
        t['entries'][0]['note'] = 'edited'
        (d / ROL).write_text(json.dumps(t))
        (d / REP).write_text(json.dumps(cur))
        assert 'rolling baseline unreadable' in R('selfeval accept z owner')
        assert 'rolling baseline CHANGED OR UNREADABLE' in R(
            'selfeval compare')
        assert (d / ROL).read_text() == json.dumps(t)
        (d / ROL).write_text(good_roll)
        # SE18/SE15: compare/accept/freeze never touch production
        p1, p2 = td / 'p1', td / 'p2'
        for q in (p1, p2):
            q.mkdir()
        prod = ['remember a robin is a bird', 'is a robin a bird',
                'is a sparrow a bird', 'readings']
        base = run(argv, prod + ['quit'], p1, env)
        iso = run(argv, prod[:2] + ['selfeval run ' + SUITE,
                                    'selfeval freeze r owner',
                                    'selfeval run ' + S2,
                                    'selfeval run ' + SUITE,
                                    'selfeval accept a owner',
                                    'selfeval compare', 'selfeval ops',
                                    'selfeval baseline'] + prod[2:] +
                  ['quit'], p2, env)
        keep = [l for l in iso.split('\n') if l[:1] not in ' -' and
                not l.startswith(('selfeval', 'frozen release', 'rolling',
                                  'operational', 'suite ', 'overall', 'bye'))]
        kb = [l for l in base.split('\n') if not l.startswith(('  ', 'bye'))]
        keep = [l for l in keep if l]
        kb = [l for l in kb if l]
        assert keep == kb, (keep, kb)
        assert mem(p1) == mem(p2)
        # SE2: operational snapshot separate, window rate, no transcripts
        w = td / 'w2'
        w.mkdir()
        (w / 'agent-tripwire.json').write_text(json.dumps({
            'version': 1, 'hash_algo': 'poly62', 'patterns': {
                'pat1': {'state': 'CLEAR', 'fp_lifetime': 3,
                         'polarity_lifetime': 0, 'matches_lifetime': 40,
                         'window': [['k1', 0], ['k2', 1], ['k3', 0]],
                         'reports': [], 'history': []}},
            'events': {c: 0 for c in ['privacy_forget', 'correction',
                                      'addition', 'supersession',
                                      'disagreement', 'preference_change',
                                      'other']},
            'investigations': []}))
        o1 = run(argv, ['selfeval run ' + SUITE, 'selfeval ops', 'quit'],
                 w, env)
        r1 = (w / REP).read_bytes()
        assert 'window FPs 1/3 matches' in o1
        assert 'lifetime (a total, not a rate): matches 40, FPs 3' in o1
        assert 'share of window exposure 3/3' in o1
        o2 = run(argv, ['selfeval run ' + SUITE, 'quit'], w, env)
        assert r1 == (w / REP).read_bytes()
        assert 'pat1' not in r1.decode() and 'window FPs' not in r1.decode()
        (w / 'agent-tripwire.json').write_text('{bad')
        o = run(argv, ['selfeval ops', 'quit'], w, env)
        assert 'tripwire file unreadable' in o
        print('ok %s: freeze/accept owner-only, immutable frozen, comparability, '
              'regression never hidden, tamper detection, ops snapshot' % label)
        return 1


def main():
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if which in ('both', 'interp'):
        suite('interp', [sys.executable, str(ROOT / 'interp.py'),
                         str(ROOT / 'agent' / 'repl.holy')], env)
    if which in ('both', 'native'):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / 'repl'
            r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build',
                                str(ROOT / 'agent' / 'repl.holy'), '-o',
                                str(img)], capture_output=True, text=True,
                               env=env)
            assert r.returncode == 0, r.stderr[-400:]
            suite('native', [str(img)], env)
    print('all agent selfeval baseline tests passed')


if __name__ == '__main__':
    main()
