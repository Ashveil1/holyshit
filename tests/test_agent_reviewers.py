#!/usr/bin/env python3
"""A22.3 reviewer budgets, suspension and isolated canaries (interp and
native). Budgets refuse and never auto-extend; self-asserted attestations
spend nothing and never count; canaries are synthetic and cannot touch
patterns, counters or approval; a critical miss suspends a family, the
owner reinstates, the delegation file is never edited; ambiguous cases
are never scored.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_review as rv
from test_agent_shadow import run, OWN_HAS

ACT = 'patterns activate ' + OWN_HAS


RUNS = {'fa': 'run1', 'fb': 'run2', 'fz': 'run3'}


def A(f, owner=True):
    return 'patterns attest %s att-%s-%s.json%s' % (
        OWN_HAS, f, RUNS[f], ' owner' if owner else '')


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        base = td / 'base'
        out0 = rv.build(base, argv, env)
        for fam, dep in (('fa', 'dep1'), ('fb', 'dep2'), ('fz', 'dep3')):
            rv.att(base, out0, fam, RUNS[fam], dep)
        rv.deleg(base)
        cases = {'cases': [
            {'id': 'c1', 'expected': 'reject', 'critical': True,
             'synthetic': True, 'text': 'a made-up case'},
            {'id': 'c2', 'expected': 'approve', 'synthetic': True},
            {'id': 'c3', 'expected': 'reject', 'synthetic': True,
             'ambiguous': True}]}
        (base / 'cases.json').write_text(json.dumps(cases))
        ans = lambda a, b, c: {'answers': [
            {'id': 'c1', 'verdict': a}, {'id': 'c2', 'verdict': b},
            {'id': 'c3', 'verdict': c}]}
        (base / 'ans-bad.json').write_text(json.dumps(
            ans('approve', 'approve', 'approve')))
        (base / 'ans-amb.json').write_text(json.dumps(
            ans('reject', 'approve', 'approve')))
        (base / 'ans-soft.json').write_text(json.dumps(
            {'answers': [{'id': 'c1', 'verdict': 'reject'},
                         {'id': 'c2', 'verdict': 'reject'}]}))
        prod = dict(cases)
        prod = {'cases': [dict(cases['cases'][0], text='see pc-43a7bbc8')]}
        (base / 'cases-prod.json').write_text(json.dumps(prod))
        nons = {'cases': [{'id': 'x', 'expected': 'reject'}]}
        (base / 'cases-nonsyn.json').write_text(json.dumps(nons))
        outs = {}

        def sc(name, cmds):
            d = td / name
            shutil.copytree(base, d)
            o = run(argv, list(cmds) + ['quit'], d, env)
            outs[name] = o
            return d, o
        D = 'patterns delegate del.json'
        # budgets
        d, o = sc('bud', [
            D, 'patterns reviewers',
            'patterns budget fa 1 1000 owner', 'patterns budget fb 0 1000 owner',
            'patterns budget fx 1 0 owner', 'patterns budget fa x y owner',
            'patterns budget fa 1 1000',
            A('fa'), A('fb'), A('fz'), A('fz', False),
            'patterns reviewers'])
        assert 'review is unbudgeted' in o
        assert 'recorded at-' in o and 'assurance owner_attested' in o
        assert 'A10 candidate budget exhausted for fb' in o
        assert 'A10 family fz has no budget' in o
        assert 'assurance self_asserted (cannot count toward independence)' in o
        assert 'budget refused: limits must be whole numbers' in o
        assert 'usage: `patterns budget FAMILY' in o or \
            'budget refused: usage' in o
        assert 'fa ACTIVE: budget 1/1 candidates' in o
        d, o = sc('work', [D, 'patterns budget fa 5 1 owner', A('fa'),
                           'patterns reviewers'])
        assert 'A10 weighted-work budget exhausted for fa' in o
        assert 'nothing auto-extends' in o
        # suspension via a critical canary, owner reinstatement
        d, o = sc('susp', [
            D, 'patterns budget fa 5 1000 owner',
            'patterns budget fb 5 1000 owner', A('fa'), A('fb'),
            'patterns approve ' + OWN_HAS,
            'patterns canary fa cases.json ans-amb.json owner',
            'patterns canary fa cases.json ans-bad.json owner', ACT,
            'patterns reviewers',
            'patterns reinstate fa owner reviewed the miss', ACT])
        dl = (d / 'del.json').read_bytes()
        assert dl == (base / 'del.json').read_bytes()
        assert 'flag: identical rationale' in o
        assert '1 passed, 1 missed, 0 critical' not in o
        assert 'canary fa: 2 passed, 0 missed, 0 critical, 0 unanswered, ' \
            '1 ambiguous (never scored)' in o, o[-1500:]
        assert 'canary fa: 1 passed, 1 missed, 1 critical' in o
        assert 'family SUSPENDED (owner decides reinstatement' in o
        assert 'activate refused: L15 A11 lineage family fa is SUSPENDED' in o
        assert 'owner reinstated fa' in o
        assert 'activated ' + OWN_HAS in o
        assert 'critical 1' in o or '1 critical' in o
        # canary isolation and pool validation
        st0 = (base / 'agent-patterns.json').read_bytes()
        d, o = sc('can', [
            'patterns canary fa cases-prod.json ans-bad.json owner',
            'patterns canary fa cases-nonsyn.json ans-bad.json owner',
            'patterns canary fa cases.json ans-soft.json owner',
            'patterns canary fa cases.json ans-bad.json',
            'patterns reinstate fa NOTE'])
        assert 'references production data' in o
        assert 'every case needs id, expected and synthetic=true' in o
        assert 'canary fa: 1 passed, 1 missed, 0 critical, 0 unanswered, ' \
            '1 ambiguous' in o
        assert 'SUSPENDED' not in o
        assert 'usage: `patterns canary' in o or 'canary refused: usage' in o
        assert 'reinstate refused: usage' in o
        assert (d / 'agent-patterns.json').read_bytes() == st0
        assert not (d / 'agent-tripwire.json').exists()
        assert not (d / 'agent-attestations.json').exists()
        src = (ROOT / 'agent' / 'reviewers.holy').read_text()
        imps = [l for l in src.split('\n') if l.startswith('import ')]
        assert imps == ['import agent.core', 'import agent.patgen'], imps
        # a corrupt reviewer registry fails closed for attestation
        d = td / 'corrupt'
        shutil.copytree(base, d)
        (d / 'agent-reviewers.json').write_text('{garbage')
        o = run(argv, [D, A('fa'), 'quit'], d, env)
        assert 'A11 reviewer registry unreadable' in o
        print('ok %s: budgets enforced, canaries isolated, critical miss '
              'suspends, owner reinstates, delegation untouched' % label)
        return outs


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
            r = subprocess.run([sys.executable, str(ROOT / 'hs.py'),
                                'build', str(ROOT / 'agent' / 'repl.holy'),
                                '-o', str(img)], capture_output=True,
                               text=True, env=env)
            assert r.returncode == 0, r.stderr[-400:]
            suite('native', [str(img)], env)
    print('all agent reviewers tests passed')


if __name__ == '__main__':
    main()
