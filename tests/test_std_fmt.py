#!/usr/bin/env python3
"""Pure-hs std.fmt format() against a Python reference, all hosted routes."""
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


def hs_str(v):
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if v is None:
        return 'null'
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return '[' + ', '.join(hs_str(x) for x in v) + ']'
    if isinstance(v, dict):
        return '{' + ', '.join(k + ': ' + hs_str(x) for k, x in v.items()) + '}'
    return str(v)


def hs_format(template, args):
    out = ''
    rest = template
    i = 0
    while True:
        o = rest.find('{')
        c = rest.find('}')
        if o < 0 and c < 0:
            return out + rest
        if c >= 0 and (o < 0 or c < o):
            assert rest[c:c + 2] == '}}', 'lone } in generated template'
            out += rest[:c] + '}'
            rest = rest[c + 2:]
        elif rest[o:o + 2] == '{{':
            out += rest[:o] + '{'
            rest = rest[o + 2:]
        else:
            assert rest[o:o + 2] == '{}', 'unsupported field in generated template'
            assert i < len(args), 'generated template short of args'
            out += rest[:o] + hs_str(args[i])
            i += 1
            rest = rest[o + 2:]


values = [0, 1, -5, 42, 10 ** 15, 1.5, -0.5, '', 'x', 'hello world',
          'ไทย', '🙂', 'a,b', True, False, None,
          [1, 2, 3], ['a', 'b'], [], [1, [2, 'x']], {'k': 1}, {'a': True, 'b': None}]
texts = ['', 'x', 'abc', 'no fields', 'a b c', 'ไทย', '🙂🎉', 'a,b', '  ',
         '100%', 'line\ttab', 'say "hi"', 'back\\slash', 'y' * 200]

rng = random.Random(13013)
cases = []
fixed = ['', 'no fields', '{}', '{} {}', '{{}}', '{{{}}}', '{{{}?}}', 'a{}b{}c',
         'ไทย {} 🙂', '100% {}', '{}{}', '{{', '}}', '{{{{', '}}}}', 'x{}y',
         '{} = {} ({})', 'pre {} mid {} post', '{{literal}} {}']
for t in fixed:
    n = t.replace('{{', '').replace('}}', '').count('{}')
    cases.append((t, [rng.choice(values) for _ in range(n + rng.randrange(3))]))
for _ in range(160):
    parts = []
    nargs = 0
    for _ in range(rng.randrange(6)):
        kind = rng.randrange(10)
        if kind < 5:
            parts.append(rng.choice(texts))
        elif kind < 8:
            parts.append('{}')
            nargs += 1
        elif kind == 8:
            parts.append('{{')
        else:
            parts.append('}}')
    t = ''.join(parts)
    extra = rng.randrange(3)
    cases.append((t, [rng.choice(values) for _ in range(nargs + extra)]))

want = [hs_format(t, a) for t, a in cases]


def lit(value):
    # hs string escapes cover only \n \t \r \" \\ \0; the corpus avoids
    # other control characters and emits Unicode literally.
    return json.dumps(value, ensure_ascii=False)


text = 'import std.fmt\nresults = []\n'
text += 'for case in ' + lit(cases) + ':\n'
text += '  append(results, std.fmt.format(case[0], case[1]))\n'
text += 'expected = ' + lit(want) + '\nfor i in range(len(expected)):\n  if results[i] != expected[i]:\n    print i\n    raise "std.fmt result mismatch"\nprint len(results)\n'

RAISE_CASES = [
    ('std.fmt.format("}", [])', 'std.fmt.format: single } in template'),
    ('std.fmt.format("a}b", [])', 'std.fmt.format: single } in template'),
    ('std.fmt.format("{0}", [1])', 'std.fmt.format: unsupported field'),
    ('std.fmt.format("{name}", [1])', 'std.fmt.format: unsupported field'),
    ('std.fmt.format("{:>3}", [1])', 'std.fmt.format: unsupported field'),
    ('std.fmt.format("{ }", [1])', 'std.fmt.format: unsupported field'),
    ('std.fmt.format("{}", [])', 'std.fmt.format: not enough arguments'),
    ('std.fmt.format("{} {}", [1])', 'std.fmt.format: not enough arguments'),
]


def check_raises():
    for call, message in RAISE_CASES:
        prog = 'import std.fmt\n' + call + '\n'
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
    print('ok std.fmt raise paths', len(RAISE_CASES), 'cases (reference route)', flush=True)


def verify(label, r):
    assert r.returncode == 0, (label, r.returncode, r.stderr[-1500:])
    assert not r.stderr, (label, r.stderr[-1500:])
    assert r.stdout == str(len(want)) + '\n', (label, r.stdout[-2000:])
    print('ok std.fmt corpus', label, len(want), 'cases', flush=True)


with tempfile.TemporaryDirectory(prefix='hs-fmt-') as tmp:
    d = Path(tmp)
    source = d/'fmts.holy'
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
print(str(6 if '--skip-gcc' in sys.argv else 7) + '/7 std.fmt execution routes; ' + str(len(want)) + ' cases each')
