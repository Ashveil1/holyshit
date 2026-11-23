#!/usr/bin/env python3
"""A21.2b activation + fail-closed loader tests (interp and native).

An approved pattern is activated; its readings appear only in the
learned-readings section, never in `readings`; every loader failure
disables the pattern at the next command and keeps the approval in
history; revocation is immediate; the reader transcript with no ACTIVE
pattern is byte-identical to a run with no proposals files at all.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_review as rv
from test_agent_shadow import run, OWN_HAS

READ = 'read z1: a finch owns a nest. a wren owns a nest. a kiwi is a bird'


def make(base, argv, env, out0):
    f = [rv.att(base, out0, 'fa', 'run1', 'dep1'),
         rv.att(base, out0, 'fb', 'run2', 'dep2')]
    rv.deleg(base)
    o = run(argv, ['patterns manifest accept', 'patterns delegate del.json'] +
            ['patterns attest %s %s owner' % (OWN_HAS, x) for x in f] +
            ['patterns approve ' + OWN_HAS, 'quit'], base, env)
    assert 'approved ' + OWN_HAS in o, o[-600:]


def edit(d, fn):
    p = d / 'agent-patterns.json'
    st = json.loads(p.read_text())
    fn(st['candidates'][OWN_HAS])
    p.write_text(json.dumps(st))


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        base = td / 'base'
        out0 = rv.build(base, argv, env)
        make(base, argv, env, out0)
        res = {}

        def sc(name, pre=None, cmds=()):
            d = td / name
            shutil.copytree(base, d)
            if pre:
                pre(d)
            o = run(argv, list(cmds) + ['quit'], d, env)
            res[name] = o
            return d, o
        act = 'patterns activate ' + OWN_HAS
        # activation refused before approval / on a stale snapshot
        d, o = sc('early', None, [
            'patterns lineage o4 o0 repost disputed owner',
            'patterns review ' + OWN_HAS, act])
        assert 'activate refused: state REVIEW_PENDING' in o
        # activate + use + revoke
        d, o = sc('use', None, [act, READ, 'readings', 'patterns learned',
                                'patterns revoke ' + OWN_HAS,
                                'read z2: a lark owns a nest',
                                'patterns learned'])
        assert 'activated ' + OWN_HAS in o
        assert '2 learned-pattern readings recorded (LEARNED_PATTERN' in o
        assert 'a finch | has | a nest via ' + OWN_HAS + \
            ' [ACTIVE]' in o
        assert 'a kiwi | is-a | a bird' in o   # handwritten reader wins
        assert 'finch' not in o.split('read candidate')[1].split(
            'learned-pattern readings this session')[0]
        assert ('[REVOKED]' in o)           # current status shown
        assert '0 learned-pattern readings recorded' not in o
        assert 'z2: 1 segments in' in o and \
            'z2: 1 segments in, 0 pattern matches, 0 candidates extracted' in o
        tail = o.split('read z2')[-1] if 'read z2' in o else o
        assert o.count('learned-pattern readings recorded') == 1  # z2: none
        lg = json.loads((d / 'agent-learned-log.json').read_text())
        assert lg['total'] == 2 and lg['entries'][0]['pattern'] == OWN_HAS
        assert 'text' not in json.dumps(lg)
        st = json.loads((d / 'agent-patterns.json').read_text())
        c = st['candidates'][OWN_HAS]
        assert c['label'] == 'REVOKED' and c['active'] is False
        assert c['approval']['hash']      # approval history kept
        # loader failures disable at the next command
        def bad_hash(d):
            edit(d, lambda c: c['approval'].update(hash='0' * 16))
        acc = 'patterns manifest accept'
        d, o = sc('stale', lambda d: (run(argv, [act, 'quit'], d, env),
                                      bad_hash(d)), [acc, READ])
        assert 'disabled: L09' in o and 'learned-pattern readings' not in o.split('disabled')[-1]
        st = json.loads((d / 'agent-patterns.json').read_text())
        c = st['candidates'][OWN_HAS]
        assert c['label'] == 'REVIEW_PENDING' and c['active'] is False
        assert len(c['approval_history']) == 1
        assert any('DISABLED by loader' in x
                   for x in c['provenance']['history'])

        def bad_verb(d):
            edit(d, lambda c: c['descriptor'].update(verb='owns owns'))
        d, o = sc('canon', lambda d: (run(argv, [act, 'quit'], d, env),
                                      bad_verb(d)), [acc, READ])
        assert 'disabled: L03' in o

        def revoke_del(d):
            x = json.loads((d / 'del.json').read_text())
            x.update(version=2, revoked=True)
            (d / 'del2.json').write_text(json.dumps(x))
        d, o = sc('deleg', lambda d: (run(argv, [act, 'quit'], d, env),
                                      revoke_del(d)),
                  [acc, 'patterns delegate del2.json', READ])
        assert 'disabled: L12' in o
        # manifest: an outside edit stops learned loading until accepted
        d, o = sc('manifest', lambda d: (run(argv, [act, 'quit'], d, env),
                                         bad_hash(d)), [READ, acc, READ])
        assert 'integrity: ' in o and 'changed outside the repl' in o
        first = o.split('manifest accepted')[0]
        assert 'learned-pattern readings recorded' not in first
        assert 'disabled: L09' in o.split('manifest accepted')[1]
        # hash-algorithm mismatch: approval predates the algorithm
        def old_algo(d):
            edit(d, lambda c: c['approval'].update(hash_algo='md5'))
        d, o = sc('algo', lambda d: (run(argv, [act, 'quit'], d, env),
                                     old_algo(d)), [acc, READ])
        assert 'disabled: L13' in o
        # changed provenance after activation: stale at next command
        d, o = sc('graph', lambda d: run(argv, [act, 'quit'], d, env), [
            'patterns lineage o4 o0 repost disputed owner', READ])
        assert 'disabled: L09' in o
        # reader isolation: no ACTIVE pattern => identical to no files
        e2 = td / 'empty'
        e2.mkdir()
        reader = ['remember a sparrow is a bird', READ, 'readings',
                  'is a sparrow a bird', 'quit']
        ra = run(argv, reader, td / 'revoked_probe', env) \
            if (td / 'revoked_probe').exists() else None
        d = td / 'iso'
        shutil.copytree(base, d)
        ia = run(argv, reader, d, env)          # approved, not active
        ib = run(argv, reader, e2, env)
        assert ia == ib, 'approved-but-inactive pattern changed the reader'
        assert (d / 'agent-memory.json').read_text() == \
            (e2 / 'agent-memory.json').read_text()
        # active pattern: reader replies identical except the appended
        # learned suffix; memory file byte-identical
        d3 = td / 'iso2'
        shutil.copytree(base, d3)
        run(argv, [act, 'quit'], d3, env)
        e3 = td / 'empty3'
        e3.mkdir()
        i3 = run(argv, reader, d3, env)
        b3 = run(argv, reader, e3, env)
        strip = re.sub(r'; \d+ learned-pattern readings recorded \(.*?\)',
                       '', i3)
        assert strip == b3, 'active pattern changed reader beyond suffix'
        assert (d3 / 'agent-memory.json').read_text() == \
            (e3 / 'agent-memory.json').read_text()
        print('ok %s: activation, fail-closed loader, revocation, isolation'
              % label)
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
    print('ok native == interp (learned transcripts)')
    print('all agent learned tests passed')


if __name__ == '__main__':
    main()
