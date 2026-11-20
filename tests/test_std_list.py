#!/usr/bin/env python3
"""Pure-hs std.list everyday helpers against Python, all hosted routes."""
import contextlib
import io
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import interp
import ir
import x64gen

env = dict(os.environ, HSROOT=str(ROOT), HSPATH=os.pathsep.join([
    str(ROOT), str(ROOT/'selfhost'), str(ROOT/'selfhost/be')]))

rng = random.Random(14014)

int_lists = [[], [1], [3, 1, 2, 1], list(range(10)), list(range(9, -1, -1)),
             [0] * 7, [-5, 10 ** 15, 42, -1], [2, 2, 2, 1, 1, 3]]
for _ in range(14):
    int_lists.append([rng.randrange(-50, 50) for _ in range(rng.randrange(20))])
int_lists.append([rng.randrange(-1000, 1000) for _ in range(120)])

float_lists = [[0.5], [1.5, -0.5, 2.5, 1.5], [-3.5, 0.5, 100.5]]
for _ in range(8):
    float_lists.append([rng.randrange(-20, 20) + 0.5 for _ in range(rng.randrange(12))])

# sort/min/max over strings use the builtin < comparison, whose ordering
# of non-ASCII text differs between the reference interpreter (Unicode
# codepoints) and the compiled x64 backends (signed byte order) - a
# pre-existing language-level divergence pinned by this corpus staying
# ASCII for comparisons. Reverse/enumerate carry any text.
str_lists = [['b', 'a', 'c'], ['banana', 'apple', 'cherry'], [''], ['x'] * 4,
             ['Zebra', 'abc', 'Abc', 'z']]
for _ in range(8):
    str_lists.append([rng.choice(['aa', 'ab', 'b', 'a', '', 'zz', 'A', 'Z'])
                      for _ in range(rng.randrange(10))])
unicode_str_lists = [['banana', 'apple', 'é', '🙂'], ['ไทย', 'abc'], ['é']]

mixed_lists = [[1, 'a', True, None], [], [[1, 2], {'k': 1}, 'x'], [1.5, 'y', [0]]]
for _ in range(8):
    mixed_lists.append([rng.choice([1, 'a', True, None, 2.5, [1], {'k': 0}])
                        for _ in range(rng.randrange(8))])

zip_cases = [([1, 2, 3], ['a', 'b']), ([], [1]), ([1], []), ([1, 2], [3, 4]),
             (['x'], [1, 2, 3]), (list(range(50)), list(range(40, 100)))]
for _ in range(10):
    zip_cases.append(([rng.randrange(5) for _ in range(rng.randrange(8))],
                      [rng.choice(['a', 'b', 'é']) for _ in range(rng.randrange(8))]))

want = []
for xs in int_lists + float_lists:
    want += [sorted(xs), list(reversed(xs)), sum(xs)]
    if xs:
        want += [min(xs), max(xs)]
for xs in str_lists:
    want += [sorted(xs), list(reversed(xs))]
    if xs:
        want += [min(xs), max(xs)]
for xs in unicode_str_lists:
    want += [list(reversed(xs)), [[i, x] for i, x in enumerate(xs)]]
for xs in mixed_lists:
    want += [list(reversed(xs)), [[i, x] for i, x in enumerate(xs)]]
for a, b in zip_cases:
    want.append([[x, y] for x, y in zip(a, b)])


def lit(value):
    # hs string escapes cover only \n \t \r \" \\ \0; the corpus avoids
    # other control characters and emits Unicode literally.
    return json.dumps(value, ensure_ascii=False)


text = 'import std.list\nresults = []\n'
text += 'for case in ' + lit(int_lists + float_lists) + ':\n'
text += '  append(results, std.list.sort(case))\n'
text += '  append(results, std.list.reverse(case))\n'
text += '  append(results, std.list.sum(case))\n'
text += '  if len(case) > 0:\n'
text += '    append(results, std.list.min(case))\n'
text += '    append(results, std.list.max(case))\n'
text += 'for case in ' + lit(str_lists) + ':\n'
text += '  append(results, std.list.sort(case))\n'
text += '  append(results, std.list.reverse(case))\n'
text += '  if len(case) > 0:\n'
text += '    append(results, std.list.min(case))\n'
text += '    append(results, std.list.max(case))\n'
text += 'for case in ' + lit(unicode_str_lists) + ':\n'
text += '  append(results, std.list.reverse(case))\n'
text += '  append(results, std.list.enumerate(case))\n'
text += 'for case in ' + lit(mixed_lists) + ':\n'
text += '  append(results, std.list.reverse(case))\n'
text += '  append(results, std.list.enumerate(case))\n'
text += 'for case in ' + lit(zip_cases) + ':\n'
text += '  append(results, std.list.zip(case[0], case[1]))\n'
text += 'expected = ' + lit(want) + '\nfor i in range(len(expected)):\n  if results[i] != expected[i]:\n    print i\n    raise "std.list result mismatch"\nprint len(results)\n'

RAISE_CASES = [
    ('std.list.min([])', 'std.list.min: empty list'),
    ('std.list.max([])', 'std.list.max: empty list'),
]


def check_raises():
    for call, message in RAISE_CASES:
        prog = 'import std.list\n' + call + '\n'
        with tempfile.NamedTemporaryFile('w', suffix='.holy', delete=False) as f:
            f.write(prog)
            path = f.name
        try:
            r = subprocess.run([sys.executable, str(ROOT/'interp.py'), path],
                               env=env, capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 1, (call, r.returncode, r.stdout, r.stderr)
        assert r.stderr.startswith('error: ' + message + ' at line '), (call, r.stderr)
    print('ok std.list raise paths', len(RAISE_CASES), 'cases (reference route)', flush=True)


def verify(label, r):
    assert r.returncode == 0, (label, r.returncode, r.stderr[-1500:])
    assert not r.stderr, (label, r.stderr[-1500:])
    assert r.stdout == str(len(want)) + '\n', (label, r.stdout[-2000:])
    print('ok std.list corpus', label, len(want), 'cases', flush=True)


with tempfile.TemporaryDirectory(prefix='hs-list-') as tmp:
    d = Path(tmp)
    source = d/'lists.holy'
    source.write_text(text, encoding='utf-8')
    verify('reference', subprocess.run([sys.executable, str(ROOT/'interp.py'), str(source)],
           env=env, capture_output=True, text=True, timeout=120))
    # The reference IR executor is independent of native code generation.
    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        interp.reset_parse_state()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            ir.run_module(ir.build_module(interp.parse_program(text)), str(d))
        verify('reference-ir', subprocess.CompletedProcess([], 0, output.getvalue(), ''))
    finally:
        if old is None: os.environ.pop('HSPATH', None)
        else: os.environ['HSPATH'] = old
    runner = []
    if platform.machine() not in ('x86_64', 'amd64'):
        qemu = shutil.which('qemu-x86_64')
        if not qemu:
            print('skip hosted x86 path routes: qemu-x86_64 unavailable')
            raise SystemExit(0)
        runner = [qemu]
    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        for label, build in [('ir-x64', x64gen.build_x64), ('ast-x64', x64gen.build_x64_ast)]:
            image = d/label
            with contextlib.redirect_stdout(io.StringIO()):
                rc = build(str(source), str(image))
            assert rc == 0 and image.exists(), label
            verify(label, subprocess.run(runner + [str(image)], env=env, capture_output=True, text=True, timeout=120))
    finally:
        if old is None: os.environ.pop('HSPATH', None)
        else: os.environ['HSPATH'] = old
    for label, src in [('seed-native', source), ('hs-interpreter', ROOT/'selfhost/be/irinterp_run.holy')]:
        image = d/label
        r = subprocess.run(runner + [str(ROOT/'bootstrap/hs-hosted-x86_64'), str(src), str(image)],
                           env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0 and image.exists(), (label, r.stdout[-500:], r.stderr[-500:])
        command = runner + [str(image)]
        if label == 'hs-interpreter': command.append(str(source))
        verify(label, subprocess.run(command, env=env, capture_output=True, text=True, timeout=120))
    if '--skip-gcc' not in sys.argv:
        verify('gcc-native', subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run', str(source), '--backend', 'native'],
                env=env, capture_output=True, text=True, timeout=180))
check_raises()
print(str(6 if '--skip-gcc' in sys.argv else 7) + '/7 std.list execution routes; ' + str(len(want)) + ' cases each')
