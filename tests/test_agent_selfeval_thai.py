#!/usr/bin/env python3
"""A23.3 Thai dataset format check (T-SE16 provenance rules). ASCII
placeholders only: the checker validates structure, it creates no labels."""
import copy, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_agent_shadow import run

TEMPLATE = ROOT / 'tests' / 'selfeval' / 'thai-core-v1.pending.json'
L = {'epistemic': 'supported', 'action': 'answer'}
AMB = {'epistemic': 'ambiguous', 'action': 'clarify'}


def item(i, cat='recall', crit=False, ann=None, adj=None, origin='authored'):
    return {'id': i, 'category': cat, 'input': 'placeholder-' + i,
            'origin': origin, 'critical': crit,
            'annotations': ann if ann is not None else [],
            'adjudication': adj or {'state': 'none'}}


def A(n, lb=L, role='independent'):
    return {'annotator': n, 'role': role, 'label': lb}


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        base = json.loads(TEMPLATE.read_text())
        base.pop('item_example_shape')

        def chk(items=None, **kw):
            s = copy.deepcopy(base)
            if items is not None:
                s['items'] = items
            s.update(kw)
            (td / 't.json').write_text(json.dumps(s))
            return run(argv, ['selfeval thai-check t.json', 'quit'], td, env)
        full = json.loads(TEMPLATE.read_text())
        (td / 'tpl.json').write_text(json.dumps(full))
        o = run(argv, ['selfeval thai-check tpl.json', 'quit'], td, env)
        assert 'PENDING_OWNER_LABELING: no items yet' in o
        assert 'no labels are created' in o
        o = chk([])
        assert 'status PENDING_OWNER_LABELING' in o
        # resolved paths
        ok = [item('a1', ann=[A('p1'), A('p2')],
                   adj={'state': 'agreed'}),
              item('a2', ann=[A('p1'), A('p2', AMB)],
                   adj={'state': 'adjudicated', 'by': 'judge',
                        'final': AMB}, crit=True),
              item('a3')]
        o = chk(ok)
        assert 'recall: 2 resolved of 3 items TOO_FEW_TO_JUDGE' in o, o
        assert '1 unresolved item(s), 0 problem(s)' in o
        ok[2] = item('a3', ann=[A('p1'), A('p2')], adj={'state': 'agreed'})
        assert 'READY_TO_FREEZE' in chk(ok)
        # rules
        def bad(it, msg, **kw):
            o = chk([it], **kw)
            assert msg in o, (msg, o)
            assert 'READY_TO_FREEZE' not in o
        bad(item('t1', origin='translated'), 't1: translated items are not')
        bad(item('t2', origin='scraped'), 't2: origin must be authored')
        bad(item('t3', cat='zzz'), 't3: category zzz has no semantic')
        bad(item('t4', ann=[A('p1')], adj={'state': 'agreed'}),
            't4: agreed needs two distinct annotators')
        bad(item('t5', ann=[A('p1'), A('p1')], adj={'state': 'agreed'}),
            't5: agreed needs two distinct annotators')
        bad(item('t6', ann=[A('p1'), A('p2', AMB)],
                 adj={'state': 'agreed'}),
            't6: marked agreed but annotations differ')
        bad(item('t7', crit=True, ann=[A('p1'), A('p2')],
                 adj={'state': 'agreed'}),
            't7: critical or ambiguous items need an adjudicator')
        bad(item('t8', ann=[A('p1', AMB), A('p2', AMB)],
                 adj={'state': 'agreed'}),
            't8: critical or ambiguous items need an adjudicator')
        bad(item('t9', ann=[A('p1'), A('p2', AMB)],
                 adj={'state': 'adjudicated', 'by': 'p1', 'final': L}),
            't9: the adjudicator cannot be one of the annotators')
        bad(item('t10', ann=[A('p1'), A('p2', AMB)],
                 adj={'state': 'adjudicated', 'by': 'j',
                      'final': {'epistemic': 'maybe'}}),
            't10: final label invalid')
        bad(item('t11', ann=[A('p1', {'epistemic': 'nope'}), A('p2')],
                 adj={'state': 'agreed'}),
            't11: annotation label invalid')
        bad(item('t12', ann=[A('p1', role='boss'), A('p2')],
                 adj={'state': 'agreed'}),
            't12: annotation role must be primary or independent')
        # suite-level refusals
        assert 'tier must be' in chk([], tier='future')
        assert 'status invalid' in chk([], status='DONE')
        assert 'owner-authored or owner-real' in chk(
            [], provenance={'method': 'synthetic', 'author': 'x'})
        assert 'owner-real data needs explicit opt_in' in chk(
            [], provenance={'method': 'owner-real', 'author': 'x'})
        assert 'kind must be thai-dataset' in chk([], lang='en')
        assert 'duplicate item id d' in chk([item('d'), item('d')])
        # criteria must be non-empty
        s = copy.deepcopy(base)
        s['acceptance_criteria']['recall'] = ''
        (td / 'c.json').write_text(json.dumps(s))
        o = run(argv, ['selfeval thai-check c.json', 'quit'], td, env)
        assert 'acceptance criteria must be a non-empty' in o
        # a Thai dataset is not a runnable suite and ids/counts only
        o = run(argv, ['selfeval run tpl.json', 'quit'], td, env)
        assert 'suite refused' in o
        assert 'placeholder-' not in chk(ok)
        print('ok %s: Thai dataset format, provenance and adjudication '
              'rules' % label)


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
            r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'build',
                                str(ROOT / 'agent' / 'repl.holy'), '-o',
                                str(img)], capture_output=True, text=True,
                               env=env)
            assert r.returncode == 0, r.stderr[-400:]
            suite('native', [str(img)], env)
    print('all agent selfeval thai tests passed')


if __name__ == '__main__':
    main()
