#!/usr/bin/env python3
"""A22.1 predicate/type registry tests (interp and native).

Only verified, unambiguous type evidence raises TYPE_MISMATCH; declared
and inferred disagreement is an unflagged suspicion; several verified
types are ambiguous and not flagged; unknown stays unknown. The registry
never changes reader output or agent-memory.json: transcripts are
byte-identical with the registry absent, present and corrupt.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEACH = ['remember paris is in france', 'remember berlin is in germany',
         'remember rex is a dog']
READER = TEACH + ['paris is in what', 'readings', 'is rex a dog', 'quit']
AUDIT = TEACH + [
    'patterns predicate is-in city country',
    'patterns predicate is-a animal any',
    'patterns type paris city verified',
    'patterns type france country verified',
    'patterns type berlin planet verified',
    'patterns type germany country declared',
    'patterns type germany planet inferred',
    'patterns type rex dog verified',
    'patterns type rex cat verified',
    'patterns type rex cat verified',
    'patterns type rex cat bogus',
    'patterns predicate Bad!Name a b',
    'patterns registry', 'patterns typecheck', 'quit']


def run(argv, lines, cwd, env):
    r = subprocess.run(argv, input='\n'.join(lines) + '\n', cwd=str(cwd),
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, (argv, r.stderr[-600:])
    return r.stdout


def mem(d):
    p = Path(d) / 'agent-memory.json'
    return p.read_text(encoding='utf-8') if p.exists() else ''


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a = td / 'audit'
        a.mkdir()
        o = run(argv, AUDIT, a, env)
        assert o.count('TYPE_MISMATCH  berlin | is-in | germany') == 1, o
        assert 'TYPE_MISMATCH' in o and o.count('TYPE_MISMATCH  ') == 1
        assert '1 TYPE_MISMATCH (verified evidence only), 1 unverified ' \
            'suspicion(s), 1 ambiguous argument(s) not flagged' in o, o
        assert 'suspect (not verified, not flagged)  berlin | is-in | ' \
            'germany (object germany' in o
        assert 'type evidence already recorded' in o
        assert 'type refused: class must be' in o
        assert 'predicate refused' in o
        assert 'rex: declared [] inferred [] verified [dog, cat]' in o
        reg = json.loads((a / 'agent-registry.json').read_text())
        assert reg['hash_algo'] == 'poly62' and reg['version'] == 1
        # isolation: reader output and memory identical in every state
        dirs = {k: td / k for k in ('absent', 'present', 'corrupt',
                                    'badshape')}
        for d in dirs.values():
            d.mkdir()
        (dirs['present'] / 'agent-registry.json').write_text(
            json.dumps(reg))
        (dirs['corrupt'] / 'agent-registry.json').write_text('{garbage')
        (dirs['badshape'] / 'agent-registry.json').write_text(
            json.dumps({'version': 1, 'predicates': {'x': {'subj': 1}}}))
        outs = {k: run(argv, READER, d, env) for k, d in dirs.items()}
        ref = outs['absent']
        for k, out in outs.items():
            assert out == ref, (label, k, 'reader transcript changed')
            assert mem(dirs[k]) == mem(dirs['absent']), (label, k)
            assert 'registry' not in mem(dirs[k]).lower()
        # corrupt/badshape files load as an empty registry, audit is clean
        for k in ('corrupt', 'badshape'):
            t = run(argv, TEACH + ['patterns typecheck', 'quit'],
                    dirs[k], env)
            assert '0 edge(s) with a declared signature, 0 TYPE_MISMATCH' \
                in t, (k, t[-300:])
        # the memory file never records the registry
        assert 'registry' not in mem(a).lower()
        print('ok %s: only verified unambiguous evidence raises '
              'TYPE_MISMATCH; reader byte-identical with registry '
              'absent/present/corrupt/bad-shape' % label)
    return o


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
    assert ia == na, 'native and interp transcripts differ'
    print('ok native == interp (registry transcripts)')
    print('all agent registry tests passed')


if __name__ == '__main__':
    main()
