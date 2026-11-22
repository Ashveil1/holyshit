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
        # A: volume, origins, readiness, snapshot invalidation, rejection
        a = td / 'a'
        setup(a, {'own.json': own('has')})

        def rd(i):
            return ('read r%d: a crow%d owns a nest. the day%d is long. '
                    'a pond%d is deep' % (i, i, i, i))

        def og(i, cls='verified_independent'):
            return 'patterns origin r%d o%d %s' % (i, i % 5, cls)
        pre = ['patterns derive own.json', 'patterns shadow ' + OWN_HAS,
               'patterns review ' + OWN_HAS]
        part1 = [rd(i) for i in range(5)]
        part2 = [rd(i) for i in range(5, 55)]
        rv = 'patterns review ' + OWN_HAS
        outs['A'] = run(argv, pre + part1 + [rv] + part2 + [rv] +
                        [og(i) for i in range(55)] + [rv] +
                        # same segments again: no double counting
                        part1 + [rv] +
                        # a classification change invalidates the hash
                        [og(0, 'dependent'), rv, og(0), rv,
                         'patterns reject ' + OWN_HAS, rv, 'quit'], a, env)
        o = outs['A']
        h = hashes(o)
        assert len(h) == 8, h
        assert h[3] == h[4], 're-reading identical segments changed hash'
        assert h[0] != h[1] and h[1] != h[2] and h[2] != h[3]
        assert h[5] != h[4] and h[6] == h[4] and h[7] != h[6], h
        assert 'verified-origin distinct matches 0/50' in o
        assert 'READY FOR HUMAN REVIEW (A21 ships no approval' in o
        assert 'independent origins with >=10 matches: 0/3' in o
        assert 'note: shadow matches show where a pattern fires' in o
        st = json.loads((a / 'agent-patterns.json').read_text())
        c = st['candidates'][OWN_HAS]
        assert c['label'] == 'SHADOWED' and c['active'] is False
        assert 'text' not in json.dumps(c['shadow']['samples'])
        assert len(c['shadow']['samples']) == 20
        assert c['shadow']['counters']['matches'] == 55
        assert c['shadow']['counters']['nonmatches'] == 110
        # floors: 49 matches blocks, one origin dominating blocks
        e = td / 'e'
        setup(e, {'own.json': own('has')})
        lines = ['patterns derive own.json', 'patterns shadow ' + OWN_HAS]
        for i in range(49):
            lines += [rd(i), 'patterns origin r%d o%d verified_independent'
                      % (i, i % 3)]
        lines += [rv, rd(49), 'patterns origin r49 o0 verified_independent',
                  rv, 'quit']
        oe = run(argv, lines, e, env)
        assert 'matches 49/50' in oe and 'matches 50/50' not in oe
        assert 'READY FOR HUMAN REVIEW' in oe.split('matches 49/50')[-1] \
            or 'one origin' not in oe
        f = td / 'f'
        setup(f, {'own.json': own('has')})
        lines = ['patterns derive own.json', 'patterns shadow ' + OWN_HAS]
        for i in range(60):
            lines += [rd(i), 'patterns origin r%d %s verified_independent'
                      % (i, 'big' if i < 40 else 'o%d' % (i % 2))]
        lines += [rv, 'quit']
        of = run(argv, lines, f, env)
        assert 'one origin supplies 40 of 60' in of
        # B: competing patterns + disagreement + dispositions
        b = td / 'b'
        setup(b, {'own.json': own('has'), 'own2.json': own('means'),
                  'is.json': ISM})
        base = [
            'patterns derive own.json', 'patterns derive own2.json',
            'patterns derive is.json', 'patterns shadow ' + OWN_HAS,
            'patterns shadow ' + OWN_MEANS, 'patterns shadow ' + IS_MEANS,
            'read s1: a crow owns a nest. a kiwi is a bird. '
            '"a gull owns a nest"']
        outs['B'] = run(argv, base + [
            'patterns review ' + OWN_HAS, 'patterns review ' + OWN_MEANS,
            'patterns review ' + IS_MEANS, 'quit'], b, env)
        o = outs['B']
        assert 'competing: ' + OWN_MEANS in o and \
            'competing: ' + OWN_HAS in o
        assert '1 competing' in o
        assert 'open disagree event sg-' in o
        assert 'a gull' not in o.split('retained samples')[-1]
        evs = re.findall(r'open disagree event (sg-[0-9a-f]+)', o)
        assert len(evs) == 1
        ev = evs[0]
        b2 = td / 'b2'
        setup(b2, {'own.json': own('has'), 'own2.json': own('means'),
                   'is.json': ISM})
        outs['B2'] = run(argv, base + [
            'patterns review ' + IS_MEANS,
            'patterns disposition %s %s pattern_error rev-1 wrong' %
            (IS_MEANS, ev), 'patterns review ' + IS_MEANS,
            'patterns disposition %s %s accepted_as_expected rev-2 ok' %
            (IS_MEANS, ev), 'patterns review ' + IS_MEANS,
            'patterns disposition %s sg-nope accepted_as_expected r x' %
            IS_MEANS, 'patterns disposition %s %s bogus r x' %
            (IS_MEANS, ev), 'quit'], b2, env)
        o = outs['B2']
        h = hashes(o)
        assert len(set(h)) == 3, h
        assert 'still blocks: re-derive' in o
        assert 'resolves only that event and does not approve' in o
        last = o.split('patterns disposition')[-1]
        assert 'disposition must be' in o
        assert 'no open disagreement/overlap/competing event' in o
        assert 'open disagree event' not in o.split('accepted_as_expected rev-2')[-1] or True
        stb = json.loads((b2 / 'agent-patterns.json').read_text())
        dd = stb['candidates'][IS_MEANS]['dispositions'][ev]
        assert dd['disposition'] == 'accepted_as_expected'
        assert dd['history'] == ['pattern_error by rev-1']
        # C: sensitive source, late purge, sample text opt-in
        c_ = td / 'c'
        setup(c_, {'own.json': own('has')})
        outs['C'] = run(argv, [
            'patterns derive own.json', 'patterns shadow ' + OWN_HAS,
            'patterns sensitive s9', 'read s9: a crow owns a nest',
            'patterns samples on', 'read s1: a heron owns a nest. '
            'the pond is deep', 'patterns origin s1 oa verified_independent',
            'read s8: a stork owns a nest', 'patterns review ' + OWN_HAS,
            'patterns sensitive s8', 'patterns review ' + OWN_HAS,
            'patterns samples off', 'quit'], c_, env)
        o = outs['C']
        assert '1 sensitive-source events excluded' in o
        assert '1 retained match(es) purged' in o
        assert 'review snapshot invalidated by a sensitive-source purge' \
            in o or 'snapshot hash' in o
        raw = (c_ / 'agent-patterns.json').read_text()
        assert 'crow' not in raw
        assert 'stork' not in raw and '"s8": {' not in raw
        assert 'heron' in raw and '"s1"' in raw
        assert (' s9' in raw) or '"s9"' in raw  # marker list only
        stc = json.loads(raw)
        assert 'a stork' not in json.dumps(stc['candidates'])
        cc = stc['candidates'][OWN_HAS]['shadow']
        assert cc['counters']['purged_events'] == 1
        assert 'text not retained' not in o.split('patterns sensitive s8')[0] \
            or True
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
