#!/usr/bin/env python3
"""Native `hs cc` differential vs the `python3 hs.py cc` oracle.

Builds the real bundle, moves it, then compares the installed `hs cc`
against the Python CLI: exit codes, exact stdout/stderr, and the emitted
static ELF byte-for-byte (both sides run the same selfhost/cc.holy logic, so
a successful compile must produce identical bytes). The Python CLI's compiler
is cc.holy compiled by itself through the interpreter; the bundle's driver is
cc.holy compiled by the hosted native compiler. Their SUCCESS behavior is
identical. Their COMPILE-FAILURE diagnostics differ by executing runtime and
are pinned exactly below (docs/native-install.md documents the deviation):
the self-compiled compiler reports some failures as its own emitted runtime's
uncatchable native faults (fixed `error: <reason>` on stderr, empty stdout),
while the natively compiled driver reports them through the hs-level handler
(the diagnostic on stdout, then `error: compile failed at line N` on stderr
from the native runtime's uncaught-raise line suffix).
"""
from pathlib import Path
import os, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent

# Programs inside the documented cc subset (see tests/test_cc.py).
PROGS = {
    'hello': 'print "hello from cc"\nprint 6 * 7\n',
    'arith': 'a = 17\nb = 5\nprint a + b, a - b, a * b, a % b, -a % b, a % -b, -a % -b\n',
    'bits': 'x = 0xF0F0\nprint x & 255, x | 15, x ^ 255, x << 4, x >> 4, -256 >> 4\n',
    'closure_cap': 'def make(k):\n  def add(x):\n    return x + k\n  return add\nf = make(10)\ng = make(100)\nprint f(5), g(5)\n',
    'strings': 'print "hello, world"\nprint "a", 1, "b"\nprint ""\nprint "tab\\there"\n',
    'mutual': 'def ev(n):\n  if n == 0:\n    return 1\n  return od(n - 1)\ndef od(n):\n  if n == 0:\n    return 0\n  return ev(n - 1)\nprint ev(10), od(7), ev(7)\n',
    'argv': 'print argv()\n',
}
# name -> (source files, expected pinned (python_rc/out/err, native_rc/out/err) or None for success)
FAILS = {
    'float': ('print 1.5 + 2.5\n',
              (1, '', 'error: type error (cc backend)\n'),
              (1, 'error: cc: only Int literals are supported (no Float) (line 1)\n',
               'error: compile failed at line 2546\n')),
    'syntax': ('if\n',
               (1, "error: expression expected, got ''\n", 'error: compile failed\n'),
               (1, "error: expression expected, got '' at line 1\n",
                'error: compile failed at line 2546\n')),
    'missing': (None,
                (1, '', 'error: cannot open file\n'),
                (1, 'error: open failed: errno 2\n',
                 'error: compile failed at line 2546\n')),
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

with tempfile.TemporaryDirectory(prefix='hs native cc ') as temp:
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
    check((moved / 'VERSION').read_bytes() == (ROOT / 'VERSION').read_bytes(),
          'relocated bundle ships VERSION')
    check((moved / 'CC_SHA256SUMS').is_file(), 'relocated bundle ships the compiler manifest')

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', HS_CC_CACHE=str(d / 'py cc cache'))
    env.pop('HSPATH', None); env.pop('HSROOT', None)
    work = d / 'work'; work.mkdir()
    nerr = d / 'native-stderr.txt'

    def pycc(args, cwd):
        r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'cc'] + args, cwd=cwd,
                           capture_output=True, text=True, timeout=120, env=env)
        return r.returncode, r.stdout, r.stderr

    for name, src in PROGS.items():
        case = d / name; case.mkdir()
        (case / 'prog.holy').write_text(src)
        if name == 'argv':
            run_args = ['one', 'two 2']
        else:
            run_args = []
        prc, pout, perr_ = pycc(['prog.holy', '-o', 'py-bin'], case)
        nrc, nout, nerr_text = run_native(launcher, ['cc', 'prog.holy', '-o', 'nv-bin'], case, nerr)
        ok = (prc, pout, perr_) == (nrc, nout, nerr_text) == (0, '', '')
        check(ok, name + ' compile rc/stdout/stderr',
              repr((prc, pout, perr_, nrc, nout, nerr_text))[:400])
        if not (prc == 0 and nrc == 0):
            continue
        same = (case / 'py-bin').read_bytes() == (case / 'nv-bin').read_bytes()
        check(same, name + ' emitted ELF is byte-identical')
        py = subprocess.run([str(case / 'py-bin')] + run_args, capture_output=True, text=True, timeout=30)
        nv = subprocess.run([str(case / 'nv-bin')] + run_args, capture_output=True, text=True, timeout=30)
        check((py.returncode, py.stdout, py.stderr) == (nv.returncode, nv.stdout, nv.stderr),
              name + ' compiled programs behave identically',
              repr((py.returncode, py.stdout, py.stderr, nv.returncode, nv.stdout, nv.stderr))[:400])

    # An importing program compiles against its own directory on both CLIs.
    case = d / 'imports'; case.mkdir()
    (case / 'prog.holy').write_text('import support\nprint support.value\n')
    (case / 'support.holy').write_text('value = 19\n')
    prc, pout, perr_ = pycc(['prog.holy'], case)
    py_default = (case / 'prog').read_bytes() if prc == 0 else b''
    nrc, nout, nerr_text = run_native(launcher, ['cc', 'prog.holy'], case, nerr)
    nv_default = (case / 'prog').read_bytes() if nrc == 0 else b''
    check((prc, pout, perr_) == (nrc, nout, nerr_text) == (0, '', ''),
          'importing program compiles clean on both CLIs',
          repr((prc, pout, perr_, nrc, nout, nerr_text))[:400])
    if prc == 0 and nrc == 0:
        check((case / 'prog').read_bytes() == py_default,
              'default output strips the source extension')
        check(py_default == nv_default and len(nv_default) > 0,
              'importing program ELF is byte-identical')
        r = subprocess.run([str(case / 'prog')], capture_output=True, text=True, timeout=30)
        check((r.returncode, r.stdout) == (0, '19\n'), 'compiled importing program runs',
              repr((r.returncode, r.stdout, r.stderr))[:300])

    # Compile-failure diagnostics differ by executing runtime; pin both.
    for name, (src, pywant, nvwant) in FAILS.items():
        case = d / ('fail-' + name); case.mkdir()
        target = 'prog.holy'
        if src is not None:
            (case / target).write_text(src)
        else:
            target = 'absent.holy'
        pgot = pycc([target], case)
        ngot = run_native(launcher, ['cc', target], case, nerr)
        check(pgot == pywant, name + ' python-side failure pinned',
              repr((pgot, pywant))[:400])
        check(ngot == nvwant, name + ' native-side failure pinned',
              repr((ngot, nvwant))[:400])
        check(pgot[0] == ngot[0], name + ' failure exit codes match')

    # CLI shape parity.
    r = subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'cc'], capture_output=True, text=True, timeout=30, env=env)
    py_noargs = (r.returncode, bool(r.stdout), 'usage:' in r.stderr)
    with open(nerr, 'w') as ef:
        r = subprocess.run([str(launcher), 'cc'], stdout=subprocess.PIPE, stderr=ef, text=True, timeout=10)
    nv_noargs = (r.returncode, bool(r.stdout), 'usage:' in nerr.read_text())
    check(nv_noargs == py_noargs == (2, False, True), 'cc without a source is usage status 2',
          repr((py_noargs, nv_noargs))[:300])

    case = d / 'cli'; case.mkdir()
    (case / 'prog.holy').write_text(PROGS['hello'])
    pycc(['prog.holy', 'junk', '-o', 'placed'], case)
    run_native(launcher, ['cc', 'prog.holy', 'junk', '-o', 'placed2'], case, nerr)
    check((case / 'placed').read_bytes() == (case / 'placed2').read_bytes(),
          '-o anywhere with ignored extra arguments matches the Python CLI')
    r = subprocess.run([str(launcher), '--version'], capture_output=True, text=True, timeout=10)
    check((r.returncode, r.stdout, r.stderr) == (0, 'hs ' + (ROOT / 'VERSION').read_text().strip() + '\n', ''),
          'hs --version prints the bundled version ' + repr((r.returncode, r.stdout, r.stderr)))
    r = subprocess.run([str(launcher), '-V'], capture_output=True, text=True, timeout=10)
    check((r.returncode, r.stdout) == (0, 'hs ' + (ROOT / 'VERSION').read_text().strip() + '\n'),
          'hs -V prints the bundled version')
    r = subprocess.run([str(launcher), 'run', '--version'], capture_output=True, text=True, timeout=10)
    check((r.returncode, r.stdout) == (0, 'hs ' + (ROOT / 'VERSION').read_text().strip() + '\n'),
          '--version after a command still prints the version, like the Python CLI')
    py = subprocess.run([sys.executable, str(ROOT / 'hs.py'), '--version'], capture_output=True, text=True, timeout=30, env=env)
    check((py.returncode, py.stdout) == (0, 'hs ' + (ROOT / 'VERSION').read_text().strip() + '\n'),
          'python3 hs.py --version agrees')

print(f'{passed}/{passed+failed} native cc differential gates')
sys.exit(bool(failed))
