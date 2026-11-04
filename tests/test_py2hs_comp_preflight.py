#!/usr/bin/env python3
"""Reject comprehension shapes outside the target parser's supported subset."""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import py2hs


def main():
    total = 0
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        inp, out = d / 'in.py', d / 'out.holy'
        def tr(src):
            inp.write_text(src)
            errs = py2hs.translate([str(inp)], str(out), str(ROOT / 'x64.py'))
            return errs, out.read_text()
        forms = ['[x CLAUSES]', '(x CLAUSES)', '{x CLAUSES}', '{x: x CLAUSES}']
        shapes = [('for x in xs for y in ys', 'multiple comprehension generators'),
                  ('for x in xs if x if x > 1', 'multiple comprehension filters'),
                  ('async for x in xs', 'async comprehension')]
        for form in forms:
            for clauses, diagnostic in shapes:
                expr = form.replace('CLAUSES', clauses)
                for src in ['bad = ' + expr + '\ngood = 7\n',
                            'def bad(xs, ys):\n    partial = 1\n    return ' + expr + '\ngood = 7\n']:
                    errs, text = tr(src)
                    assert len(errs) == 1 and diagnostic in errs[0], errs
                    assert 'bad' not in text and 'partial' not in text and 'good = 7' in text, text
                    total += 1
                errs, text = tr('class C:\n    def bad(self, xs, ys):\n        return ' + expr + '\n')
                assert len(errs) == 1 and diagnostic in errs[0], errs
                assert 'raise "untranslated bad"' in text, text
                total += 1
                # Direct translator object proves preflight leaves tuple aliases
                # and output unchanged, even on a caller catching Unsupported.
                t = py2hs.T(set(), {})
                t.alias = {'kept': 'sentinel'}
                before = (dict(t.alias), list(t.out))
                try:
                    t.e(ast.parse(expr, mode='eval').body)
                except py2hs.Unsupported as e:
                    assert diagnostic in str(e)
                else:
                    raise AssertionError('unsupported shape accepted')
                assert (t.alias, t.out) == before
                assert t.e(ast.parse('kept', mode='eval').body) == 'sentinel'
                total += 1
        for form, wrap in zip(forms, ['[BODY]', '[BODY]', 'py_set([BODY])', 'py_dict([BODY])']):
            for clause in ['for x in xs', 'for x in xs if x']:
                errs, text = tr('result = ' + form.replace('CLAUSES', clause) + '\n')
                body = ('[x, x]' if form.startswith('{x:') else 'x') + ' ' + clause
                assert not errs and text == 'result = ' + wrap.replace('BODY', body) + '\n\n', (errs, text)
                total += 1
        inp.write_text('bad = [x for x in xs for y in ys]\n')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/py2hs.py'), str(inp), str(out)], capture_output=True, text=True)
        assert r.returncode == 0 and 'UNSUPPORTED Assign:1 multiple comprehension generators' in r.stdout
        total += 1
        errs, _ = tr(inp.read_text())
        try:
            if errs: raise SystemExit(str(errs))
        except SystemExit as e:
            assert 'multiple comprehension generators' in str(e)
        else:
            raise AssertionError('strict consumer accepted')
        total += 1
    runner = ast.parse((ROOT / 'tests/run_all.py').read_text())
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in runner.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ('SUITES', 'QUICK_SKIP')}
    names = [name for name, _ in values['SUITES']]
    assert names.count(Path(__file__).name) == 1 and Path(__file__).name not in values['QUICK_SKIP']
    print(f'{total}/{total} comprehension preflight rejection/accepted bytes/rollback/alias/CLI contracts; once quick/full')


if __name__ == '__main__':
    main()
