#!/usr/bin/env python3
"""claimview-0b slice 1: agent/relindex.holy on every hosted execution route.
The same op script (random lifecycle with non-ASCII keys, fail-closed fault
injection, readers, canon) runs as an embedded-script program on the reference
interp, reference-ir, ir-x64, ast-x64, seed-native, hs-interpreter and gcc-native
and each output must equal the native stdin driver output, which
test_claim_view_0b_relindex.py checks against the Oracle model."""
import contextlib, io, json, os, platform, random, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import interp, ir, x64gen
env = dict(os.environ, HSROOT=str(ROOT), HSPATH=os.pathsep.join([str(ROOT), str(ROOT/'selfhost'), str(ROOT/'selfhost/be')]))
DRV = (ROOT/'tests/claimview/relindex_driver.holy').read_text(encoding='utf-8')
prelude = DRV.split('# --- loop ---')[0]

VOC = ['a robin', 'robin', 'Robin', '  ROBIN ', 'นก', 'นก  ตัว', 'bird', 'A Bird']
PRE = ['is-a', 'has', 'is-in', 'means']
def tup(rng): return [rng.choice(VOC), rng.choice(PRE), rng.choice(VOC), '1' if rng.random() < .3 else '0']
ops = [['new']]
for seed in range(3):
    rng = random.Random(100 + seed)
    ops.append(['new'])
    for _ in range(50):
        k = rng.random(); t = tup(rng)
        if k < .45: ops.append(['add'] + t)
        elif k < .65: ops.append(['remove'] + t)
        elif k < .75: ops.append(['drop', t[0]])
        elif k < .85: ops.append(['load'] + sum([tup(rng) for _ in range(rng.randint(0, 5))], []))
        else: ops.append(['rebuild'])
        ops.append(['dump'])
base = [['new'], ['load', 'a robin', 'is-a', 'a bird', '0', 'robin', 'has', 'wings', '0']]
for kind in ('missing', 'stale', 'count', 'droptuple', 'swap'):
    ops += base + [['break', kind, 'robin'], ['check'], ['add', 'x', 'is-a', 'y', '0'], ['remove', 'robin', 'has', 'wings', '0'],
                   ['drop', 'robin'], ['dump'], ['reads', 'robin'], ['rebuild'], ['check'], ['dump']]
ops += [['loadbad', 'q', 'w', 'e'], ['canon', '  A  Robin'], ['canon', 'นก  ตัว'], ['canon', 'Ünï  X'], ['count']]
lines = ['\t'.join(o) for o in ops]
text = prelude + 'OPS = ' + json.dumps(ops, ensure_ascii=False) + '\nfor f in OPS:\n  step(f)\n'

with tempfile.TemporaryDirectory(prefix='hs-ri-') as tmp:
    d = Path(tmp)
    exe = d/'drv'
    r = subprocess.run([sys.executable, str(ROOT/'hs.py'), 'build', str(ROOT/'tests/claimview/relindex_driver.holy'), '-o', str(exe)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    expected = subprocess.run([str(exe)], input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=120).stdout
    assert expected.count('\n') > 400, expected[-300:]
    source = d/'chat.holy'
    source.write_text(text, encoding='utf-8')

    def verify(label, r):
        assert r.returncode == 0, (label, r.returncode, r.stderr[-1500:])
        assert not r.stderr, (label, r.stderr[-1500:])
        assert r.stdout == expected, (label, r.stdout[-800:], expected[-800:])
        print('ok relindex', label, expected.count('\n'), 'output lines', flush=True)

    verify('reference', subprocess.run([sys.executable, str(ROOT/'interp.py'), str(source)], env=env, capture_output=True, text=True, timeout=300))
    old = os.environ.get('HSPATH'); os.environ['HSPATH'] = env['HSPATH']
    try:
        interp.reset_parse_state()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ir.run_module(ir.build_module(interp.parse_program(text)), str(d))
        verify('reference-ir', subprocess.CompletedProcess([], 0, out.getvalue(), ''))
        runner = []
        if platform.machine() not in ('x86_64', 'amd64'):
            q = shutil.which('qemu-x86_64')
            if not q:
                print('skip: qemu-x86_64 unavailable'); raise SystemExit(0)
            runner = [q]
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
        r = subprocess.run(runner + [str(ROOT/'bootstrap/hs-hosted-x86_64'), str(src), str(image)], env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0 and image.exists(), (label, r.stdout[-500:], r.stderr[-500:])
        cmd = runner + [str(image)]
        if label == 'hs-interpreter': cmd.append(str(source))
        verify(label, subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120))
    if '--skip-gcc' not in sys.argv:
        verify('gcc-native', subprocess.run([sys.executable, str(ROOT/'hs.py'), 'run', str(source), '--backend', 'native'], env=env, capture_output=True, text=True, timeout=180))
print('7/7 relindex execution routes byte-identical' if '--skip-gcc' not in sys.argv else '6/6')
