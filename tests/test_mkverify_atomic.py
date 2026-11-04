#!/usr/bin/env python3
"""mkverify plumbing on fake targets only; no real verifier regeneration."""
import ast
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import mkverify


class AtomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.target = self.root / 'selfhost/be/verify.holy'
        self.target.parent.mkdir(parents=True)
        (self.root / 'scripts').mkdir()
        (self.root / 'ir.py').write_text('\n' * 831 + 'def verify_module():\n    pass\ndef _verify_func():\n    need_naive = any(p not in reach for l in reach for p in preds[l])\n' + '\n' * 210 + 'def _need(by, lab, tm):\n    pass\n')
        self.target.write_bytes(b'maintained sentinel\n')
        self.target.chmod(0o640)
        self.intermediates = []
        self.stages = []

    def translate(self, sources, raw, asm):
        source, raw = pathlib.Path(sources[0]), pathlib.Path(raw)
        assert source.parent == raw.parent
        assert source.parent != pathlib.Path('/tmp')
        assert stat.S_IMODE(source.parent.stat().st_mode) == 0o700
        assert asm == str(self.root / 'x64.py')
        self.intermediates.append(source.parent)
        raw.write_text('def fake():\n  pass\n')
        return []

    def fmt(self, args, check):
        self.assertTrue(check)
        self.assertEqual(args[:3], [sys.executable, str(self.root / 'hs.py'), 'fmt'])
        self.assertEqual(args[-1], '-w')
        stage = pathlib.Path(args[3])
        self.stages.append(stage)
        self.assertEqual(stage.parent, self.target.parent)
        self.assertNotEqual(stage, self.target)
        self.assertEqual(stage.suffix, '.holy')
        self.assertEqual(self.target.read_bytes(), b'maintained sentinel\n')
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
        stage.write_text('formatted candidate\n')

    def run_fake(self, translator=None, adapter=None, formatter=None, replacer=None):
        with mock.patch.object(mkverify, '__file__', str(self.root / 'scripts/mkverify.py')), \
             mock.patch.object(mkverify, 'translate', side_effect=translator or self.translate), \
             mock.patch.object(mkverify, 'adapt_dominance', side_effect=lambda m: m), \
             mock.patch.object(mkverify, 'adapt', side_effect=adapter or (lambda s: s)), \
             mock.patch.object(mkverify.subprocess, 'run', side_effect=formatter or self.fmt), \
             mock.patch.object(mkverify.os, 'replace', wraps=os.replace) as replace:
            if replacer:
                replace.side_effect = replacer
            mkverify.main()
            return replace

    def unchanged(self):
        self.assertEqual(self.target.read_bytes(), b'maintained sentinel\n')
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
        self.clean()

    def clean(self):
        self.assertEqual(list(self.target.parent.glob('.mkverify-*')), [])
        for directory in self.intermediates:
            self.assertFalse(directory.exists())

    def test_translate_error(self):
        def bad(*args):
            self.translate(*args)
            return ['unsupported fake']
        with self.assertRaises(SystemExit):
            self.run_fake(translator=bad)
        self.unchanged()

    def test_adaptation_exception(self):
        def bad(s):
            raise ValueError('fake adaptation')
        with self.assertRaises(ValueError):
            self.run_fake(adapter=bad)
        self.unchanged()

    def test_fmt_nonzero(self):
        def bad(args, check):
            self.fmt(args, check)
            raise subprocess.CalledProcessError(1, args)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_fake(formatter=bad)
        self.unchanged()

    def test_fmt_exception(self):
        def bad(args, check):
            self.fmt(args, check)
            raise OSError('fake formatter launch')
        with self.assertRaises(OSError):
            self.run_fake(formatter=bad)
        self.unchanged()

    def test_replace_failure(self):
        def bad(*args):
            raise OSError('fake replace')
        with self.assertRaises(OSError):
            self.run_fake(replacer=bad)
        self.unchanged()

    def test_success(self):
        replace = self.run_fake()
        self.assertEqual(self.target.read_bytes(), b'formatted candidate\n')
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
        replace.assert_called_once_with(self.stages[0], self.target)
        self.clean()

    def test_unique_paths(self):
        for _ in range(2):
            self.run_fake()
            self.clean()
            self.target.write_bytes(b'maintained sentinel\n')
        self.assertEqual(len(set(self.intermediates)), 2)
        self.assertEqual(len(set(self.stages)), 2)

    def test_registration(self):
        module = ast.parse((ROOT / 'tests/run_all.py').read_text())
        values = {n.targets[0].id: ast.literal_eval(n.value) for n in module.body
                  if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id in ('SUITES', 'QUICK_SKIP')}
        names = [name for name, _ in values['SUITES']]
        self.assertEqual(names.count(pathlib.Path(__file__).name), 1)
        self.assertNotIn(pathlib.Path(__file__).name, values['QUICK_SKIP'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AtomicTests)
    result = unittest.TextTestRunner().run(suite)
    if result.wasSuccessful():
        print(f'{result.testsRun}/{result.testsRun} mkverify failure-atomic plumbing (fake targets only)')
    sys.exit(not result.wasSuccessful())
