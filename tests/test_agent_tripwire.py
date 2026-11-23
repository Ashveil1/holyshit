#!/usr/bin/env python3
"""A22.2 tripwire / quarantine state machine tests (interp and native).

T1 one owner-confirmed polarity error disables at once; T2 two confirmed
ordinary FPs in the rolling window quarantine provisionally; dual AI
reviewers may only impose a TEMP quarantine and cannot confirm an FP; the
owner lifts and reactivation still needs fresh review; lifetime counters
survive a lift; a corrupt tripwire file fails closed; forget/teach events
are classified and only an explicit correction opens an (unconfirmed)
investigation; the review packet shows registry/tripwire status.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_review as rv
import test_agent_learned as lt
from test_agent_shadow import run, OWN_HAS

READ = lt.READ
ACT = 'patterns activate ' + OWN_HAS
FPF = 'patterns fp %s a_finch has a_nest owner' % OWN_HAS
FPW = 'patterns fp %s a_wren has a_nest owner' % OWN_HAS


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        base = td / 'base'
        out0 = rv.build(base, argv, env)
        lt.make(base, argv, env, out0)
        outs = {}

        def sc(name, cmds, pre=None):
            d = td / name
            shutil.copytree(base, d)
            if pre:
                pre(d)
            o = run(argv, list(cmds) + ['quit'], d, env)
            outs[name] = o
            return d, o

        # no active pattern: no tripwire file is ever written
        d, o = sc('idle', [READ, 'no, a finch owns a branch'])
        assert not (d / 'agent-tripwire.json').exists()
        # T2: two confirmed FPs quarantine; leaves use in the same session
        d, o = sc('t2', [ACT, READ, FPF, FPW, 'read z3: a lark owns a nest',
                         'patterns learned', 'patterns tripwire',
                         'patterns lift %s owner reviewed the two FPs'
                         % OWN_HAS, 'patterns tripwire', ACT])
        assert '1 of 2 in the rolling window of 200' in o, o[-900:]
        assert 'QUARANTINED_PROVISIONAL, pattern leaves use at once' in o
        assert 'learned pattern %s disabled: L14 tripwire ' \
            'QUARANTINED_PROVISIONAL' % OWN_HAS in o
        assert 'FP lifetime 2 (window 2)' in o
        assert 'owner lifted QUARANTINED_PROVISIONAL' in o
        assert 'FP lifetime 2 (window 0)' in o        # lifetime kept
        assert 'activate refused: state REVIEW_PENDING' in o
        # T1: one polarity error disables immediately
        d, o = sc('t1', [ACT, READ, 'patterns polarity-error %s owner'
                         % OWN_HAS, 'read z4: a lark owns a nest',
                         'patterns tripwire'])
        assert 'DISABLED_POLARITY, leaves use at once' in o
        assert 'L14 tripwire DISABLED_POLARITY' in o
        assert 'polarity errors 1' in o
        # reviewers: two distinct = TEMP quarantine; cannot confirm FP
        d, o = sc('rev', [ACT, READ, 'patterns quarantine %s ai_a' % OWN_HAS,
                          'patterns quarantine %s ai_a' % OWN_HAS,
                          'patterns quarantine %s ai_b' % OWN_HAS,
                          'patterns fp %s a_finch has a_nest' % OWN_HAS,
                          'patterns fp %s a_finch has a_nest ai_a' % OWN_HAS,
                          'patterns tripwire'])
        assert '1 of 2 needed' in o and 'already reported' in o
        assert 'TEMP_QUARANTINE: two distinct reviewers' in o
        assert o.count('only the owner confirms a false positive') == 2
        assert 'FP lifetime 0' in o and 'L14 tripwire TEMP_QUARANTINE' in o
        # corrupt tripwire file fails closed with an ACTIVE pattern
        d, o = sc('corrupt', [ACT, READ])
        (d / 'agent-tripwire.json').write_text('{garbage')
        o2 = run(argv, ['patterns manifest accept',
                        'read z5: a lark owns a nest', 'patterns learned',
                        'quit'], d, env)
        assert 'L14 tripwire state unreadable' in o2, o2[-500:]
        # classification: only an explicit correction opens an investigation
        d, o = sc('cls', [ACT, READ, 'remember rex is a dog',
                          'forget rex', 'no, a finch owns a branch',
                          'patterns tripwire'])
        assert 'open correction investigations: 1' in o, o[-700:]
        assert 'privacy_forget 1' in o and 'correction 1' in o
        assert 'addition 1' in o and 'FP lifetime 0' in o
        # review packet surfaces registry + tripwire status (read-only)
        d, o = sc('pkt', ['patterns predicate has bird nest',
                          'patterns review ' + OWN_HAS])
        assert 'A22 read-only status (display only, not a gate):' in o
        assert 'predicate has signature (bird, nest)' in o
        assert 'tripwire CLEAR' in o
        print('ok %s: T1/T2 tripwires, reviewer-only temp quarantine, '
              'owner lift, fail-closed file, event classes, packet status'
              % label)
        return {k: v for k, v in outs.items()}


def main():
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    ia = na = None
    if which in ('both', 'interp'):
        ia = suite('interp', [sys.executable, str(ROOT / 'interp.py'),
                              str(ROOT / 'agent' / 'repl.holy')], env)
    if which in ('both', 'native'):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / 'repl'
            r = subprocess.run([sys.executable, str(ROOT / 'hs.py'),
                                'build', str(ROOT / 'agent' / 'repl.holy'),
                                '-o', str(img)], capture_output=True,
                               text=True, env=env)
            assert r.returncode == 0, r.stderr[-400:]
            na = suite('native', [str(img)], env)
    if ia and na:
        assert ia == na, 'native differs from interp'
        print('ok native == interp (tripwire transcripts)')
    print('all agent tripwire tests passed')


if __name__ == '__main__':
    main()
