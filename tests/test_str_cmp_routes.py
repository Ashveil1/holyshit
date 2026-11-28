#!/usr/bin/env python3
"""C24: string comparison parity on every hosted execution route.

tests/fixtures/str_cmp_prog.holy prints the result of all six comparison
operators (< <= > >= == !=) over 19 string pairs (114 lines): ASCII order,
prefix pairs both directions, code points with lead/continuation bytes
>= 0x80 (Thai, accents, emoji) vs ASCII, unicode-internal differences at
the 2nd/3rd byte, equal strings, empty vs non-empty, and long strings
whose difference sits well past the shorter string's length (the old
x64gen/be x_str_cmp scan over-read the shorter operand).

Every route's stdout must be byte-identical to every other route's and
equal to the CPython oracle computed here. Invariant (runtime/doc): hs
strings are canonical UTF-8 compared by code point with no normalization;
UTF-8 byte order equals code point order, so a correct byte-wise unsigned
compare is the correct string compare. Invalid UTF-8 input is outside
this guarantee.

Routes: reference interp, reference-ir, ir-x64, ast-x64, seed-native,
hs-interpreter, and gcc-native when the gc toolchain is available
(7/7, else 6/7 with --skip-gcc or no gc.h).
"""
import contextlib
import io
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import interp
import ir
import x64gen

env = dict(os.environ, HSROOT=str(ROOT),
           HSPATH=os.pathsep.join([str(ROOT), str(ROOT / 'selfhost'), str(ROOT / 'selfhost/be')]))
SRC = ROOT / 'tests/fixtures/str_cmp_prog.holy'
text = SRC.read_text(encoding='utf-8')

PAIRS = [
    ("a", "b"), ("b", "a"), ("a", "a"),
    ("abc", "abcd"), ("abcd", "abc"),
    ("", "a"), ("", "ก"), ("ก", ""),
    ("ก", "a"), ("z", "ก"), ("é", "e"), ("é", "é"),
    ("ก", "ข"), ("é", "ê"), ("😀", "😁"),
    ("กกก", "ก"), ("a" * 64 + "ก", "a" * 64 + "b"),
    ("a" * 128, "a" * 128 + "b"), ("a" * 128 + "b", "a" * 128),
]
OPS = ["<", "<=", ">", ">=", "==", "!="]

# Fixture must be exactly the program this oracle describes (no drift).
regen = "".join('print "%s" %s "%s"\n' % (a, op, b) for (a, b) in PAIRS for op in OPS)
assert text == regen, 'fixture str_cmp_prog.holy out of sync with PAIRS'

oracle = [("true" if eval('a %s b' % op) else "false")
          for (a, b) in PAIRS for op in OPS]


def check(label, out_bytes):
    out = out_bytes.decode('ascii')
    lines = out.splitlines()
    assert lines == oracle, (label, [i for i, (x, y) in enumerate(zip(lines, oracle)) if x != y][:5])
    return lines


outputs = {}
with tempfile.TemporaryDirectory(prefix='hs-strcmp-') as tmp:
    d = Path(tmp)

    r = subprocess.run([sys.executable, str(ROOT / 'interp.py'), str(SRC)],
                       env=env, capture_output=True, timeout=300)
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr[-500:])
    outputs['reference'] = r.stdout

    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ir.run_module(ir.build_module(interp.parse_program(text)), str(d))
        outputs['reference-ir'] = out.getvalue().encode('ascii')

        runner = []
        if platform.machine() not in ('x86_64', 'amd64'):
            q = shutil.which('qemu-x86_64')
            if not q:
                print('skip: qemu-x86_64 unavailable')
                raise SystemExit(0)
            runner = [q]
        for label, build in [('ir-x64', x64gen.build_x64), ('ast-x64', x64gen.build_x64_ast)]:
            image = d / label
            with contextlib.redirect_stdout(io.StringIO()):
                rc = build(str(SRC), str(image))
            assert rc == 0 and image.exists(), label
            r = subprocess.run(runner + [str(image)], env=env, capture_output=True, timeout=300)
            assert r.returncode == 0 and not r.stderr, (label, r.returncode, r.stderr[-500:])
            outputs[label] = r.stdout
    finally:
        if old is None:
            os.environ.pop('HSPATH', None)
        else:
            os.environ['HSPATH'] = old

    for label, src in [('seed-native', SRC), ('hs-interpreter', ROOT / 'selfhost/be/irinterp_run.holy')]:
        image = d / label
        r = subprocess.run(runner + [str(ROOT / 'bootstrap/hs-hosted-x86_64'), str(src), str(image)],
                           env=env, capture_output=True, text=True, timeout=600)
        assert r.returncode == 0 and image.exists(), (label, r.stdout[-500:], r.stderr[-500:])
        cmd = runner + [str(image)]
        if label == 'hs-interpreter':
            cmd.append(str(SRC))
        r = subprocess.run(cmd, env=env, capture_output=True, timeout=600)
        assert r.returncode == 0 and not r.stderr, (label, r.returncode, r.stderr[-500:])
        outputs[label] = r.stdout

    have_gcc = (shutil.which('gcc') and
                (os.path.exists('/usr/include/gc.h') or os.environ.get('CPATH')))
    if '--skip-gcc' not in sys.argv and have_gcc:
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'run', str(SRC), '--backend', 'native'],
                           env=env, capture_output=True, timeout=600)
        assert r.returncode == 0 and not r.stderr, ('gcc-native', r.returncode, r.stderr[-500:])
        outputs['gcc-native'] = r.stdout

ref_lines = check('reference', outputs['reference'])
for label, out in outputs.items():
    if label == 'reference':
        continue
    lines = check(label, out)
    assert lines == ref_lines, (label, 'route output differs from reference')
    print('ok str_cmp', label, len(lines), 'lines byte-identical', flush=True)

n = len(outputs)
print(f'{n}/{n} str_cmp routes byte-identical + oracle-identical')
