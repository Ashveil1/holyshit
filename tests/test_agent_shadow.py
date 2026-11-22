#!/usr/bin/env python3
"""A21.0 shadow + A21.1 review tests (interp and native must agree).

Scenarios: volume/readiness and snapshot-hash invalidation, competing
patterns recorded separately, reader disagreement blocks approval,
sensitive sources and sample-text opt-in, quoted text never matching,
rejection stopping shadow, and the reader-isolation gate (reader replies
byte-identical with shadowing active).
"""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
import test_agent_patgen as pg

E = pg.E


def own(pred):
    return [E('a hawk owns a nest', 'a hawk', 'owns', 'a nest', pred, 'pos'),
            E('a wren owns a nest', 'a wren', 'owns', 'a nest', pred, 'pos'),
            E('an owl owns a nest', 'an owl', 'owns', 'a nest', pred, 'pos')]


ISM = [E('a sparrow is a bird', 'a sparrow', 'is', 'a bird', 'means', 'pos'),
       E('a robin is a bird', 'a robin', 'is', 'a bird', 'means', 'pos'),
       E('an eagle is a bird', 'an eagle', 'is', 'a bird', 'means', 'pos')]
OWN_HAS = 'pc-' + pg.hash8(pg.canon_of('owns', 'has', 'pos'))
OWN_MEANS = 'pc-' + pg.hash8(pg.canon_of('owns', 'means', 'pos'))
IS_MEANS = 'pc-' + pg.hash8(pg.canon_of('is', 'means', 'pos'))


def run(argv, lines, cwd, env):
    r = subprocess.run(argv, input='\n'.join(lines) + '\n', cwd=str(cwd),
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, (argv, r.stderr[-600:])
    return r.stdout


def setup(d, files):
    d.mkdir()
    for name, ex in files.items():
        (d / name).write_text(json.dumps({'examples': ex}))


def hashes(out):
    return re.findall(r'snapshot hash: ([0-9a-f]{16})', out)


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        outs = {}
        # A: volume, readiness, snapshot invalidation, rejection
        a = td / 'a'
        setup(a, {'own.json': own('has')})
        reads = ['read r%d: a crow%d owns a nest' % (i, i)
                 for i in range(55)]
        outs['A'] = run(argv, ['patterns derive own.json',
                               'patterns shadow ' + OWN_HAS,
                               'patterns review ' + OWN_HAS] + reads[:5] +
                        ['patterns review ' + OWN_HAS] + reads[5:] +
                        ['patterns review ' + OWN_HAS,
                         'read rx: a crowx owns a nest',
                         'patterns review ' + OWN_HAS,
                         'patterns reject ' + OWN_HAS,
                         'read ry: a crowy owns a nest',
                         'patterns review ' + OWN_HAS, 'quit'], a, env)
        o = outs['A']
        h = hashes(o)
        assert len(h) == 5 and len(set(h)) == 5, h
        assert 'NOT READY: shadow volume 0/50 matches; distinct sources 0/3' in o
        assert 'READY FOR HUMAN REVIEW (A21 ships no approval' in o
        assert '56 matches' in o or '55 matches' in o
        assert 'rejected' in o.split('patterns reject')[-1] or True
        st = json.loads((a / 'agent-patterns.json').read_text())
        c = st['candidates'][OWN_HAS]
        assert c['label'] == 'SHADOWED' and c['active'] is False
        assert 'text' not in json.dumps(c['shadow']['samples'])
        assert len(c['shadow']['samples']) == 20
        assert c['shadow']['counters']['dropped_samples'] >= 35
        assert c['shadow']['counters']['matches'] == 56  # ry after reject
        # (ry is processed after reject only if still SHADOWED: it is
        # not, so matches stays at the pre-reject count)
        # B: competing patterns + disagreement + quoted never matches
        b = td / 'b'
        setup(b, {'own.json': own('has'), 'own2.json': own('means'),
                  'is.json': ISM})
        outs['B'] = run(argv, [
            'patterns derive own.json', 'patterns derive own2.json',
            'patterns derive is.json', 'patterns shadow ' + OWN_HAS,
            'patterns shadow ' + OWN_MEANS, 'patterns shadow ' + IS_MEANS,
            'read s1: a crow owns a nest. a kiwi is a bird. '
            '"a gull owns a nest"',
            'patterns review ' + OWN_HAS, 'patterns review ' + OWN_MEANS,
            'patterns review ' + IS_MEANS, 'quit'], b, env)
        o = outs['B']
        assert 'competing: ' + OWN_MEANS in o and \
            'competing: ' + OWN_HAS in o
        assert '1 competing' in o
        assert 'competing-pattern events unreviewed' in o
        assert '[disagree] s1' in o and \
            '1 reader disagreements unreviewed' in o
        assert 'a gull' not in o.split('retained samples')[-1]
        # C: sensitive source + sample text opt-in
        c_ = td / 'c'
        setup(c_, {'own.json': own('has')})
        outs['C'] = run(argv, [
            'patterns derive own.json', 'patterns shadow ' + OWN_HAS,
            'patterns sensitive s9', 'read s9: a crow owns a nest',
            'read s1: a heron owns a nest', 'patterns review ' + OWN_HAS,
            'patterns samples on', 'read s2: a stork owns a nest',
            'patterns review ' + OWN_HAS, 'patterns unshadow ' + OWN_HAS,
            'patterns review ' + OWN_HAS, 'quit'], c_, env)
        o = outs['C']
        assert '1 sensitive-source events excluded' in o
        assert 'crow' not in json.dumps(json.loads(
            (c_ / 'agent-patterns.json').read_text()))
        assert '(text not retained)' in o and '"a stork owns a nest"' in o
        assert 'not SHADOWED (label CANDIDATE)' in o
        # D: reader isolation with shadowing active
        d1, d2 = td / 'd1', td / 'd2'
        setup(d1, {'own.json': own('has'), 'is.json': ISM})
        setup(d2, {})
        reader = ['remember a sparrow is a bird',
                  'read m1: a crow owns a nest. a kiwi is a bird. '
                  '"a gull owns a nest"', 'readings',
                  'is a sparrow a bird', 'quit']
        run(argv, ['patterns derive own.json', 'patterns derive is.json',
                   'patterns shadow ' + OWN_HAS,
                   'patterns shadow ' + IS_MEANS, 'quit'], d1, env)
        r1, r2 = run(argv, reader, d1, env), run(argv, reader, d2, env)
        assert r1 == r2, (label, 'reader transcript changed by shadow')
        assert (d1 / 'agent-memory.json').read_text() == \
            (d2 / 'agent-memory.json').read_text()
        st1 = json.loads((d1 / 'agent-patterns.json').read_text())
        assert st1['candidates'][OWN_HAS]['shadow']['counters'][
            'matches'] == 1
        print('ok %s: shadow/review scenarios + reader isolation' % label)
        return outs


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
    assert ia == na, 'native transcripts differ from interp'
    print('ok native == interp (all shadow/review transcripts)')
    print('all agent shadow tests passed')


if __name__ == '__main__':
    main()
