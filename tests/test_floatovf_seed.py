#!/usr/bin/env python3
"""Overflowing float literals: the seed compiler must not hang, values stay exact.

The hosted seed compiler once hung forever on any literal beyond the double
range: py_f64bits (selfhost/be/pyrt.holy) scaled an infinite mantissa by
halving, which never converges. The pre-fix behavior is a 100% CPU hang in
build_ir_image, so the pin is a hard timeout on the seed compile plus exact
runtime values on the seed, ir-x64 and interp routes.

The fixture source lives in a temp dir, NOT tests/*.holy: several suites glob
that directory and round-trip fixture ASTs through hs json_str, which rejects
non-finite constants by design (C19, allow_nan=False parity with
json.dumps).
"""
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SRC = """\
# Bare overflowing and edge float literals. The hosted seed compiler once
# hung on any literal beyond the double range: py_f64bits scaled inf by
# halving forever while turning the constant into bytes. Pin the compile
# AND the runtime value of the overflow, underflow and finite edges.
print 1e999
print 0 - 1e999
print 1e308
print 1e-999
print 1.5e999 + 1
print 2.5, 0.1
"""

WANT = b"inf\n-inf\n1e+308\n0.0\ninf\n2.5 0.1\n"


def main():
    runner = []
    if platform.machine() not in ('x86_64', 'amd64'):
        q = shutil.which('qemu-x86_64')
        if not q:
            print('skip: qemu-x86_64 unavailable')
            return
        runner = [q]
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        src = d / 'floatovf.holy'
        src.write_text(SRC)

        # seed compile: the pre-fix seed spins at 100% CPU here forever
        seed_img = d / 'floatovf-seed'
        r = subprocess.run(runner + [str(ROOT / 'bootstrap/hs-hosted-x86_64'),
                                     str(src), str(seed_img)],
                           capture_output=True, timeout=300)
        assert r.returncode == 0 and seed_img.exists(), \
            ('seed compile', r.returncode, r.stdout[-300:], r.stderr[-300:])
        r = subprocess.run(runner + [str(seed_img)], capture_output=True, timeout=60)
        assert r.returncode == 0 and r.stdout == WANT and not r.stderr, \
            ('seed run', r.returncode, r.stdout, r.stderr[-300:])
        print('ok seed-native compile+run: overflowing literals exact')

        # ir-x64 route (xbuild): same values
        from x64gen import build_x64
        import interp
        interp.reset_parse_state()
        x64_img = d / 'floatovf-x64'
        assert build_x64(str(src), str(x64_img)) == 0
        r = subprocess.run(runner + [str(x64_img)], capture_output=True, timeout=60)
        assert r.returncode == 0 and r.stdout == WANT and not r.stderr, \
            ('ir-x64 run', r.returncode, r.stdout, r.stderr[-300:])
        print('ok ir-x64 compile+run: overflowing literals exact')

        # interp route: same values
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'run', str(src),
                            '--backend', 'interp'],
                           capture_output=True, timeout=60)
        assert r.returncode == 0 and r.stdout == WANT and not r.stderr, \
            ('interp run', r.returncode, r.stdout, r.stderr[-300:])
        print('ok interp: overflowing literals exact')
    print('3/3 floatovf routes: seed compiles overflowing literals, values exact')


if __name__ == '__main__':
    main()
