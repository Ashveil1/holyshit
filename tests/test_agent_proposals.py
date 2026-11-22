#!/usr/bin/env python3
"""A20 proposal-store + repl command tests, and the reader-isolation gate.

Isolation: the same reader session (teach, read, readings, questions)
is run with the proposals file ABSENT, PRESENT (candidates stored) and
REJECTED (candidates stored then rejected), and with a CORRUPT file.
The transcripts and agent-memory.json must be byte-identical. Runs on
the interp and the full native route.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_patgen as pg

OWN = [pg.E('a hawk owns a nest', 'a hawk', 'owns', 'a nest', 'has', 'pos'),
       pg.E('a wren owns a nest', 'a wren', 'owns', 'a nest', 'has', 'pos'),
       pg.E('an owl owns a nest', 'an owl', 'owns', 'a nest', 'has', 'pos')]
ANNOT = {'examples': OWN, 'corpus': ['a crow owns a nest'],
         'negatives': ['a crow owns']}
CID = 'pc-' + pg.hash8(pg.canon_of('owns', 'has', 'pos'))
READER = ['remember a sparrow is a bird',
          'read m1: a hawk owns a nest. a bicycle is a vehicle',
          'readings', 'is a sparrow a bird', 'quit']
MGMT = ['patterns derive annot.json', 'patterns list',
        'patterns derive annot.json',
        'patterns reject ' + CID, 'patterns derive annot.json',
        'patterns list', 'patterns reopen ' + CID,
        'patterns retract A Wren owns a nest', 'patterns list',
        'patterns derive annot.json', 'patterns bogus', 'quit']


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
        dirs = {k: td / k for k in ('absent', 'present', 'rejected',
                                    'corrupt', 'mgmt')}
        for d in dirs.values():
            d.mkdir()
            (d / 'annot.json').write_text(json.dumps(ANNOT))
        # management transcript (store behaviour)
        out = run(argv, MGMT, dirs['mgmt'], env)
        assert '1 pattern candidates (INACTIVE' in out, out[:600]
        assert CID in out and 'no held-out coverage' in out
        assert 'skipped ' + CID in out and 'stays rejected' in out
        assert 'reopened ' + CID in out
        assert '1 candidate(s) marked STALE' in out
        assert 'STALE, inactive' in out and 'APPROVAL BLOCKED' in out
        assert 'stays STALE' in out
        assert 'patterns: list | derive FILE' in out
        store = json.loads((dirs['mgmt'] / 'agent-patterns.json').read_text())
        assert store['version'] == 1 and store['rejected'] == []
        c = store['candidates'][CID]
        assert c['active'] is False and c['label'] == 'STALE'
        assert c['provenance']['history'][0] == 'derived'
        assert c['provenance']['history'][-1] == 're-derived'
        assert 'stale: example retracted' in c['provenance']['history']
        # isolation: build proposal files, then run the same reader session
        run(argv, ['patterns derive annot.json', 'quit'],
            dirs['present'], env)
        run(argv, ['patterns derive annot.json', 'patterns reject ' + CID,
                   'quit'], dirs['rejected'], env)
        (dirs['corrupt'] / 'agent-patterns.json').write_text('{garbage')
        assert (dirs['present'] / 'agent-patterns.json').exists()
        outs = {k: run(argv, READER, d, env) for k, d in dirs.items()
                if k != 'mgmt'}
        ref = outs['absent']
        for k, o in outs.items():
            assert o == ref, (label, k, 'reader transcript changed')
            assert mem(dirs[k]) == mem(dirs['absent']), (label, k)
            assert 'pattern' not in mem(dirs[k]).lower(), (label, k)
        print('ok %s: store behaviour + reader byte-identical with '
              'proposals absent/present/rejected/corrupt' % label)


def main():
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    suite('interp', [sys.executable, str(ROOT / 'interp.py'),
                     str(ROOT / 'agent' / 'repl.holy')], env)
    with tempfile.TemporaryDirectory() as td:
        img = Path(td) / 'repl'
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build',
                            str(ROOT / 'agent' / 'repl.holy'), '-o',
                            str(img)], capture_output=True, text=True,
                           env=env)
        assert r.returncode == 0, r.stderr[-400:]
        suite('native', [str(img)], env)
    print('all agent proposal tests passed')


if __name__ == '__main__':
    main()
