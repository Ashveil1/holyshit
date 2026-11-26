#!/usr/bin/env python3
"""`run` hands back to the shell with a status line (B23c).

A program started with `run` replaces the shell until it exits; the kernel
then reports `[PATH exited CODE]` (serial and framebuffer) and respawns the
shell, which must answer further commands. A plain `exit` still shows the
old restart notice. Typed over QEMU sendkeys, default shell image, IR and AST.
"""
import os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_shell_boot as sb
import test_shell_disk as sd


def run(ir):
    with tempfile.TemporaryDirectory(prefix='shellrun-'+('ir-' if ir else 'ast-')) as t:
        d = Path(t); kernel, _, uush, hi = sb.build(d, ir)
        iso = sb.package_iso(d, kernel, uush, hi)
        text = sd.boot(d, ['-cdrom', str(iso), '-boot', 'd'], [
            ('run /bin/hi', 'program exit /bin/hi 0'), ('echo alive after run', 'alive after run'),
            ('run /bin/none', 'exec failed'), ('exit', 'shell exit 0')], 'run')
        assert 'hi from exec' in text and text.count('shell start') >= 3, text[-800:]
        assert 'program exit /bin/none' not in text, 'failed exec reported as program exit'
        ev = os.environ.get('HS_SHELL_RUN_EVIDENCE')
        if ev:
            dest = Path(ev)/('ir' if ir else 'ast'); dest.mkdir(parents=True, exist_ok=True)
            for n in ('run.ppm', 'serial', 'qemu.stderr'): shutil.copyfile(d/n, dest/n)
    print('ok shell run returns', 'ir' if ir else 'ast')


if __name__ == '__main__':
    backends = (True, False)
    if '--backend' in sys.argv: backends = (sys.argv[sys.argv.index('--backend')+1] == 'ir',)
    for ir in backends: run(ir)
    print(f'{len(backends)}/{len(backends)} shell run gates')
