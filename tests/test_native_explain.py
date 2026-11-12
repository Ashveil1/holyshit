#!/usr/bin/env python3
"""Native `hs explain` differential vs the `python3 hs.py explain` oracle.

Builds the real bundle, moves it, then compares the installed `hs explain`
against the Python CLI over every catalog pattern (instantiated with a sample
wildcard value), error-prefix/line-suffix variants and edge cases: exit
codes, exact stdout/stderr, text and --json modes. The catalog ships inside
the relocated bundle (docs/errors.md), so coverage includes relocation.
"""
from pathlib import Path
import os, re, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent

def corpus():
    rows = []
    for ln in (ROOT / 'docs/errors.md').read_text(encoding='utf-8').split('\n'):
        m = re.match(r"^\| `(E\d+)` \| `(.+?)` \| (.+?) \| (.+?) \|$", ln)
        if m:
            rows.append(m.group(2))
            continue
        m = re.match(r"^- `(.+)`$", ln)
        if m:
            rows.append(m.group(1))
    msgs = []
    for p in rows:
        msgs.append(re.sub(r"\{[^}]*\}|<[^>]*>", "ZZ", p))
    for p in rows[:50]:
        msgs.append("error: " + re.sub(r"\{[^}]*\}|<[^>]*>", "ZZ", p) + " at line 7")
    msgs += ["totally unmatchable qwerty", "E001", "E012", "E999", "x", "",
             "at line 5", "error:", "cannot add Int and Str extra suffix"]
    seen = set()
    out = []
    for m in msgs:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out

passed = failed = 0
def check(ok, label, detail=''):
    global passed, failed
    passed += int(ok); failed += int(not ok)
    print(('ok  ' if ok else 'FAIL'), label, ('' if ok else detail), flush=True)

with tempfile.TemporaryDirectory(prefix='hs native explain ') as temp:
    d = Path(temp); bindir = d / 'utilities'; bindir.mkdir()
    for name in ['uname', 'dirname', 'sha256sum', 'mktemp', 'rm', 'mkdir', 'cp', 'chmod', 'mv', 'cmp']:
        (bindir / name).symlink_to(shutil.which(name))
    env = dict(os.environ, PATH=str(bindir)); env.pop('HSPATH', None); env.pop('HSROOT', None)
    built = d / 'built'; moved = d / 'moved bundle'
    r = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install-native.sh'), str(built)], env=env, capture_output=True, text=True, timeout=300)
    check(r.returncode == 0, 'bundle build ' + r.stderr[-150:])
    if r.returncode: sys.exit(1)
    built.rename(moved)
    launcher = moved / 'bin/hs'
    check((moved / 'docs/errors.md').read_bytes() == (ROOT / 'docs/errors.md').read_bytes(),
          'relocated bundle ships the error catalog')
    check((moved / 'docs/for-agents.md').read_bytes() == (ROOT / 'docs/for-agents.md').read_bytes(),
          'relocated bundle ships the agent doc the catalog points at')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('HSPATH', None); env.pop('HSROOT', None)
    nerr = d / 'native-stderr.txt'
    for msg in corpus():
        for as_json in (False, True):
            flag = ['--json'] if as_json else []
            py = subprocess.run([sys.executable, str(ROOT / 'hs.py')] + flag + ['explain', msg],
                                capture_output=True, text=True, timeout=60)
            with open(nerr, 'w') as ef:
                nv = subprocess.run([str(launcher)] + flag + ['explain', msg],
                                    stdout=subprocess.PIPE, stderr=ef, text=True, timeout=60)
            nerr_text = nerr.read_text()
            label = repr(msg) + (' --json' if as_json else '')
            ok = (py.returncode == nv.returncode and py.stdout == nv.stdout and py.stderr == nerr_text)
            check(ok, label, repr((py.returncode, nv.returncode, py.stdout, nv.stdout, py.stderr, nerr_text))[:400])
    # The Python CLI joins argv words with spaces; --json is global.
    py = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'explain', 'cannot', 'add', 'Int', 'and', 'Str'],
                        capture_output=True, text=True, timeout=60)
    with open(nerr, 'w') as ef:
        nv = subprocess.run([str(launcher), 'explain', 'cannot', 'add', 'Int', 'and', 'Str'],
                            stdout=subprocess.PIPE, stderr=ef, text=True, timeout=60)
    check(py.returncode == nv.returncode and py.stdout == nv.stdout and py.stderr == nerr.read_text(),
          'multi-word message joins like the Python CLI')
    py = subprocess.run([sys.executable, str(ROOT / 'hs.py'), '--json', 'explain', 'index out of range'],
                        capture_output=True, text=True, timeout=60)
    with open(nerr, 'w') as ef:
        nv = subprocess.run([str(launcher), 'explain', '--json', 'index out of range'],
                            stdout=subprocess.PIPE, stderr=ef, text=True, timeout=60)
    check(py.returncode == nv.returncode and py.stdout == nv.stdout and py.stderr == nerr.read_text(),
          '--json after the command matches --json before it')
    r = subprocess.run(['/bin/sh', str(launcher), 'explain'], capture_output=True, text=True, timeout=10)
    check(r.returncode == 2 and not r.stdout and 'usage:' in r.stderr, 'explain requires a message')
print(f'{passed}/{passed+failed} native explain differential gates')
sys.exit(bool(failed))
