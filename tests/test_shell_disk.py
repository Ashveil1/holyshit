#!/usr/bin/env python3
"""Persistent shell (B23): files written at the shell and `sync`ed survive reboot.

Explicit `shell-disk` target over a disposable QEMU IDE disk (never the
default image, no real-hardware disk support). Three boots of one disk:
blank (mkdir/write/sync typed at the shell), restored (the files read back
and the packaged /bin is intact), and no disk at all (RAM-only, sync
refuses). The saved volume must also stay small: /bin is never serialized.
IR and AST kernel backends; the IR leg builds through the packaging script
and proves its kernel is byte-identical to the reference build.
"""
import contextlib, io, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gui_session import qemu
import test_shell_boot as sb
ROOT = sb.ROOT
from x64gen import build_x64, build_xkernel
KEYMAP = dict(sb.KEYMAP, **{'.': 'dot', '-': 'minus'})


def boot(d, args, script, shot):
    serial = d/'serial'; qmp = d/'qmp'; serial.unlink(missing_ok=True); qmp.unlink(missing_ok=True)
    err = (d/'qemu.stderr').open('wb')
    p = subprocess.Popen([qemu, '-m', '256M', '-nic', 'none', '-display', 'none',
        '-serial', 'file:'+str(serial), '-qmp', 'unix:'+str(qmp)+',server=on,wait=off'] + args, stderr=err)
    def out(): return serial.read_text(errors='replace') if serial.exists() else ''
    def wait_for(test, label, seconds=60):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            if test(): return
            assert p.poll() is None, ('QEMU exited', out()[-2000:])
            time.sleep(.05)
        raise AssertionError((label, out()[-2000:]))
    try:
        wait_for(lambda: 'sh> ' in out(), 'shell prompt')
        time.sleep(2)
        s = socket.socket(socket.AF_UNIX); s.settimeout(10); s.connect(str(qmp))
        f = s.makefile('rwb', buffering=0); json.loads(f.readline())
        def cmd(name, cargs=None):
            req = {'execute': name}
            if cargs is not None: req['arguments'] = cargs
            f.write(json.dumps(req).encode()+b'\r\n')
            while True:
                r = json.loads(f.readline()); assert 'error' not in r, r
                if 'return' in r: return r['return']
        cmd('qmp_capabilities')
        def h(c):
            r = cmd('human-monitor-command', {'command-line': c}); assert not r, (c, r)
        for line, expect in script:
            n = out().count('sh> ')
            for ch in line: h('sendkey '+KEYMAP.get(ch, ch)); time.sleep(0.6)
            h('sendkey ret')
            wait_for(lambda: expect in out(), 'output of '+line, 40)
            wait_for(lambda: out().count('sh> ') > n, 'prompt after '+line, 40)
            time.sleep(0.5)
        text = out(); assert 'EXC ' not in text, text[-2000:]
        h('screendump '+str(d/(shot+'.ppm')))
        return text
    finally:
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill()
        err.close()


def build(d, ir):
    kernel = d/'kernel.elf'; uush = d/'uush.elf'; hi = d/'hi.elf'
    with contextlib.redirect_stdout(io.StringIO()):
        assert build_xkernel(str(ROOT/'kernel/kshelldisk.holy'), str(kernel), ir_backend=ir) == 0
        assert build_x64(str(ROOT/'kernel/uush.holy'), str(uush)) == 0
        assert build_x64(str(ROOT/'kernel/uuhi.holy'), str(hi)) == 0
    if ir:
        subprocess.run([str(ROOT/'scripts/build-gui-iso.sh'), str(d/'script.iso'), 'shell-disk'],
                       env=sb.ENV, check=True, capture_output=True, timeout=300)
        subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(d/'script.iso'),
                        '-extract', '/boot/kernel.elf', str(d/'script-kernel.elf')],
                       env=sb.ENV, check=True, capture_output=True, timeout=30)
        assert (d/'script-kernel.elf').read_bytes() == kernel.read_bytes(), 'packaged shell-disk kernel differs'
        return d/'script.iso'
    return sb.package_iso(d, kernel, uush, hi)


def run(ir):
    with tempfile.TemporaryDirectory(prefix='shelldisk-'+('ir-' if ir else 'ast-')) as t:
        d = Path(t); iso = build(d, ir)
        disk = d/'disk.img'; disk.write_bytes(bytes(2*1024*1024))
        a = ['-cdrom', str(iso), '-boot', 'd', '-drive', 'file='+str(disk)+',if=ide,format=raw']
        one = boot(d, a, [('mkdir /home', 'sh> '), ('write /home/a hello disk', 'sh> '),
                          ('sync', 'synced')], 'blank')
        assert 'SHELL VOLUME 0' in one, one[-1500:]
        raw = disk.read_bytes(); assert raw[:4] == b'KVOL', 'sync wrote no volume'
        assert len(raw) == 2*1024*1024
        used = max(i for i, b in enumerate(raw) if b) + 1
        assert used < 4096, ('volume holds more than user files (/bin leaked?)', used)
        sb_save(d, 'blank', ir)
        two = boot(d, a, [('cat /home/a', 'hello disk'), ('ls /bin', 'uush'), ('write /home/b two', 'sh> '),
                          ('sync', 'synced')], 'restored')
        assert 'SHELL VOLUME 6' in two, two[-1500:]
        assert disk.read_bytes()[:4] == b'KVOL'
        sb_save(d, 'restored', ir)
        three = boot(d, a, [('cat /home/b', 'two')], 'second')
        sb_save(d, 'second', ir)
        none = boot(d, ['-cdrom', str(iso), '-boot', 'd'], [('sync', 'sync failed')], 'nodisk')
        assert 'SHELL VOLUME -1' in none, none[-1500:]
        sb_save(d, 'nodisk', ir)
    print('ok persistent shell', 'ir' if ir else 'ast')


def sb_save(d, label, ir):
    ev = os.environ.get('HS_SHELL_DISK_EVIDENCE')
    if ev:
        dest = Path(ev)/(('ir-' if ir else 'ast-')+label); dest.mkdir(parents=True, exist_ok=True)
        for n in (label+'.ppm', 'serial', 'qemu.stderr'): shutil.copyfile(d/n, dest/n)


if __name__ == '__main__':
    backends = (True, False)
    if '--backend' in sys.argv: backends = (sys.argv[sys.argv.index('--backend')+1] == 'ir',)
    for ir in backends: run(ir)
    print(f'{len(backends)}/{len(backends)} shell disk gates')
