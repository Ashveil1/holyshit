#!/usr/bin/env python3
"""Translate/adapt the CFG verifier, then install a formatted candidate.

Formatting validates syntax/format only, not semantics, CHK equivalence or
identity with the maintained verifier. Review the regeneration diff: even a
successfully formatted candidate can drift from the maintained implementation.
"""
import ast
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from py2hs import translate


def adapt(s):
    s=s.replace('l = py_pop(stack)', 'l = stack[len(stack) - 1]\n    stack = stack[0:len(stack) - 1]')
    s=s.replace('(intersections([dom[p] for p in ps]) | py_set([l]))', 'py_union(intersections([dom[p] for p in ps]), py_set([l]))')
    s=s.replace('      new = (py_union(intersections([dom[p] for p in ps]), py_set([l])) if ps else py_set([l]))', '''      ds = []
      for p in keys(ps):
        append(ds, dom[p])
      new = py_set([l])
      if len(ds) > 0:
        new = py_union(intersections(ds), new)''')
    s=re.sub(r'\bpy_(\w+)\(',r'pyrt.py_\1(',s)
    s += '''

def intersections(sets):
  if len(sets) == 0:
    return {}
  out = {}
  for k in keys(sets[0]):
    yes = true
    for d in sets:
      if not has(d, k):
        yes = false
    if yes:
      out[k] = true
  return out
'''
    return 'import pyrt\n\n' + s


def candidate(root):
    m = ast.parse((root / 'ir.py').read_text())
    items = [n for n in m.body if isinstance(n, ast.FunctionDef) and 831 <= n.lineno < 1037]
    s = ast.unparse(ast.Module(body=items, type_ignores=[]))
    s = s.replace('set.intersection(*(dom[p] for p in ps))', 'intersections([dom[p] for p in ps])')
    with tempfile.TemporaryDirectory(prefix='mkverify-') as td:
        source = pathlib.Path(td) / 'verify-source.py'
        raw = pathlib.Path(td) / 'verify-raw.holy'
        source.write_text(s)
        errs = translate([str(source)], str(raw), str(root / 'x64.py'))
        if errs:
            raise SystemExit(str(errs))
        return adapt(raw.read_text())


def install(root, target, text):
    """Failure-atomic installation, not a semantic regeneration check."""
    mode = stat.S_IMODE(target.stat().st_mode)
    fd, name = tempfile.mkstemp(prefix='.mkverify-', suffix='.holy', dir=target.parent)
    stage = pathlib.Path(name)
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(text)
        subprocess.run([sys.executable, str(root / 'hs.py'), 'fmt', str(stage), '-w'], check=True)
        stage.chmod(mode)
        os.replace(stage, target)
    finally:
        stage.unlink(missing_ok=True)


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    install(root, root / 'selfhost/be/verify.holy', candidate(root))


if __name__ == '__main__':
    main()
