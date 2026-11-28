#!/usr/bin/env python3
"""`run PROG args...` passes argv to the program (B23d).

The shell sends the words after PROG with the exec syscall; the kernel
validates the vector (16 words of 255 bytes, 2048 bytes total, argv[0] =
PROG), lays it out Linux-style on the new user stack, and the hosted
argv() reports the words after argv[0]. A line past the bound is refused
with 'exec failed' before the image is replaced. Typed over QEMU sendkeys,
default shell image, IR and AST.
"""
import os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_shell_boot as sb
import test_shell_disk as sd


def run(ir):
    with tempfile.TemporaryDirectory(prefix='shellargs-'+('ir-' if ir else 'ast-')) as t:
        d = Path(t); kernel, _, uush, hi = sb.build(d, ir)
        iso = sb.package_iso(d, kernel, uush, hi)
        text = sd.boot(d, ['-cdrom', str(iso), '-boot', 'd'], [
            ('run /bin/hi one two', 'program exit /bin/hi 0'),
            ('run /bin/hi a b c d e f g h i j k l m n o p q', 'exec failed'),
            ('echo alive after args', 'alive after args'),
            ('exit', 'shell exit 0')], 'args')
        assert 'argc 2' in text and 'arg 0 one' in text and 'arg 1 two' in text, text[-800:]
        assert text.count('program exit /bin/hi') == 1, 'refused exec reported as program exit'
        ev = os.environ.get('HS_SHELL_ARGS_EVIDENCE')
        if ev:
            dest = Path(ev)/('ir' if ir else 'ast'); dest.mkdir(parents=True, exist_ok=True)
            for n in ('args.ppm', 'serial', 'qemu.stderr'): shutil.copyfile(d/n, dest/n)
    print('ok shell run args', 'ir' if ir else 'ast')


if __name__ == '__main__':
    backends = (True, False)
    if '--backend' in sys.argv: backends = (sys.argv[sys.argv.index('--backend')+1] == 'ir',)
    for ir in backends: run(ir)
    print(f'{len(backends)}/{len(backends)} shell args gates')
