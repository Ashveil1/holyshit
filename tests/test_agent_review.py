#!/usr/bin/env python3
"""A21.2a delegated review gate tests (interp and native must agree).

Covers: attestation binding and identity assurance (self-asserted never
independent), proposer-family exclusion, forged coverage, reviewer
conflict and owner decisions, stale-approval invalidation, revocation,
agent-proposed vs verified lineage edges, and that nothing is ever
ACTIVE (the store validator forbids it).
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_shadow as sh
from test_agent_shadow import run, setup, own, OWN_HAS

RV = 'patterns review ' + OWN_HAS


def rd(i):
    return ('read r%d: a crow%d owns a nest. the day%d is long. '
            'a pond%d is deep' % (i, i, i, i))


def build(d, argv, env):
    setup(d, {'own.json': own('has')})
    lines = ['patterns derive own.json', 'patterns shadow ' + OWN_HAS]
    for i in range(55):
        lines += [rd(i), 'patterns origin r%d o%d verified_independent'
                  % (i, i % 5)]
    lines += [RV, 'quit']
    return run(argv, lines, d, env)


def att(d, out, fam, run_id, dep, verdict='approve', tweak=None):
    keys = dict(re.findall(r'(\w+_hash) ([0-9a-f]{16})',
                           out.split('coverage keys:')[-1].split('\n')[0]))
    st = json.loads((d / 'agent-patterns.json').read_text())
    c = st['candidates'][OWN_HAS]
    h = re.findall(r'snapshot hash: ([0-9a-f]{16})', out)[-1]
    r = {'identity': {'provider': 'p-' + fam, 'model_version': 'm1',
                      'lineage_family': fam, 'deployment_id': dep,
                      'run_id': run_id, 'config_version': 'c1',
                      'tool_setup': 'none', 'timestamp': '2026-01-01T00:00Z',
                      'delegation_version': '1'},
         'binding': {'candidate': OWN_HAS, 'snapshot_hash': h},
         'coverage': {'tests_hash': keys['tests_hash'],
                      'origins_hash': keys['origins_hash'],
                      'corpus_hash': keys['corpus_hash'],
                      'sample_events': [x['event'] for x in
                                        c['shadow']['samples']],
                      'disagreement_events': [], 'truncated': False},
         'verdict': verdict, 'rationale': 'checked packet'}
    if tweak:
        tweak(r)
    f = d / ('att-%s-%s.json' % (fam, run_id))
    f.write_text(json.dumps(r))
    return f.name


def deleg(d, version=1, **kw):
    x = {'version': version, 'revoked': False, 'expired': False,
         'predicates': ['has', 'is-a', 'is-in', 'means'],
         'accepted_families': ['fa', 'fb', 'fp', 'fc'],
         'proposer_family': 'fp', 'owner_ref': 'owner-msg-1'}
    x.update(kw)
    (d / 'del.json').write_text(json.dumps(x))


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        base = td / 'base'
        out0 = build(base, argv, env)
        assert 'coverage keys: tests_hash' in out0
        assert 'READY FOR HUMAN REVIEW' in out0
        res = {}

        def scenario(name, prep, cmds):
            d = td / name
            shutil.copytree(base, d)
            deleg(d)
            fl = prep(d)
            o = run(argv, ['patterns delegate del.json'] + cmds(fl) +
                    ['quit'], d, env)
            res[name] = o
            return d, o

        def two(d):
            return [att(d, out0, 'fa', 'run1', 'dep1'),
                    att(d, out0, 'fb', 'run2', 'dep2')]
        # 1. self-asserted attestations never count
        d, o = scenario('self', two, lambda f: [
            'patterns attest %s %s' % (OWN_HAS, f[0]),
            'patterns attest %s %s' % (OWN_HAS, f[1]),
            'patterns approve ' + OWN_HAS])
        assert 'A05' in o and 'self-asserted' in o and 'approve refused' in o
        # 2. owner-attested, two families, approves; still inactive
        d, o = scenario('ok', two, lambda f: [
            'patterns attest %s %s owner' % (OWN_HAS, f[0]),
            'patterns attest %s %s owner' % (OWN_HAS, f[1]),
            'patterns approve ' + OWN_HAS, 'patterns list',
            # changed provenance invalidates the approval
            'patterns lineage o4 o0 repost disputed owner',
            'patterns review ' + OWN_HAS,
            'patterns approve ' + OWN_HAS,
            'patterns revoke ' + OWN_HAS, 'patterns list'])
        assert 'approved ' + OWN_HAS in o and 'INACTIVE' in o
        assert 'approval invalidated' in o or 'REVIEW_PENDING' in o
        assert 'A07' in o or 'A04' in o or 'A01' in o
        assert 'REVOKED' in o
        st = json.loads((d / 'agent-patterns.json').read_text())
        c = st['candidates'][OWN_HAS]
        assert c['active'] is False and c['label'] == 'REVOKED'
        assert any('APPROVED (delegated)' in x
                   for x in c['provenance']['history'])
        # 3. proposer-family reviewer excluded
        d, o = scenario('prop', lambda d: [
            att(d, out0, 'fp', 'run1', 'dep1'),
            att(d, out0, 'fb', 'run2', 'dep2')], lambda f: [
            'patterns attest %s %s owner' % (OWN_HAS, f[0]),
            'patterns attest %s %s owner' % (OWN_HAS, f[1]),
            'patterns approve ' + OWN_HAS])
        assert 'A06' in o and 'approve refused' in o
        # 4. same run id / deployment: not independent
        d, o = scenario('same', lambda d: [
            att(d, out0, 'fa', 'run1', 'dep1'),
            att(d, out0, 'fb', 'run1', 'dep1')], lambda f: [
            'patterns attest %s %s owner' % (OWN_HAS, f[0]),
            'patterns attest %s %s owner' % (OWN_HAS, f[1]),
            'patterns approve ' + OWN_HAS])
        assert 'A07' in o and 'approve refused' in o
        # 5. forged coverage and bad files
        def forge(r):
            r['coverage']['tests_hash'] = '0' * 16

        def trunc(r):
            r['coverage']['truncated'] = True
        d, o = scenario('forged', lambda d: [
            att(d, out0, 'fa', 'run1', 'dep1', tweak=forge),
            att(d, out0, 'fb', 'run2', 'dep2'),
            att(d, out0, 'fc', 'run3', 'dep3', tweak=trunc)], lambda f: [
            'patterns attest %s %s owner' % (OWN_HAS, f[0]),
            'patterns attest %s %s owner' % (OWN_HAS, f[1]),
            'patterns attest %s %s owner' % (OWN_HAS, f[2]),
            'patterns approve ' + OWN_HAS])
        assert 'A04' in o and 'E04' in o and 'approve refused' in o
        # 6. conflict -> owner review; owner cannot override technical
        d, o = scenario('conf', lambda d: two(d) + [
            att(d, out0, 'fc', 'run3', 'dep3', 'reject')], lambda f: [
            'patterns attest %s %s owner' % (OWN_HAS, f[0]),
            'patterns attest %s %s owner' % (OWN_HAS, f[1]),
            'patterns attest %s %s owner' % (OWN_HAS, f[2]),
            'patterns approve ' + OWN_HAS,
            'patterns owner %s approve' % OWN_HAS])
        assert 'A08' in o and 'PENDING_OWNER_REVIEW' in o
        assert 'owner approved ' + OWN_HAS in o
        d, o = scenario('conf2', lambda d: [
            att(d, out0, 'fa', 'run1', 'dep1'),
            att(d, out0, 'fc', 'run3', 'dep3', 'reject')], lambda f: [
            'patterns attest %s %s owner' % (OWN_HAS, f[0]),
            'patterns attest %s %s owner' % (OWN_HAS, f[1]),
            'patterns approve ' + OWN_HAS,
            'patterns owner %s approve' % OWN_HAS])
        assert 'cannot override technical failures' in o
        # 7. lineage: agent may only propose; verified mirror collapses
        d, o = scenario('lin', lambda d: [], lambda f: [
            'patterns lineage o0 o1 mirror verified agent',
            'patterns lineage o0 o1 mirror proposed agent', RV,
            'patterns lineage o0 o1 mirror verified owner', RV,
            'patterns lineage o2 o3 aggregation verified owner', RV,
            'patterns lineage o4 o0 repost disputed owner', RV])
        assert 'refused: only the owner or documented' in o
        assert o.count('verified origins: 5') == 1
        assert o.count('verified origins: 4') == 3   # aggregation: no merge
        assert 'disputed lineage edge' in o
        hs = re.findall(r'snapshot hash: ([0-9a-f]{16})', o)
        assert len(set(hs)) == len(hs) or hs[0] != hs[1]
        # 8. delegation versioning and revoked delegation
        d, o = scenario('delv', lambda d: [], lambda f: [
            'patterns delegate del.json'])
        assert 'version must increase' in o
        # 9. reader isolation with reviewed state present
        reader = ['remember a sparrow is a bird',
                  'read m1: a crow owns a nest. a kiwi is a bird',
                  'readings', 'is a sparrow a bird', 'quit']
        e2 = td / 'empty'
        e2.mkdir()
        ra = run(argv, reader, td / 'ok', env)
        rb = run(argv, reader, e2, env)
        assert ra == rb, 'reader changed by review state'
        print('ok %s: delegated review gate scenarios' % label)
        return res


def main():
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    ia = suite('interp', [sys.executable, str(ROOT / 'interp.py'),
                          str(ROOT / 'agent' / 'repl.holy')], env)
    with tempfile.TemporaryDirectory() as td:
        img = Path(td) / 'repl'
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build',
                            str(ROOT / 'agent' / 'repl.holy'), '-o',
                            str(img)], capture_output=True, text=True,
                           env=env)
        assert r.returncode == 0, r.stderr[-400:]
        na = suite('native', [str(img)], env)
    assert ia == na, 'native differs from interp'
    print('ok native == interp (review transcripts)')
    print('all agent review tests passed')


if __name__ == '__main__':
    main()
