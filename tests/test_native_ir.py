#!/usr/bin/env python3
"""Native `hs ir` differential vs the `python3 hs.py ir` oracle.

Builds the real bundle, moves it, then compares the installed `hs ir`
against the Python CLI: exit codes and exact stdout/stderr. Both sides run
the same pipeline (parse with prelude injection and the range-step/defaults
desugars, build the flat CFG with the hs IR builder, verify it, dump the
canonical text), so successful dumps are byte-identical. Read failures on an
existing but unreadable source differ by executing runtime and are pinned
exactly below (docs/native-install.md documents the deviation): the Python
CLI reports CPython's strerror text (`Is a directory`), while the installed
natively-compiled driver reports the native runtime's errno text
(`read failed: errno 21`). A source whose Int literal exceeds the native
runtime's 62-bit tagged range cannot be lexed by any native driver at all
(native `hs check` fails the same way); both sides are pinned below.
"""
from pathlib import Path
import os, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent

PROGS = {
    'hello': 'print "hello from ir"\nprint 6 * 7\n',
    'defs': 'def greet(name, greeting="hi", punct="!"):\n  return greeting + " " + name + punct\n'
            'print greet("b")\nprint greet("b", "yo")\nprint greet("b", "yo", "?")\n',
    'enum': 'for i, x in enumerate(["a", "b", "c"]):\n  print i, x\n',
    'min2': 'print min(3, 7), max(3, 7)\nprint min([3, 7]), max([3, 7])\n',
    'sorted': 'print sorted([3, 1, 2])\nprint sum([1, 2, 3])\nprint abs(0 - 5)\n',
    'rangestep': 'for i in range(10, 0, -2):\n  print i\nfor i in range(0, 10, 3):\n  print i\n',
    'closure': 'def make(k):\n  def add(x):\n    return x + k\n  return add\n'
               'f = make(10)\nprint f(5)\n',
    'strings': 'print "café", "a\\nb", "tab\\there", "q\\"uote"\n',
    'cls': 'class A:\n  def get(self):\n    return 1\na = A()\nprint a.get()\n',
    'lc': 'print [p[0] + p[1] for p in enumerate([5, 6])]\n',
    'bigfit': 'print 0x0123456789ABCDEF\n',
    'whiletry': 'i = 0\nwhile i < 3:\n  try:\n    if i == 1:\n      raise "one"\n    print i\n'
                '  except as e:\n    print e\n  i = i + 1\n',
}
# Repo regression corpus: the three shapes that need normalization
# (prelude injection, range-step desugar, call-defaults fill).
REPO = ['tests/t_enumerate.holy', 'tests/t_rangestep.holy', 'tests/t_defaults.holy']
# name -> (source, python (rc/out/err), native (rc/out/err)); None source
# means the path stays absent.
FAILS = {
    'missing': (None,
                (1, '', 'error: cannot read absent.holy: No such file or directory\n'),
                (1, '', 'error: cannot read absent.holy: No such file or directory\n')),
    'parse': ('if\n',
              (1, '', "error: expression expected, got '' at line 1\n"),
              (1, '', "error: expression expected, got '' at line 1\n")),
    'break': ('break\n',
              (1, '', 'error: break outside loop at line 1\n'),
              (1, '', 'error: break outside loop at line 1\n')),
    # Deviation: an existing but unreadable source reports each runtime's
    # own read-error text (exit codes match).
    'directory': ('DIR',
                  (1, '', 'error: cannot read adir: Is a directory\n'),
                  (1, '', 'error: cannot read adir: read failed: errno 21\n')),
    # Deviation: a literal outside the native runtime's 62-bit tagged Int
    # range cannot be lexed by any native driver (native `hs check` on the
    # same source fails identically); the Python CLI dumps it.
    'biglit': ('print 0x4000000000000000\n',
               (0, 'func <main>():\nb_entry_0:\n  %1 = const 4611686018427387904 @1\n'
                   '  print %1 @1\n  ret @1\n', ''),
               (97, '', 'error: Int outside the 62-bit range\n')),
}
FAILS_JSON = {
    'missing': ('{"file": "absent.holy", "line": null, '
                '"message": "cannot read absent.holy: No such file or directory"}\n'),
    'parse': ('{"file": "prog.holy", "line": 1, "message": "expression expected, got \'\'", '
              '"code": "E006", "hint": "see the line number in the error"}\n'),
    'break': '{"file": "prog.holy", "line": 1, "message": "break outside loop"}\n',
}

passed = failed = 0
def check(ok, label, detail=''):
    global passed, failed
    passed += int(ok); failed += int(not ok)
    print(('ok  ' if ok else 'FAIL'), label, ('' if ok else detail), flush=True)

def run_native(launcher, args, cwd, nerr):
    with open(nerr, 'w') as ef:
        r = subprocess.run([str(launcher)] + args, cwd=cwd,
                           stdout=subprocess.PIPE, stderr=ef, text=True, timeout=60)
    return r.returncode, r.stdout, nerr.read_text()

with tempfile.TemporaryDirectory(prefix='hs native ir ') as temp:
    d = Path(temp); bindir = d / 'utilities'; bindir.mkdir()
    for name in ['uname', 'dirname', 'sha256sum', 'mktemp', 'rm', 'mkdir', 'cp', 'chmod', 'mv', 'cmp']:
        (bindir / name).symlink_to(shutil.which(name))
    env = dict(os.environ, PATH=str(bindir)); env.pop('HSPATH', None); env.pop('HSROOT', None)
    built = d / 'built'; moved = d / 'moved bundle'
    r = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install-native.sh'), str(built)], env=env,
                       capture_output=True, text=True, timeout=300)
    check(r.returncode == 0, 'bundle build ' + r.stderr[-150:])
    if r.returncode: sys.exit(1)
    built.rename(moved)
    launcher = moved / 'bin/hs'
    check((moved / 'IR_SHA256SUMS').is_file(), 'relocated bundle ships the IR dumper manifest')

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('HSPATH', None); env.pop('HSROOT', None)
    work = d / 'work'; work.mkdir()
    nerr = d / 'native-stderr.txt'

    def pyir(args, cwd):
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'ir'] + args, cwd=cwd,
                           capture_output=True, text=True, timeout=120, env=env)
        return r.returncode, r.stdout, r.stderr

    for name, src in PROGS.items():
        case = d / name; case.mkdir()
        (case / 'prog.holy').write_text(src)
        pgot = pyir(['prog.holy'], case)
        ngot = run_native(launcher, ['ir', 'prog.holy'], case, nerr)
        check(pgot == ngot and pgot[0] == 0, name + ' rc/stdout/stderr identical',
              repr((pgot, ngot))[:400])
        check(pgot[1].endswith('\n') and pgot[1].count('func ') >= 1,
              name + ' dump shape', repr(pgot)[:200])

    for rel in REPO:
        case = d / ('repo-' + Path(rel).stem); case.mkdir()
        shutil.copyfile(ROOT / rel, case / 'prog.holy')
        pgot = pyir(['prog.holy'], case)
        ngot = run_native(launcher, ['ir', 'prog.holy'], case, nerr)
        check(pgot == ngot and pgot[0] == 0, rel + ' identical',
              repr((pgot[0], ngot[0], pgot[2], ngot[2]))[:300])

    for name, (src, pywant, nvwant) in FAILS.items():
        case = d / ('fail-' + name); case.mkdir()
        target = 'prog.holy'
        if src == 'DIR':
            target = 'adir'; (case / 'adir').mkdir()
        elif src is not None:
            (case / target).write_text(src)
        else:
            target = 'absent.holy'
        pgot = pyir([target], case)
        ngot = run_native(launcher, ['ir', target], case, nerr)
        check(pgot == pywant, name + ' python-side pinned', repr((pgot, pywant))[:400])
        check(ngot == nvwant, name + ' native-side pinned', repr((ngot, nvwant))[:400])

    for name, want_err in FAILS_JSON.items():
        case = d / ('fail-' + name)
        target = 'absent.holy' if name == 'missing' else 'prog.holy'
        pgot = pyir(['--json', target], case)
        ngot = run_native(launcher, ['ir', '--json', target], case, nerr)
        check(pgot == (1, '', want_err), name + ' --json python-side pinned',
              repr((pgot, want_err))[:400])
        check(ngot == pgot, name + ' --json identical', repr((ngot, pgot))[:400])

    # CLI shape parity: no source is usage status 2; extras are ignored.
    r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'ir'],
                       capture_output=True, text=True, timeout=30, env=env)
    py_noargs = (r.returncode, bool(r.stdout), 'usage:' in r.stderr)
    with open(nerr, 'w') as ef:
        r = subprocess.run([str(launcher), 'ir'], stdout=subprocess.PIPE, stderr=ef,
                           text=True, timeout=10)
    nv_noargs = (r.returncode, bool(r.stdout), 'usage:' in nerr.read_text())
    check(nv_noargs == py_noargs == (2, False, True), 'ir without a source is usage status 2',
          repr((py_noargs, nv_noargs))[:300])

    case = d / 'cli'; case.mkdir()
    (case / 'prog.holy').write_text(PROGS['hello'])
    pgot = pyir(['prog.holy'], case)
    ngot = run_native(launcher, ['ir', 'prog.holy', 'junk', 'more'], case, nerr)
    check(ngot == pgot, 'extra arguments ignored like the Python CLI',
          repr((ngot, pgot))[:300])

print(passed, 'passed,', failed, 'failed')
sys.exit(1 if failed else 0)
