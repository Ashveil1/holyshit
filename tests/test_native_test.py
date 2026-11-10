#!/usr/bin/env python3
"""Native `hs test` differential vs the `python3 hs.py test` oracle.

Builds the real bundle, moves it, then compares the installed `hs test`
against the Python CLI over a curated corpus: exit codes and exact stdout
for both text and --json modes, covering discovery order, selection rules,
crash and parse errors, imports, state sharing, marker spoofing and missing
files. The one intentional deviation is pinned: a file using unsafe runs
under the CPython interpreter but is reported failed with the hs
interpreter's refusal line by the native driver.
"""
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent

FIXTURES = {
    "basic/test_basic.holy": 'x = 1\ndef test_add():\n  assert x + 1 == 2\ndef test_fail():\n  assert 1 == 2, "one is not two"\ndef test_str():\n  assert "a" + "b" == "ab"\n',
    "basic/t_other.hs": 'def test_hs():\n  assert 2 * 3 == 6\n',
    "basic/nottests.holy": 'def test_skip():\n  assert false\n',
    "basic/sub/test_deep.holy": 'def test_deep():\n  assert len([1, 2]) == 2\n',
    "basic/sub/t_mod.holy": 'def helper():\n  return 41\n',
    "basic/test_crash.holy": 'raise "boom at top"\ndef test_never():\n  pass\n',
    "basic/test_parse.holy": 'def broken(:\n',
    "basic/test_sel.holy": 'def test_with_param(a):\n  assert false\ntest_lam = lambda: 1\ndef test_default(a=1):\n  assert false\ndef test_ok():\n  assert true\n',
    "basic/test_dup.holy": 'def test_same():\n  assert true\ndef test_same():\n  assert false, "second one"\n',
    "basic/test_bare.holy": 'def test_bare_assert():\n  assert 1 == 2\n',
    "basic/test_msg.holy": 'def test_spaces():\n  raise "custom error with spaces"\n',
    "basic/test_state.holy": 'counter = 0\ndef test_first():\n  global counter\n  counter = counter + 1\n  assert counter == 1\ndef test_second():\n  global counter\n  counter = counter + 1\n  assert counter == 2\n',
    "basic/test_import.holy": 'import sub.t_mod\ndef test_imp():\n  assert sub.t_mod.helper() == 41\n',
    "basic/test_spoof.holy": 'def test_real():\n  print "@@hs-test ok test_fake"\n',
    "deep/a/b/c/test_z.holy": 'def test_z():\n  assert true\n',
    "deep/a/test_y.holy": 'def test_y():\n  assert true\n',
    "deep/test_x.holy": 'def test_x():\n  assert true\n',
    "empty/test_none.holy": 'def helper():\n  pass\n',
    "unsafe/test_unsafe.holy": 'def test_ptr():\n  unsafe:\n    Ptr p = alloc(8)\n    store8(p, 7)\n    store8(p, load8(p))\n',
}

CASES = [
    ["basic/test_basic.holy"],
    ["basic"],
    ["basic/"],
    ["deep"],
    ["empty"],
    ["emptydir"],
    ["basic/test_sel.holy", "basic/test_dup.holy"],
    ["basic/test_bare.holy", "basic/test_msg.holy", "basic/test_state.holy"],
    ["basic/test_import.holy"],
    ["basic/test_spoof.holy"],
    ["missing.holy"],
    ["-q", "basic/t_other.hs"],
    ["basic/test_basic.holy", "deep"],
]

passed = failed = 0
def check(ok, label, detail=''):
    global passed, failed
    passed += int(ok); failed += int(not ok)
    print(('ok  ' if ok else 'FAIL'), label, ('' if ok else detail), flush=True)

with tempfile.TemporaryDirectory(prefix='hs native test ') as temp:
    d = Path(temp); bindir = d / 'utilities'; bindir.mkdir()
    for name in ['uname', 'dirname', 'sha256sum', 'mktemp', 'rm', 'mkdir', 'cp', 'chmod', 'mv', 'cmp', 'find']:
        (bindir / name).symlink_to(shutil.which(name))
    env = dict(os.environ, PATH=str(bindir)); env.pop('HSPATH', None); env.pop('HSROOT', None)
    built = d / 'built'; moved = d / 'moved bundle'
    r = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install-native.sh'), str(built)], env=env, capture_output=True, text=True, timeout=300)
    check(r.returncode == 0, 'bundle build ' + r.stderr[-150:])
    if r.returncode: sys.exit(1)
    built.rename(moved)
    launcher = moved / 'bin/hs'
    base = d / 'corpus'; base.mkdir()
    (base / 'emptydir').mkdir()
    for rel, content in FIXTURES.items():
        p = base / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content)
    for args in CASES:
        for as_json in (False, True):
            flag = ['--json'] if as_json else []
            py = subprocess.run([sys.executable, str(ROOT / 'hs.py')] + flag + ['test'] + args,
                                cwd=base, capture_output=True, text=True, timeout=120)
            nv = subprocess.run([str(launcher)] + flag + ['test'] + args,
                                cwd=base, capture_output=True, text=True, timeout=120)
            label = ' '.join(args) + (' --json' if as_json else '')
            check(py.returncode == nv.returncode and py.stdout == nv.stdout, label,
                  repr((py.returncode, nv.returncode, py.stdout[:300], nv.stdout[:300], nv.stderr[-150:])))
    # Pinned deviation: unsafe runs under the CPython interpreter; the native
    # driver's hs interpreter subset refuses it before running (rc 3 text as
    # the failure line), matching the documented irinterp subset.
    py = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'test', 'unsafe'], cwd=base, capture_output=True, text=True, timeout=120)
    nv = subprocess.run([str(launcher), 'test', 'unsafe'], cwd=base, capture_output=True, text=True, timeout=120)
    check(py.returncode == 0 and 'ok   unsafe/test_unsafe.holy::test_ptr' in py.stdout
          and nv.returncode == 1 and 'irinterp: unsupported' in nv.stdout and '0 passed, 1 failed' in nv.stdout,
          'pinned deviation: unsafe refused natively, runs under Python',
          repr((py.returncode, py.stdout[:200], nv.returncode, nv.stdout[:300])))
print(f'{passed}/{passed+failed} native test differential gates')
sys.exit(bool(failed))
