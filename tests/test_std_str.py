#!/usr/bin/env python3
"""Pure-hs std.str text helpers against Python str methods, all hosted routes."""
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


def ascii_lower(s):
    return ''.join(chr(ord(c) + 32) if 'A' <= c <= 'Z' else c for c in s)


def ascii_upper(s):
    return ''.join(chr(ord(c) - 32) if 'a' <= c <= 'z' else c for c in s)


strings = ['', 'a', 'A', 'zZ', 'abc', 'AbC dEf', '  pad  ', '\t\nmixed \r',
           'aaa', 'aAaA', 'hello world', 'x,y,,z,', ',,', 'ไทยภาษา', 'éÉè',
           '🙂🎉', 'MiXeD123!', '  ', 'a b c d', 'foo.bar.baz', 'ab' * 120,
           'A' * 64 + 'z', 'x y', 'Y', 'aAbB', '...,', 'éà']
rng = random.Random(12026)
alpha = ['a', 'b', 'A', 'B', ' ', ',', 'x', 'é', '🙂', '0', '\t']
for _ in range(120):
    strings.append(''.join(rng.choice(alpha) for _ in range(rng.randrange(13))))

replace_cases = []
olds = ['a', 'aa', 'ab', ',', ' ', 'xy', 'ไท', '🙂', 'ab' * 60]
news = ['', 'X', '--', 'é', ' a ', 'b' * 40]
for _ in range(150):
    replace_cases.append((rng.choice(strings), rng.choice(olds), rng.choice(news)))

count_cases = []
subs = ['a', 'aa', 'ab', ',', ' ', 'x', '🙂', 'ab' * 60]
for _ in range(120):
    count_cases.append((rng.choice(strings), rng.choice(subs)))

# find_from returns an index, and indices follow the backend's string
# model (characters in the reference interpreter, bytes on compiled x64);
# the corpus keeps the haystacks ASCII so every route agrees.
ascii_strings = [s for s in strings if all(ord(c) < 128 for c in s)]
find_cases = []
fsubs = ['', 'a', 'aa', 'ab', ',', 'x', 'xy', '0']
starts = [-100, -4, -1, 0, 1, 2, 3, 5, 8, 50]
for _ in range(120):
    find_cases.append((rng.choice(ascii_strings), rng.choice(fsubs), rng.choice(starts)))

split_cases = []
seps = [',', 'aa', ' ', 'ab', 'x', '🙂']
maxsplits = [-1, 0, 1, 2, 3, 7, 100]
for _ in range(100):
    split_cases.append((rng.choice(strings), rng.choice(seps), rng.choice(maxsplits)))

# strip charsets must be ASCII (non-ASCII raises); the stripped text may
# be anything.
strip_cases = []
charsets = ['', ' ', ' \t\n\r', 'ab', 'xyz', ',.', 'aA', '0']
for _ in range(100):
    strip_cases.append((rng.choice(strings), rng.choice(charsets)))

want = []
for s in strings:
    want.append(ascii_lower(s))
    want.append(ascii_upper(s))
for s, old, new in replace_cases:
    want.append(s.replace(old, new))
for s, sub in count_cases:
    want.append(s.count(sub))
for s, sub, start in find_cases:
    want.append(s.find(sub, start))
for s, sep, maxsplit in split_cases:
    want.append(s.split(sep, maxsplit))
for s, chars in strip_cases:
    want.append(s.strip(chars))
    want.append(s.lstrip(chars))
    want.append(s.rstrip(chars))


def lit(value):
    # hs string escapes cover only \n \t \r \" \\ \0; keep the corpus free
    # of other control characters and emit Unicode literally.
    return json.dumps(value, ensure_ascii=False)


text = 'import std.str\nresults = []\n'
text += 'for s in ' + lit(strings) + ':\n'
text += '  append(results, std.str.lower(s))\n  append(results, std.str.upper(s))\n'
text += 'for case in ' + lit(replace_cases) + ':\n'
text += '  append(results, std.str.replace(case[0], case[1], case[2]))\n'
text += 'for case in ' + lit(count_cases) + ':\n'
text += '  append(results, std.str.count(case[0], case[1]))\n'
text += 'for case in ' + lit(find_cases) + ':\n'
text += '  append(results, std.str.find_from(case[0], case[1], case[2]))\n'
text += 'for case in ' + lit(split_cases) + ':\n'
text += '  append(results, std.str.split_n(case[0], case[1], case[2]))\n'
text += 'for case in ' + lit(strip_cases) + ':\n'
text += '  append(results, std.str.strip(case[0], case[1]))\n'
text += '  append(results, std.str.lstrip(case[0], case[1]))\n'
text += '  append(results, std.str.rstrip(case[0], case[1]))\n'
text += 'expected = ' + lit(want) + '\nfor i in range(len(expected)):\n  if results[i] != expected[i]:\n    print i\n    raise "std.str result mismatch"\nprint len(results)\n'


RAISE_CASES = [
    ('std.str.replace("a", "", "x")', 'std.str.replace: empty pattern'),
    ('std.str.count("a", "")', 'std.str.count: empty pattern'),
    ('std.str.split_n("a", "", 1)', 'std.str.split_n: empty separator'),
    ('std.str.strip("a", "é")', 'std.str.strip: chars must be ASCII'),
    ('std.str.lstrip("a", "é")', 'std.str.lstrip: chars must be ASCII'),
    ('std.str.rstrip("a", "é")', 'std.str.rstrip: chars must be ASCII'),
]


def check_raises():
    for call, message in RAISE_CASES:
        prog = 'import std.str\n' + call + '\n'
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
    print('ok std.str raise paths', len(RAISE_CASES), 'cases (reference route)', flush=True)


def verify(label, r):
    assert r.returncode == 0, (label, r.returncode, r.stderr[-1500:])
    assert not r.stderr, (label, r.stderr[-1500:])
    assert r.stdout == str(len(want)) + '\n', (label, r.stdout[-2000:])
    print('ok std.str corpus', label, len(want), 'cases', flush=True)


with tempfile.TemporaryDirectory(prefix='hs-str-') as tmp:
    d = Path(tmp)
    source = d/'strs.holy'
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
print(str(6 if '--skip-gcc' in sys.argv else 7) + '/7 std.str execution routes; ' + str(len(want)) + ' cases each')
