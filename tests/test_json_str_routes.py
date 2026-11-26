#!/usr/bin/env python3
"""C19: json_str byte parity on every hosted execution route.

tests/fixtures/json_str_routes.holy prints "<idx>|<json_str output>" lines
covering CPython json.dumps(ensure_ascii=True, allow_nan=False) semantics:
all control chars, DEL, ASCII/quote/backslash/solidus, embedded NUL, BMP and
supplementary code points incl. boundary planes, Thai text, floats (shortest
round-trip repr incl. -0.0, subnormals, largest finite), typed round trips
(3.0 stays "3.0"), buffer-growth sizes, an LCG differential battery, and the
non-finite rejection surface.

Every route's stdout must be byte-identical to every other route's, and the
non-error lines must equal the CPython oracle computed here. Invalid UTF-8
input is outside this guarantee (see native/rt.c js_str).

Routes: reference interp, ir-x64, ast-x64, seed-native, hs-interpreter,
and gcc-native when the gc toolchain is available (6/6, else 5/5 with
--skip-gcc or no gc.h). reference-ir (ir.py) is excluded: json_parse /
json_str are not in its IR builtin subset (pre-existing, unrelated to
C19).
"""
import contextlib
import io
import json
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
SRC = ROOT / 'tests/fixtures/json_str_routes.holy'
text = SRC.read_text(encoding='utf-8')

# ---------------- CPython oracle ----------------
pool = ["ก", "นกแก้ว", "a", "A", "é", "z", "🙂", "aa", "", " ",
        ''.join(chr(c) for c in [0x01, 0x1F, 0x7F, 0x80]), "ข้าว ข้า a robin", "🙂😀"]
oracle = {}
def J(v):
    return json.dumps(v, ensure_ascii=True, allow_nan=False)
oracle['01'] = J(''.join(chr(c) for c in range(0x20)))
oracle['02'] = J(''.join(chr(c) for c in [0x7F, 0x80, 0xFF, 0x100, 0x7FF, 0x800]))
oracle['03'] = J("ก ข นก นกแก้ว ไทย สวัสดีครับ ผู้ใช้")
oracle['04'] = J("🙂 🙂🙂🙂 🚀✨")
oracle['05'] = J(''.join(chr(c) for c in [0xD7FF, 0xE000, 0xFFFF]))
oracle['06'] = J('\U00010000')
oracle['07'] = J('\U0010FFFF')
oracle['08'] = J('a"b\\c/d\te\nf')
oracle['09'] = J('nul\x00here')
oracle['10'] = J([0.1, 3.0, -0.0, 0.5, -0.5, 1.5, 123456.789])
oracle['11'] = J([1e300, 1e-5, 1e16, 1e15, 1e-4, 9.999e-5, -1.5e-7])
oracle['12'] = J([5e-324, 1.7976931348623157e308, 2.2250738585072014e-308])
oracle['13'] = J([9007199254740992.0, 9007199254740994.0, 9999999999999998.0])
oracle['14'] = J({"s": "ไทย", "n": 42, "f": 0.1, "deep": [{"x": "🙂🙂"}], "ผู้ใช้": [True, None]})
oracle['15'] = J(3.0)
oracle['16'] = J(-0.0)
oracle['17'] = J(0.1)
oracle['18'] = J("ก")
oracle['19'] = J({"t": "ไทย", "e": "🙂", "l": [1, 2.5, "x"]})
lcg_lines = []
x = 12345
for _ in range(200):
    x = (48271 * x + 12345) % 2147483648
    lcg_lines.append(J([x, pool[x % len(pool)]]))
s = "กขc def🙂"
for _ in range(8):
    s = s + s
oracle['21'] = J(s)
oracle['22'] = J([0.1] * 400)

ERR_PREFIX = 'err json_str failed: Out of range float values are not JSON compliant at line '


def check(label, out_bytes):
    out = out_bytes.decode('ascii')
    lines = out.splitlines()
    assert lines, label
    seen_20 = 0
    for ln in lines:
        idx, payload = ln.split('|', 1)
        if idx == '20':
            assert payload == lcg_lines[seen_20], (label, seen_20, payload[:80], lcg_lines[seen_20][:80])
            seen_20 += 1
        elif idx in ('23', '24', '25'):
            assert payload.startswith(ERR_PREFIX), (label, ln)
        else:
            assert idx in oracle, (label, idx)
            assert payload == oracle[idx], (label, idx, payload[:100], oracle[idx][:100])
    assert seen_20 == 200, (label, seen_20)
    return lines


outputs = {}
with tempfile.TemporaryDirectory(prefix='hs-jsr-') as tmp:
    d = Path(tmp)

    r = subprocess.run([sys.executable, str(ROOT / 'interp.py'), str(SRC)],
                       env=env, capture_output=True, timeout=300)
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr[-500:])
    outputs['reference'] = r.stdout

    old = os.environ.get('HSPATH')
    os.environ['HSPATH'] = env['HSPATH']
    try:
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

ref_label = 'reference'
ref_lines = check(ref_label, outputs[ref_label])
for label, out in outputs.items():
    if label == ref_label:
        continue
    lines = check(label, out)
    assert lines == ref_lines, (label, 'route output differs from reference')
    print('ok json_str', label, len(lines), 'lines byte-identical', flush=True)

n = len(outputs)
print(f'{n}/{n} json_str routes byte-identical + CPython-oracle-identical')
