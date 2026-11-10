#!/usr/bin/env python3
"""Native `hs check` differential vs the `python3 hs.py check` oracle.

Builds the real bundle, moves it, then compares the installed `hs check`
against the Python CLI over a curated valid/invalid matrix: exit codes,
stdout, exact text errors, and the JSON file/line/message fields. The JSON
error catalog's optional code/hint fields are a documented follow-up: the
native object must not emit them yet, and comparison covers the three base
fields only. Driver stderr goes to a temp file so the suite is independent
of how the runner wires standard error.
"""
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parent.parent

CASES = []
def case(name, files, main, hspath=(), effects=False):
    CASES.append(dict(name=name, files=files, main=main, hspath=hspath, effects=effects))

# Accepted by Python check, including its documented baseline quirks.
case('ok_simple', {'m.holy': 'print "hi"\n'}, 'm.holy')
case('ok_unknown_name', {'m.holy': 'print missing_name\n'}, 'm.holy')
case('ok_http_get', {'m.holy': 'print http_get("https://example.com")\n'}, 'm.holy')
case('ok_bare_raise', {'m.holy': 'raise\n'}, 'm.holy')
case('ok_def_after_use', {'m.holy': 'print f()\ndef f():\n  return 1\n'}, 'm.holy')
case('ok_missing_module_attr', {'m.holy': 'import mod\nprint mod.nope\n', 'mod.holy': 'x = 3\n'}, 'm.holy')
case('ok_circular', {'m.holy': 'import a\nprint "main"\n', 'a.holy': 'import b\nprint "a"\n', 'b.holy': 'import a\nprint "b"\n'}, 'm.holy')
case('ok_hspath', {'m.holy': 'import libmod\nprint libmod.v\n', 'libs/libmod.holy': 'v = 7\n'}, 'm.holy', hspath=('libs',))
case('ok_hs_suffix', {'m.holy': 'import util\nprint util.v\n', 'util.hs': 'v = 8\n'}, 'm.holy')
case('ok_unsafe', {'m.holy': 'unsafe:\n  Ptr p = alloc(8)\n  store8(p, 1)\n  print load8(p)\n'}, 'm.holy')
case('ok_extern_ffi', {'m.holy': 'extern:\n  I64 puts(Str s)\nputs("x")\n'}, 'm.holy')
case('ok_struct_sizeof', {'m.holy': 'unsafe:\n  struct Probe:\n    I64 a\n    I64 b\nx = sizeof(Probe)\n'}, 'm.holy')
case('ok_closure', {'m.holy': 'def f():\n  x = 1\n  def g():\n    return x\n  return g\nprint f()()\n'}, 'm.holy')
case('ok_class', {'m.holy': 'class A:\n  def m(self):\n    return 1\nprint A().m()\n'}, 'm.holy')
case('ok_sugar', {'m.holy': 'f = lambda x: x + 1\nxs = [i * 2 for i in range(3)]\nname = "w"\nprint f"hi {name} {f(1)} {1 if true else 2}"\n'}, 'm.holy')
case('ok_defaults', {'m.holy': 'def f(a, b=2):\n  return a + b\nprint f(1)\n'}, 'm.holy')
case('ok_dotted_import', {'m.holy': 'import sub.leaf\nprint sub.leaf.v\n', 'sub/leaf.holy': 'v = 9\n'}, 'm.holy')
case('ok_mixed', {'m.holy': 'q = 0\ndef bump():\n  global q\n  q = q + 1\nfor i in range(3):\n  bump()\nwhile q < 5:\n  bump()\nif q == 5:\n  print {"k": [q]}\nelif q > 5:\n  pass\nelse:\n  print "no"\ntry:\n  raise "e"\nexcept as err:\n  print err\nfinally:\n  print "done"\n'}, 'm.holy')
case('ok_nested_import_dir', {'sub/main.holy': 'import helper\nprint helper.v\n', 'sub/helper.holy': 'v = 11\n'}, 'sub/main.holy')
case('ok_module_reimport', {'m.holy': 'import mod\nimport mod\nprint mod.x\n', 'mod.holy': 'x = 3\n'}, 'm.holy')
# Dogfooding: the checker checks its own source and import graph.
case('ok_self_check', {}, str(ROOT / 'selfhost/check.holy'),
     hspath=(str(ROOT / 'selfhost'), str(ROOT / 'selfhost/be'), str(ROOT / 'std')))

# Rejected by Python check: rc 1 and identical file/line/message.
case('err_parse_root', {'m.holy': 'def broken(:\n'}, 'm.holy')
case('err_missing_import', {'m.holy': 'import no_such_module_zz\nprint "x"\n'}, 'm.holy')
case('err_parse_in_module', {'m.holy': 'import badmod\nprint "x"\n', 'badmod.holy': 'def broken(:\n'}, 'm.holy')
case('err_dup_udecl', {'m.holy': 'unsafe:\n  I64 x\n  I64 x\n'}, 'm.holy')
case('err_unsafe_call', {'m.holy': 'unsafe:\n  print len([1])\n'}, 'm.holy')
case('err_extern_shadow_builtin', {'m.holy': 'extern:\n  I64 print(Str s)\n'}, 'm.holy')
case('err_extern_dup', {'m.holy': 'extern:\n  I64 f(Str s)\nextern:\n  I64 f(Str s)\n'}, 'm.holy')
case('err_ffi_missing_src', {'m.holy': 'extern from "missing_zz.c":\n  I64 f()\n'}, 'm.holy')
case('err_ffi_missing_lib', {'m.holy': 'extern from "missing_zz.so":\n  I64 f()\n'}, 'm.holy')
case('err_asm_outside', {'m.holy': 'asm("nop")\n'}, 'm.holy')
case('err_asm_bad_form', {'m.holy': 'unsafe:\n  asm(1)\n'}, 'm.holy')
case('err_ffi_arity', {'m.holy': 'extern:\n  I64 f(I64 a, I64 b)\nf(1)\n'}, 'm.holy')
case('err_slice_unsafe', {'m.holy': 'unsafe:\n  Ptr p = alloc(8)\n  x = p[0:1]\n'}, 'm.holy')
case('err_attr_unsafe', {'m.holy': 'unsafe:\n  Ptr p = alloc(8)\n  y = p.foo\n'}, 'm.holy')
case('err_unknown_struct', {'m.holy': 'x = sizeof(Nope)\n'}, 'm.holy')
case('err_ucapture', {'m.holy': 'def f():\n  unsafe:\n    I64 q = 0\n  def g():\n    return q\n'}, 'm.holy')
case('err_global_unsafe', {'m.holy': 'unsafe:\n  I64 q = 0\ndef f():\n  global q\n  q = 1\n'}, 'm.holy')
case('err_set_imported', {'m.holy': 'import mod\nmod = 3\n', 'mod.holy': 'x = 3\n'}, 'm.holy')
case('err_def_collision', {'m.holy': 'import mod\ndef mod():\n  pass\n', 'mod.holy': 'x = 3\n'}, 'm.holy')
case('err_import_after_assign', {'m.holy': 'x = 1\nimport x\n', 'x.holy': 'v = 2\n'}, 'm.holy')
case('err_udecl_global', {'m.holy': 'def f():\n  global q\n  unsafe:\n    I64 q\n'}, 'm.holy')
case('err_extern_in_unsafe', {'m.holy': 'unsafe:\n  extern:\n    I64 f()\n'}, 'm.holy')
case('err_def_in_unsafe', {'m.holy': 'unsafe:\n  def f():\n    pass\n'}, 'm.holy')
case('err_for_unsafe', {'m.holy': 'unsafe:\n  for i in range(3):\n  pass\n'}, 'm.holy')
case('err_bad_extern_type', {'m.holy': 'extern:\n  Nope f()\n'}, 'm.holy')
case('err_struct_redefine', {'m.holy': 'unsafe:\n  struct S:\n    I64 a\n  struct S:\n    U64 b\n'}, 'm.holy')
case('err_nested_module_error', {'m.holy': 'import mid\n', 'mid.holy': 'import badmod\n', 'badmod.holy': 'def broken(:\n'}, 'm.holy')

# Checking never executes the target or its imports.
case('fx_no_effects', {'m.holy': 'print "TARGET RAN"\nwrite_text("EFFECT_MARK", "x")\nsystem("touch EFFECT_MARK2")\nimport modwrite\n', 'modwrite.holy': 'print "MODULE RAN"\nwrite_text("EFFECT_MARK3", "x")\n'}, 'm.holy', effects=True)

passed = failed = 0
def check(ok, label, detail=''):
    global passed, failed
    passed += int(ok); failed += int(not ok)
    print(('ok  ' if ok else 'FAIL'), label, ('' if ok else detail), flush=True)

with tempfile.TemporaryDirectory(prefix='hs native check ') as temp:
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
    for c in CASES:
        cdir = d / 'cases' / c['name']; cdir.mkdir(parents=True)
        for rel, content in c['files'].items():
            p = cdir / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content)
        main = Path(c['main']); main = main if main.is_absolute() else cdir / main
        hspath = ':'.join(str(Path(h) if Path(h).is_absolute() else cdir / h) for h in c['hspath'])
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        if hspath: env['HSPATH'] = hspath
        else: env.pop('HSPATH', None)
        for as_json in (False, True):
            flag = ['--json'] if as_json else []
            py = subprocess.run([sys.executable, str(ROOT / 'hs.py')] + flag + ['check', str(main)], cwd=cdir, env=env, capture_output=True, text=True, timeout=60)
            nerr = cdir / 'native-stderr.txt'
            with open(nerr, 'w') as ef:
                nv = subprocess.run([str(launcher)] + flag + ['check', str(main)], cwd=cdir, env=env, stdout=subprocess.PIPE, stderr=ef, text=True, timeout=60)
            nerr_text = nerr.read_text()
            label = c['name'] + (' --json' if as_json else '')
            ok = py.returncode == nv.returncode and py.stdout == nv.stdout
            if as_json:
                pj = nvj = None
                try: pj = json.loads(py.stderr)
                except Exception: pass
                try: nvj = json.loads(nerr_text)
                except Exception: pass
                if py.returncode == 0:
                    ok = ok and py.stderr == '' and nerr_text == ''
                else:
                    ok = ok and pj is not None and nvj is not None
                    if pj and nvj:
                        ok = ok and all(pj.get(k) == nvj.get(k) for k in ('file', 'line', 'message'))
                        # Documented gap: catalog code/hint parity is a follow-up.
                        ok = ok and 'code' not in nvj and 'hint' not in nvj
            else:
                ok = ok and py.stderr == nerr_text
            check(ok, label, repr((py.returncode, nv.returncode, py.stdout, nv.stdout, py.stderr, nerr_text))[:400])
        if c['effects']:
            for mark in ('EFFECT_MARK', 'EFFECT_MARK2', 'EFFECT_MARK3'):
                check(not (cdir / mark).exists(), c['name'] + ' no ' + mark)
print(f'{passed}/{passed+failed} native check differential gates')
sys.exit(bool(failed))
