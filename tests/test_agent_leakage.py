#!/usr/bin/env python3
"""A22.4 leakage guard tests (interp and native).

Immutable sequence cutoffs at derivation and shadow start; sources first
seen at or before the shadow cutoff are excluded unless declared held out
before derivation; text equal to a derivation example never counts as
validation; a re-derive after the shadow cutoff changes no evidence input;
a derivation example whose text appears in the learned-pattern log is
refused as circular learning.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_agent_shadow import run, setup, own, OWN_HAS

RV = 'patterns review ' + OWN_HAS
DER = 'patterns derive own.json'
SHD = 'patterns shadow ' + OWN_HAS


def matches(o):
    return int(re.findall(r'shadow lifetime: (\d+) matches', o)[-1])


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        base = td / 'base'
        setup(base, {'own.json': own('has')})

        def sc(name, cmds, pre=None):
            d = td / name
            shutil.copytree(base, d)
            if pre:
                pre(d)
            return d, run(argv, list(cmds) + ['quit'], d, env)
        # cutoffs are immutable across unshadow / re-shadow / re-derive
        d, o = sc('cut', [DER, SHD, RV, 'patterns unshadow ' + OWN_HAS,
                          SHD, DER, RV])
        assert o.count('derive_seq 1, shadow_seq 2') == 2, o[-1500:]
        assert 're-derived after the shadow cutoff: evidence inputs ' \
            'unchanged' not in o  # history is not printed, check the file
        st = json.loads((d / 'agent-patterns.json').read_text())
        c = st['candidates'][OWN_HAS]
        assert c['cutoffs'] == {'derive_seq': 1, 'shadow_seq': 2,
                                'legacy': False}, c['cutoffs']
        assert any('re-derived after the shadow cutoff' in h
                   for h in c['provenance']['history'])
        # pre-shadow source excluded, post-shadow source counted
        d, o = sc('pre', [DER, 'read pre1: a finch owns a nest'])
        o = run(argv, [SHD, 'read pre1: a lark owns a nest',
                       'read post1: a robin owns a nest', RV, 'quit'], d, env)
        assert matches(o) == 1, o[-1200:]
        assert 'excluded 1 pre-shadow-source segment(s)' in o
        # held-out declared before derivation is allowed
        d, o = sc('ho', ['patterns holdout h1 owner', DER,
                         'read h1: a finch owns a nest'])
        o = run(argv, [SHD, 'read h1: a lark owns a nest',
                       'patterns holdout pre1 owner', RV, 'quit'], d, env)
        assert matches(o) == 1, o[-1200:]
        assert 'excluded 0 pre-shadow-source segment(s)' in o
        assert 'held-out source h1 declared' not in o
        assert (d / 'agent-patterns.json').exists()
        # a source already seen cannot be declared held out afterwards
        d, o = sc('late', [DER, 'read s1: a finch owns a nest',
                           'patterns holdout s1 owner',
                           'patterns holdout s1'])
        assert 'must be declared before it is read' in o
        # text equal to a derivation example is never validation
        d, o = sc('txt', [DER, SHD, 'read t1: a hawk owns a nest',
                          'read t2: a finch owns a nest', RV])
        assert matches(o) == 1, o[-1200:]
        assert '1 segment(s) equal to a derivation example' in o
        # circular learning: example text present in the learned log
        def circ(d):
            (d / 'agent-learned-log.json').write_text(json.dumps(
                {'version': 1, 'total': 1, 'sensitive': 0, 'dropped': 0,
                 'entries': [{'pattern': 'pc-x', 'subject': 'a hawk',
                              'predicate': 'has', 'object': 'a nest',
                              'source': 's', 'ambiguous': False,
                              'text': 'a hawk owns a nest'}]}))
        d, o = sc('circ', [DER, 'patterns list'], circ)
        assert 'circular learning' in o, o[-800:]
        assert 'verb \'owns\' has 2 annotated example(s)' in o, o[-800:]
        print('ok %s: immutable cutoffs, pre-shadow exclusion, held-out '
              'rule, derived-text exclusion, circular-learning refusal'
              % label)


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
    print('all agent leakage tests passed')


if __name__ == '__main__':
    main()
