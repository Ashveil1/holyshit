#!/usr/bin/env python3
"""A23.0 self-evaluation harness tests (interp and native).

SE1 report determinism + append-only ledger (the counter is NOT in the
report); SE3 status dimensions kept apart, per-category confusion
matrices, no blended score; SE6 contamination retirement; SE11 production
isolation (reader transcript and agent-memory.json identical whether or
not selfeval ran; disposable per-scenario state); refusal of network /
owner-command items; suite validation; denominator labels.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_agent_shadow import run, setup, own, OWN_HAS

SUITE = str(ROOT / 'tests' / 'selfeval' / 'smoke-en-v2.json')
PROD = ['remember a robin is a bird', 'is a robin a bird',
        'is a sparrow a bird', 'readings', 'quit']


def suite_file(d, name, items, **kw):
    s = {'id': name, 'version': 1, 'kind': 'dialogue', 'frozen': True,
         'tier': 'supported', 'lang': 'en',
         'provenance': {'method': 'synthetic', 'author': 'test'},
         'items': items}
    s.update(kw)
    p = Path(d) / (name + '.json')
    p.write_text(json.dumps(s))
    return str(p)


def mem(d):
    p = Path(d) / 'agent-memory.json'
    return p.read_text(encoding='utf-8') if p.exists() else ''


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a = td / 'a'
        a.mkdir()
        # SE1: determinism, ledger
        o1 = run(argv, ['selfeval run ' + SUITE, 'quit'], a, env)
        rep1 = (a / 'agent-selfeval-report.json').read_bytes()
        o2 = run(argv, ['selfeval run ' + SUITE, 'selfeval ledger', 'quit'],
                 a, env)
        rep2 = (a / 'agent-selfeval-report.json').read_bytes()
        assert rep1 == rep2, 'report is not deterministic'
        assert o1.split('\n')[1] == o2.split('\n')[1]
        r = json.loads(rep1)
        assert 'n' not in r and 'runs' not in r and 'timestamp' not in r
        assert r['blended_score'] == 'none by design'
        led = json.loads((a / 'agent-selfeval-ledger.json').read_text())
        assert [x['n'] for x in led['runs']] == [1, 2]
        assert led['runs'][0]['report_hash'] == r['report_hash']
        assert '2 run(s)' in o2
        # SE3: dimensions apart + matrices + counts, no blended number
        s0 = r['suites'][0]
        assert s0['scored'] == 8 and s0['frozen'] and not s0['failing']
        rc = s0['categories']['recall']['dims']
        assert set(rc) == {'epistemic', 'action', 'contains'}
        assert rc['epistemic']['matrix'] == {'supported': {'supported': 1}}
        assert rc['epistemic']['label'] == 'TOO_FEW_TO_JUDGE'
        bad = suite_file(td, 'wrong', [
            {'id': 'w1', 'category': 'c', 'input': 'is a rock a bird',
             'expect': {'epistemic': 'supported', 'action': 'abstain',
                        'contains': 'zzz'}},
            {'id': 'w2', 'category': 'c', 'input': 'blorp',
             'expect': {'action': 'clarify'}}])
        o = run(argv, ['selfeval run ' + bad, 'quit'], a, env)
        assert 'failing items: w1, w2' in o
        assert 'c / epistemic: 0/1 TOO_FEW_TO_JUDGE matrix ' \
            '{"supported": {"unknown": 1}}' in o, o
        assert 'c / action: 1/2' in o and 'c / contains: 0/1' in o
        # labels at the floors
        for n, lab in ((29, 'TOO_FEW_TO_JUDGE'), (30, 'PRELIMINARY'),
                       (50, 'USEFUL_DIAGNOSTIC'),
                       (100, 'STRONGER_DIVERSITY_DEPENDENT')):
            f = suite_file(td, 'n%d' % n, [
                {'id': 'i%d' % i, 'category': 'k', 'input': 'who is zed',
                 'scenario': 'sc%d' % i,
                 'expect': {'action': 'abstain'}} for i in range(n)])
            o = run(argv, ['selfeval run ' + f, 'quit'], a, env)
            assert 'k / action: %d/%d %s' % (n, n, lab) in o, (n, o[-300:])
        # refusals: network, files, owner commands never run
        f = suite_file(td, 'refuse', [
            {'id': 'r1', 'category': 'x', 'input': 'read url http://x/'},
            {'id': 'r2', 'category': 'x', 'input': 'patterns list'},
            {'id': 'r3', 'category': 'x', 'input': 'selfeval run y'},
            {'id': 'r4', 'category': 'x', 'input': 'quit'},
            {'id': 'r5', 'category': 'x', 'input': 'who is zed',
             'expect': {'action': 'abstain'}}])
        o = run(argv, ['selfeval run ' + f, 'quit'], a, env)
        assert '4 refused' in o and '1 scored of 5 items' in o
        # validation
        dup = suite_file(td, 'dup', [{'id': 'd', 'category': 'x',
                                      'input': 'a'},
                                     {'id': 'd', 'category': 'x',
                                      'input': 'b'}])
        o = run(argv, ['selfeval run ' + dup, 'quit'], a, env)
        assert 'suite refused: duplicate item id d' in o
        unf = suite_file(td, 'unf', [{'id': 'u', 'category': 'x',
                                      'input': 'who is zed',
                                      'expect': {'action': 'abstain'}}],
                         frozen=False)
        o = run(argv, ['selfeval run ' + unf, 'quit'], a, env)
        assert 'UNFROZEN (not baseline-eligible)' in o
        o = run(argv, ['selfeval run nofile.json', 'quit'], a, env)
        assert 'cannot read suite file nofile.json' in o
        # corrupt ledger: report still printed, ledger not written
        c = td / 'c'
        c.mkdir()
        (c / 'agent-selfeval-ledger.json').write_text('{garbage')
        o = run(argv, ['selfeval run ' + SUITE, 'quit'], c, env)
        assert 'ledger unreadable: not written' in o
        assert (c / 'agent-selfeval-ledger.json').read_text() == '{garbage'
        # SE6: contamination (exact text), derivation example reused
        k = td / 'k'
        setup(k, {'own.json': own('has')})
        f = suite_file(k, 'cont', [
            {'id': 'k1', 'category': 'x', 'input': 'a hawk owns a nest',
             'expect': {'action': 'answer'}},
            {'id': 'k2', 'category': 'x', 'input': 'who is zed',
             'expect': {'action': 'abstain'}},
            {'id': 'k3', 'category': 'x', 'input': 'who is zed',
             'status': 'contaminated', 'expect': {'action': 'abstain'}}])
        o = run(argv, ['selfeval run ' + f, 'patterns derive own.json',
                       'selfeval run ' + f, 'quit'], k, env)
        first, second = o.split('selfeval report')[1:3]
        assert '2 scored of 3 items, 1 retired' in first  # k3 only
        assert '1 scored of 3 items, 2 retired' in second
        assert 'retired items: k1, k3' in second
        # A23.1: suite hardening, tiers, lineage, provenance
        def one(name, items=None, **kw):
            its = items or [{'id': 'q', 'category': 'x',
                             'input': 'who is zed',
                             'expect': {'action': 'abstain'}}]
            return run(argv, ['selfeval run ' + suite_file(td, name, its,
                                                           **kw), 'quit'],
                       a, env)
        o = run(argv, ['selfeval run ' + str(ROOT / 'tests' / 'selfeval' /
                                             'smoke-en-v1.json'), 'quit'],
                a, env)
        assert 'suite refused: malformed suite' in o  # v1 lacks tier
        assert 'tier must be' in one('t1', tier='future')
        assert 'suite lang missing' in one('t2', lang='')
        assert 'provenance method must be' in one(
            't3', provenance={'method': 'scraped', 'author': 'x'})
        assert 'provenance author missing' in one(
            't4', provenance={'method': 'synthetic', 'author': ''})
        assert 'owner-real data needs explicit opt_in' in one(
            't5', provenance={'method': 'owner-real', 'author': 'o'})
        o = one('t6', provenance={'method': 'owner-real', 'author': 'o',
                                  'opt_in': True, 'privacy_check': True})
        assert '1 scored of 1 items' in o and 'by owner-real' in o
        # challenge probes never share the supported section (T-SE14)
        o = one('t7', tier='challenge')
        sup, chal = o.split('-- challenge probes')
        assert 'suite t7' not in sup and 'suite t7 v1 challenge' in chal
        rj = json.loads((a / 'agent-selfeval-report.json').read_text())
        assert rj['suites'] == [] and rj['challenge'][0]['id'] == 't7'
        # lineage retires with a stated reason; unclear is excluded
        its = [{'id': 'l%d' % i, 'category': 'x', 'input': 'who is zed',
                'expect': {'action': 'abstain'}, 'lineage': lg}
               for i, lg in enumerate([
                   {'seen_in_dev': True}, {'unclear': True},
                   {'derived_from': ['own.json']}, {'derived_from': []}])]
        o = one('t8', its)
        assert '1 scored of 4 items, 3 retired' in o
        assert 'l0: seen in development' in o
        assert 'l1: lineage unclear (excluded conservatively)' in o
        assert 'l2: derived from development material' in o
        # reordered copy of a derivation example is caught (hint only)
        f = suite_file(k, 'reord', [
            {'id': 'o1', 'category': 'x', 'input': 'a nest a hawk owns',
             'expect': {'action': 'answer'}}])
        o = run(argv, ['patterns derive own.json', 'selfeval run ' + f,
                       'quit'], k, env)
        assert 'o1: word-set equals a derivation example' in o, o
        # aggregate privacy (T-SE17): report holds no input text
        raw = (a / 'agent-selfeval-report.json').read_text()
        assert 'who is zed' not in raw
        # SE11: production isolation
        p1 = td / 'p1'
        p2 = td / 'p2'
        for d in (p1, p2):
            d.mkdir()
        base = run(argv, PROD, p1, env)
        iso = run(argv, PROD[:2] + ['selfeval run ' + SUITE] + PROD[2:],
                  p2, env)
        keep = [l for l in iso.split('\n') if not l.startswith(
            ('selfeval report', 'suite smoke', '  ', 'bye', '-- '))]
        keep_base = [l for l in base.split('\n') if not l.startswith(
            ('  ', 'bye'))]
        assert keep == keep_base, (keep, keep_base)
        assert mem(p1) == mem(p2), 'production memory changed'
        assert 'sparrow' not in mem(p2)
        print('ok %s: deterministic report + append-only ledger, status '
              'dimensions apart, labels, refusals, contamination, '
              'production isolation' % label)
        return rep1


def main():
    import re
    banner = re.search(r'holyshit agent (v[0-9.]+) - type',
                       (ROOT / 'agent' / 'repl.holy').read_text()).group(1)
    assert 'BUILD = "%s"' % banner in (
        ROOT / 'agent' / 'selfeval.holy').read_text(), 'BUILD != banner'
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    ra = rb = None
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if which in ('both', 'interp'):
        ra = suite('interp', [sys.executable, str(ROOT / 'interp.py'),
                              str(ROOT / 'agent' / 'repl.holy')], env)
    if which in ('both', 'native'):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / 'repl'
            r = subprocess.run([sys.executable, str(ROOT / 'hs.py'),
                                'build', str(ROOT / 'agent' / 'repl.holy'),
                                '-o', str(img)], capture_output=True,
                               text=True, env=env)
            assert r.returncode == 0, r.stderr[-400:]
            rb = suite('native', [str(img)], env)
    if ra and rb:
        assert ra == rb, 'native and interp reports differ'
        print('ok native == interp (byte-identical report)')
    print('all agent selfeval tests passed')


if __name__ == '__main__':
    main()
