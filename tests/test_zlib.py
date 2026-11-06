#!/usr/bin/env python3
"""Real zlib through an explicit C-int/LP64 bridge on four existing routes.

Linux x86-64 requires gcc, zlib headers/library and libgc headers/library.
Missing dependencies fail the suite; they are never counted as passes/skips.
Manual example: build examples/zlib/bridge.c as documented in that file, then
cd examples/zlib && python3 ../../hs.py run roundtrip.holy --backend x64.
"""
import ast
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parent.parent
DATA = bytes([65, 0, 66, 255, 67, 0])
ENV = dict(os.environ, HSPATH=str(ROOT / 'selfhost') + ':' + str(ROOT / 'selfhost/be'),
           HSROOT=str(ROOT))


def run(args, timeout=120, cwd=ROOT):
    return subprocess.run([str(x) for x in args], cwd=cwd, env=ENV,
                          capture_output=True, text=True, timeout=timeout)


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        print('FAIL zlib integration requires Linux x86-64 LP64 and its pinned seed')
        return 1
    if not shutil.which('gcc'):
        print('FAIL zlib integration requires gcc, zlib1g-dev and libgc-dev')
        return 1
    passed = failed = 0
    with tempfile.TemporaryDirectory(prefix='hs zlib bridge space ') as tmp:
        tmp = Path(tmp)
        source = tmp / 'zlib_roundtrip.holy'
        source.write_bytes((ROOT / 'examples/zlib/roundtrip.holy').read_bytes())
        built = run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-shared',
                     '-fPIC', ROOT / 'examples/zlib/bridge.c', '-lz', '-o',
                     tmp / 'zlib_bridge.so'])
        if built.returncode:
            print('FAIL zlib bridge build (zlib1g-dev required):', built.stderr)
            return 1
        for backend in ('interp', 'native', 'x64', 'native-hs'):
            if backend == 'native-hs':
                program = tmp / 'program'
                result = run([ROOT / 'bootstrap/hs-hosted-x86_64', source, program])
                if result.returncode == 0:
                    result = run([program], timeout=20, cwd=tmp)
            else:
                result = run([sys.executable, ROOT / 'hs.py', 'run', source,
                              '--backend', backend], cwd=tmp)
            ok = False
            detail = ''
            try:
                lines = result.stdout.splitlines()
                packed = bytes(ast.literal_eval(lines[0]))
                restored = bytes(ast.literal_eval(lines[1]))
                # Independent Python zlib decoder checks actual compressed bytes.
                ok = (result.returncode == 0 and not result.stderr
                      and len(lines) == 5 and zlib.decompress(packed) == DATA
                      and restored == DATA and lines[2:] == ['-5', '-2', '-3'])
            except (ValueError, SyntaxError, IndexError, TypeError, zlib.error) as error:
                detail = str(error)
            passed += int(ok)
            failed += int(not ok)
            print(('ok  ' if ok else 'FAIL'), backend, 'zlib roundtrip/error gates',
                  '' if ok else repr((result.returncode, result.stdout,
                                      result.stderr[-1200:], detail)))
    print(f'{passed}/{passed + failed} real zlib four-route integration gates')
    return bool(failed)


if __name__ == '__main__':
    sys.exit(main())
