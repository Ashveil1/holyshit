#!/usr/bin/env python3
"""Exercise failure evidence without running/replacing the compiler driver."""
import ast
import json
from pathlib import Path
import subprocess
import time
import traceback
import unittest

# Loading the suite as a module would build and execute the entire corpus.
# Compile only the real pure helper, so these tests do not duplicate its logic.
source = Path(__file__).with_name('test_irbuild.py').read_text()
node = next(n for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == 'exception_evidence')
namespace = dict(time=time, traceback=traceback)
exec(compile(ast.Module(body=[node], type_ignores=[]), '<evidence-helper>', 'exec'), namespace)
evidence = namespace['exception_evidence']


class EvidenceTests(unittest.TestCase):
    def test_timeout_keeps_class_traceback_partial_bytes(self):
        try:
            raise subprocess.TimeoutExpired(['driver', 'ast'], 60,
                                            output=b'partial\xff', stderr=b'error')
        except subprocess.TimeoutExpired as exc:
            d = evidence(exc, 'native-run', None, ['driver', 'ast'],
                         time.monotonic(), None)
        self.assertEqual(d['exception_class'], 'TimeoutExpired')
        self.assertIn('subprocess.TimeoutExpired:', d['traceback'])
        self.assertEqual(d['stdout'], 'partial\\xff')
        self.assertEqual(d['stderr'], 'error')
        self.assertEqual(d['timeout_seconds'], 60)
        self.assertIsNone(d['returncode'])
        self.assertGreaterEqual(d['elapsed_seconds'], 0)
        self.assertEqual(json.loads(json.dumps(d)), d)

    def test_parse_error_keeps_complete_process_output(self):
        native = subprocess.CompletedProcess(['driver', 'ast'], -11,
                                             'x' * 1000, 'e' * 1000)
        try:
            json.loads(native.stdout)
        except json.JSONDecodeError as exc:
            d = evidence(exc, 'native-parse', native, native.args, 0, 2.5)
        self.assertEqual(d['exception_class'], 'JSONDecodeError')
        self.assertEqual(d['stdout'], native.stdout)
        self.assertEqual(d['stderr'], native.stderr)
        self.assertEqual(d['returncode'], -11)
        self.assertEqual(d['elapsed_seconds'], 2.5)
        self.assertIn('JSONDecodeError', d['traceback'])

    def test_pre_native_exception_has_no_native_metadata(self):
        try:
            raise ValueError('full failure ' + 'z' * 1000)
        except ValueError as exc:
            d = evidence(exc, 'interp-verify', None, None, None, None)
        self.assertEqual(d['exception_class'], 'ValueError')
        self.assertIn('z' * 1000, d['traceback'])
        for field in ('command', 'elapsed_seconds', 'timeout_seconds',
                      'returncode', 'stdout', 'stderr'):
            self.assertIsNone(d[field])


if __name__ == '__main__':
    unittest.main()
