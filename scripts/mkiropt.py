#!/usr/bin/env python3
"""Translate and adapt the small reference CFG optimizer."""
import pathlib
import sys
import re
import ast
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from py2hs import translate
root = pathlib.Path(__file__).resolve().parent.parent
mod = ast.parse((root/'iropt.py').read_text())
# Python's dict.clear/update changes the instruction in place. hs has no
# dict deletion, so replace the owning instruction list element instead.
for fn in mod.body:
    if isinstance(fn, ast.FunctionDef) and fn.name == 'optimize_func':
        loop = fn.body[2].body[0]
        loop.target = ast.Tuple(elts=[ast.Name(id='ii', ctx=ast.Store()), ast.Name(id='ins', ctx=ast.Store())], ctx=ast.Store())
        loop.iter = ast.Call(func=ast.Name(id='enumerate', ctx=ast.Load()), args=[loop.iter], keywords=[])
class ReplaceClear(ast.NodeTransformer):
    def visit_Expr(self, n):
        if isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == 'ins':
            if n.value.func.attr == 'clear':
                return None
            if n.value.func.attr == 'update':
                return ast.Assign(targets=[ast.Subscript(value=ast.Subscript(value=ast.Name(id='b', ctx=ast.Load()), slice=ast.Constant('instrs'), ctx=ast.Load()), slice=ast.Name(id='ii', ctx=ast.Load()), ctx=ast.Store())], value=n.value.args[0])
        return n
mod = ReplaceClear().visit(mod)
ast.fix_missing_locations(mod)
src = pathlib.Path('/tmp/iropt-source.py')
src.write_text(ast.unparse(mod))
errs = translate([str(src)], '/tmp/iropt-raw.hs', str(root/'x64.py'))
if errs: raise SystemExit(str(errs))
s = pathlib.Path('/tmp/iropt-raw.hs').read_text()
s = re.sub(r'\bpy_(\w+)\(', r'pyrt.py_\1(', s)
s = s.replace('(type(v) == int_)', '(pyrt.py_type(v) == "int")')
s = s.replace('pyrt.py_get(os.environ, "HS_NOOPT", null)', 'env("HS_NOOPT")')
# The Python oracle has unbounded intermediate arithmetic. Avoid wrapping
# an overflowing product into the foldable 62-bit interval in hs.
s = s.replace('r = (a * b)', 'return bounded_mul(a, b)')
s = s.replace('r = (a + b)', 'return bounded_add(a, b)')
s = s.replace('r = (a - b)', 'return bounded_sub(a, b)')
s += '''

def bounded_add(a, b):
  if b > 0 and a >= LIM - b:
    return null
  if b < 0 and a <= (0 - LIM) - b:
    return null
  r = a + b
  if r <= (0 - LIM) or r >= LIM:
    return null
  return r

def bounded_sub(a, b):
  if b > 0 and a <= (0 - LIM) + b:
    return null
  if b < 0 and a >= LIM + b:
    return null
  r = a - b
  if r <= (0 - LIM) or r >= LIM:
    return null
  return r

def bounded_mul(a, b):
  if a == 0 or b == 0:
    return 0
  if a <= (0 - LIM) or a >= LIM or b <= (0 - LIM) or b >= LIM:
    return null
  neg = false
  if a < 0:
    neg = not neg
  if b < 0:
    neg = not neg
  if a < 0:
    a = 0 - a
  if b < 0:
    b = 0 - b
  r = 0
  while b > 0:
    if b & 1:
      if r >= LIM - a:
        return null
      r = r + a
    b = b >> 1
    if b > 0:
      if a >= LIM - a:
        return null
      a = a + a
  return (0 - r) if neg else r
'''
(root/'selfhost/be/iropt.hs').write_text('import pyrt\n\n'+s)
import subprocess
subprocess.run([sys.executable, str(root/'hs.py'), 'fmt', str(root/'selfhost/be/iropt.hs'), '-w'], check=True)
