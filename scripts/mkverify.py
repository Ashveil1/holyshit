#!/usr/bin/env python3
"""Translate the CFG verifier, adapting Python sets to explicit maps."""
import ast
import pathlib
import re
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from py2hs import translate
root=pathlib.Path(__file__).resolve().parent.parent
m=ast.parse((root/'ir.py').read_text())
items=[n for n in m.body if isinstance(n,ast.FunctionDef) and 831<=n.lineno<1037]
s=ast.unparse(ast.Module(body=items,type_ignores=[]))
s=s.replace('set.intersection(*(dom[p] for p in ps))', 'intersections([dom[p] for p in ps])')
p=pathlib.Path('/tmp/verify-source.py');p.write_text(s)
errs=translate([str(p)],'/tmp/verify-raw.holy',str(root/'x64.py'))
if errs:raise SystemExit(str(errs))
s=pathlib.Path('/tmp/verify-raw.holy').read_text()
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
(root/'selfhost/be/verify.holy').write_text('import pyrt\n\n'+s)
import subprocess
subprocess.run([sys.executable,str(root/'hs.py'),'fmt',str(root/'selfhost/be/verify.holy'),'-w'],check=True)
