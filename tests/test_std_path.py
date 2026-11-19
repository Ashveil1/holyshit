#!/usr/bin/env python3
"""Pure-hs POSIX path helpers against Python posixpath, all hosted routes."""
import contextlib
import io
import json
import os
from pathlib import Path
import platform
import posixpath
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
paths = ['', '.', '..', '/', '//', '///', '////', 'a', 'a/', '/a/',
         'a//b///', '/a/../../b', '//a/../b/', 'a/../../b', '../..',
         '/../../', 'a/./b/../c', '.hidden', '..hidden', '...',
         '.a.b', 'a.', 'a..', 'a.tar.gz', '/a.b/name', '/a.b/.file',
         'dir/.', 'dir/..', 'dir/...', 'dir/.a.ext', 'a\\b.txt',
         'C:/dir/file', 'a b/$name', 'ไทย/../é.txt', 'ไทย/แฟ้ม.txt',
         '🙂/文件.tar.gz', 'é/.cache', 'a\t/b\n', 'a\0/b.ext',
         'a'*1024+'/../b', ('a/../'*80)+'final']
rng = random.Random(11019)
parts = ['', '.', '..', 'a', '.cache', 'b.txt', 'x.y.z', 'ไทย', 'é', '🙂']
for _ in range(240):
    paths.append('/'*rng.randrange(5) + '/'.join(rng.choice(parts) for _ in range(rng.randrange(9))))
pairs = [(a, b) for a in ['', 'a', 'a/', '/', '//root', 'ไทย/dir']
         for b in ['', 'b', '/b', '//b', '../b', './b', 'é.txt']]
pairs += [(rng.choice(paths), rng.choice(paths)) for _ in range(100)]
want = [[p, posixpath.isabs(p), posixpath.basename(p), posixpath.dirname(p),
         list(posixpath.splitext(p)), posixpath.normpath(p)] for p in paths]
want += [[a, b, posixpath.join(a, b)] for a, b in pairs]

def lit(value):
    # hs supports explicit NUL but no JSON's generic Unicode escape syntax.
    return json.dumps(value, ensure_ascii=False).replace('\\u0000', '\\0')

text = 'import std.path\nresults = []\n'
text += 'for p in '+lit(paths)+':\n'
text += '  append(results, [p, std.path.isabs(p), std.path.basename(p), std.path.dirname(p), std.path.splitext(p), std.path.normpath(p)])\n'
text += '  normalized = std.path.normpath(p)\n'
text += '  if std.path.normpath(normalized) != normalized:\n    raise "normpath not idempotent"\n'
text += 'for pair in '+lit(pairs)+':\n'
text += '  append(results, [pair[0], pair[1], std.path.join(pair[0], pair[1])])\n'
text += 'expected = '+lit(want)+'\nfor i in range(len(expected)):\n  if results[i] != expected[i]:\n    print i\n    raise "path result mismatch"\nprint len(results)\n'

def verify(label, r):
    assert r.returncode == 0, (label, r.returncode, r.stderr[-1500:])
    assert not r.stderr, (label, r.stderr[-1500:])
    assert r.stdout == str(len(want))+'\n', (label, r.stdout[-2000:])
    print('ok POSIX path corpus', label, len(want), 'cases', flush=True)

with tempfile.TemporaryDirectory(prefix='hs-path-') as tmp:
    d = Path(tmp)
    source = d/'paths.holy'
    source.write_text(text, encoding='utf-8')
    verify('reference', subprocess.run([sys.executable, str(ROOT/'interp.py'), str(source)],
           env=env, capture_output=True, text=True, timeout=60))
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
            verify(label, subprocess.run(runner+[str(image)], env=env, capture_output=True, text=True, timeout=60))
    finally:
        if old is None: os.environ.pop('HSPATH', None)
        else: os.environ['HSPATH'] = old
    for label, src in [('seed-native', source), ('hs-interpreter', ROOT/'selfhost/be/irinterp_run.holy')]:
        image = d/label
        r = subprocess.run(runner+[str(ROOT/'bootstrap/hs-hosted-x86_64'), str(src), str(image)],
                           env=env, capture_output=True, text=True, timeout=180)
        assert r.returncode == 0 and image.exists(), (label, r.stdout[-500:], r.stderr[-500:])
        command = runner+[str(image)]
        if label == 'hs-interpreter': command.append(str(source))
        verify(label, subprocess.run(command, env=env, capture_output=True, text=True, timeout=60))
    if '--skip-gcc' not in sys.argv:
        verify('gcc-native', subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run', str(source), '--backend', 'native'],
                env=env, capture_output=True, text=True, timeout=120))
print(str(6 if '--skip-gcc' in sys.argv else 7)+'/7 POSIX path execution routes; '+str(len(want))+' cases each, normpath idempotence')
