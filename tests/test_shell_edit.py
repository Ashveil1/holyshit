#!/usr/bin/env python3
"""In-shell line editor (B23b): `edit FILE` creates, lists, saves and edits files.

Typed over QEMU sendkeys into the default shell image: create a two-line file,
save, reopen it, delete a line, save, discard a change. Output is asserted on
the serial byte log and the framebuffer screendump is kept for inspection.
IR and AST kernel backends.
"""
import contextlib, io, os, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_shell_boot as sb
import test_shell_disk as sd
ROOT = sb.ROOT
from x64gen import build_x64, build_xkernel
ED = 'ed> '


def run(ir):
    with tempfile.TemporaryDirectory(prefix='shelledit-'+('ir-' if ir else 'ast-')) as t:
        d = Path(t); kernel, _, uush, hi = sb.build(d, ir)
        iso = sb.package_iso(d, kernel, uush, hi)
        a = ['-cdrom', str(iso), '-boot', 'd']
        text = sd.boot(d, a, [
            ('edit /e', 'edit /e', ED), ('alpha beta', 'ed> ', ED), ('gamma', 'ed> ', ED),
            ('.list', '2: gamma', ED), ('.save', 'saved 2 lines'), ('cat /e', 'sh> '),
            ('edit /e', 'edit /e', ED), ('.list', '1: alpha beta', ED), ('.del 2', 'ed> ', ED),
            ('.save', 'saved 1 lines'), ('cat /e', 'sh> '),
            ('edit /e', 'edit /e', ED), ('zzz', 'ed> ', ED), ('.quit', 'discarded'), ('cat /e', 'sh> ')], 'edit')
        first, rest = text.split('saved 2 lines', 1)
        assert '\nalpha beta\ngamma\n' in rest, rest[:600]
        after_del = rest.split('saved 1 lines', 1)[1]
        assert 'alpha beta' in after_del and 'gamma' not in after_del.split('edit /e')[0], after_del[:400]
        assert 'zzz' not in after_del.split('discarded', 1)[1], 'discarded edit leaked'
        ev = os.environ.get('HS_SHELL_EDIT_EVIDENCE')
        if ev:
            dest = Path(ev)/('ir' if ir else 'ast'); dest.mkdir(parents=True, exist_ok=True)
            for n in ('edit.ppm', 'serial', 'qemu.stderr'): shutil.copyfile(d/n, dest/n)
    print('ok shell line editor', 'ir' if ir else 'ast')


if __name__ == '__main__':
    backends = (True, False)
    if '--backend' in sys.argv: backends = (sys.argv[sys.argv.index('--backend')+1] == 'ir',)
    for ir in backends: run(ir)
    print(f'{len(backends)}/{len(backends)} shell editor gates')
