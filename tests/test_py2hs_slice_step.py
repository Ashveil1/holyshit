#!/usr/bin/env python3
"""Explicit Python slice steps must fail, never silently lose semantics."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import py2hs


def translate(source, directory):
    inp, out = directory / 'in.py', directory / 'out.holy'
    inp.write_text(source)
    errs = py2hs.translate([str(inp)], str(out), str(ROOT / 'x64.py'))
    return errs, out.read_text()


def main():
    count = 0
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for expr in ('xs[::-1]', 'xs[::1]', 'xs[::0]', 'xs[a:b:step]', 'xs[::None]'):
            for source in ('bad = ' + expr + '\ngood = 7\n',
                           'def bad(xs, a, b, step):\n    keep = 1\n    return ' + expr + '\ngood = 7\n'):
                errs, out = translate(source, d)
                assert len(errs) == 1 and 'slice step' in errs[0], errs
                assert 'bad' not in out and 'keep' not in out and 'good = 7' in out, out
                count += 1
        errs, out = translate('class C:\n    def bad(self, xs):\n        return xs[::-1]\n', d)
        assert len(errs) == 1 and 'slice step' in errs[0], errs
        assert 'raise "untranslated bad"' in out and 'py_tail' not in out, out
        count += 1
        for expr, expected in [('xs[a:b]', 'xs[a:b]'), ('xs[:b]', 'xs[0:b]'), ('xs[a:]', 'py_tail(xs, a)'), ('xs[:]', 'py_tail(xs, 0)')]:
            errs, out = translate('result = ' + expr + '\n', d)
            assert not errs and out == 'result = ' + expected + '\n\n', (errs, out)
            count += 1
        inp = d / 'in.py'; inp.write_text('bad = xs[::-1]\n')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/py2hs.py'), str(inp), str(d / 'out.holy')], capture_output=True, text=True)
        assert r.returncode == 0 and 'UNSUPPORTED Assign:1 slice step' in r.stdout, (r.returncode, r.stdout, r.stderr)
        count += 1
        # Strict consumers already stop on returned errors; preserve that API.
        errs, _ = translate('bad = xs[::-1]\n', d)
        try:
            if errs:
                raise SystemExit(str(errs))
        except SystemExit as e:
            assert 'slice step' in str(e)
        else:
            raise AssertionError('strict consumer accepted unsupported input')
        count += 1
    runner = ast.parse((ROOT / 'tests/run_all.py').read_text())
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in runner.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ('SUITES', 'QUICK_SKIP')}
    names = [name for name, _ in values['SUITES']]
    assert names.count(Path(__file__).name) == 1 and Path(__file__).name not in values['QUICK_SKIP']
    print(f'{count}/{count} explicit-step rejection and existing output/error contracts; registration once quick/full')


if __name__ == '__main__':
    main()
