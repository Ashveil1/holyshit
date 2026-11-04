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
    union = '(intersections(_mkverify_domsets) | py_set([l]))'
    if s.count(union) != 1:
        raise ValueError('mkverify: expected exactly one naive union spelling')
    s = s.replace(union, 'py_union(intersections(_mkverify_domsets), py_set([l]))')
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



def adapt_need_naive(module):
    """Lower only the oracle's pure local membership scan, not generic any().

    The full scan has the same boolean as short-circuit any here because
    reach/preds are local sets with side-effect-free membership/lookups.
    """
    expected = ast.parse('need_naive = any(p not in reach for l in reach for p in preds[l])').body[0]
    assignments = [n for n in ast.walk(module) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'need_naive' for t in n.targets)]
    if len(assignments) != 1 or ast.dump(assignments[0]) != ast.dump(expected):
        raise ValueError('mkverify: expected exactly one exact need_naive assignment')
    original = assignments[0]
    replacement = ast.parse('need_naive = False\nfor l in reach:\n    for p in preds[l]:\n        if p not in reach:\n            need_naive = True\n').body
    class Splice(ast.NodeTransformer):
        count = 0
        def visit_Assign(self, node):
            if node is original:
                self.count += 1
                return replacement
            return node
    splice = Splice()
    module = splice.visit(module)
    if splice.count != 1:
        raise ValueError('mkverify: need_naive splice count mismatch')
    return ast.fix_missing_locations(module)


def adapt_dominance(module):
    """Exact local list reversal and pure predecessor-set intersection only."""
    funcs = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == '_verify_func']
    if len(funcs) != 1:
        raise ValueError('mkverify: expected unique _verify_func')
    fn = funcs[0]
    fresh = '_mkverify_domsets'
    if any(isinstance(n, ast.Name) and n.id == fresh for n in ast.walk(fn)):
        raise ValueError('mkverify: fresh dominance local collision')
    reverse = ast.parse('rpo = order[::-1]').body[0]
    naive = ast.parse('new = (set.intersection(*(dom[p] for p in ps)) | {l}) if ps else {l}').body[0]
    # The source contract puts the assignment in the need_naive fallback's
    # changed fixpoint/label loop. Bind that whole branch, not a text indent.
    branches = [n for n in ast.walk(fn) if isinstance(n, ast.If)
                and isinstance(n.test, ast.Name) and n.test.id == 'need_naive']
    if len(branches) != 1:
        raise ValueError('mkverify: expected unique need_naive fallback')
    branch = branches[0]
    expected_branch = ast.parse('if need_naive:\n    dom = {l: set(labels) for l in labels}\n    dom[fn["entry"]] = {fn["entry"]}\n    changed = True\n    while changed:\n        changed = False\n        for l in labels:\n            if l == fn["entry"]:\n                continue\n            ps = preds[l]\n            new = (set.intersection(*(dom[p] for p in ps)) | {l}) if ps else {l}\n            if new != dom[l]:\n                dom[l] = new\n                changed = True\n').body[0]
    actual_branch = ast.If(test=branch.test, body=branch.body, orelse=[])
    if ast.dump(actual_branch) != ast.dump(expected_branch):
        raise ValueError('mkverify: naive fallback shape changed')
    reverses = [n for n in ast.walk(fn) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'rpo' for t in n.targets)]
    naives = [n for n in ast.walk(branch) if ast.dump(n) == ast.dump(naive)]
    if (len(reverses) != 1 or ast.dump(reverses[0]) != ast.dump(reverse)
            or reverses[0] not in list(ast.walk(ast.Module(body=branch.orelse, type_ignores=[])))
            or len(naives) != 1):
        raise ValueError('mkverify: expected unique scoped reverse/naive assignment')
    replacements = {
        id(reverses[0]): ast.parse('rpo = list(reversed(order))').body,
        id(naives[0]): ast.parse('_mkverify_domsets = []\nfor p in ps:\n    _mkverify_domsets.append(dom[p])\nnew = {l}\nif len(_mkverify_domsets) > 0:\n    new = intersections(_mkverify_domsets) | {l}\n').body,
    }
    class Splice(ast.NodeTransformer):
        count = 0
        def visit_Assign(self, node):
            if id(node) in replacements:
                self.count += 1
                return replacements[id(node)]
            return node
    splice = Splice()
    splice.visit(fn)
    if splice.count != 2:
        raise ValueError('mkverify: dominance splice count mismatch')
    return ast.fix_missing_locations(module)


def select_verifier(module):
    items = [n for n in module.body if isinstance(n, ast.FunctionDef) and 831 <= n.lineno < 1037]
    helpers = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == '_need']
    expected = ast.parse('def _need(by, lab, tm): pass').body[0].args
    if (len(helpers) != 1 or helpers[0] in items or helpers[0].decorator_list
            or ast.dump(helpers[0].args) != ast.dump(expected)):
        raise ValueError('mkverify: expected one disjoint _need(by, lab, tm) helper')
    items += helpers
    names = [n.name for n in items]
    if len(names) != 3 or set(names) != {'verify_module', '_verify_func', '_need'}:
        raise ValueError('mkverify: unexpected verifier selection')
    return items


def candidate(root):
    m = ast.parse((root / 'ir.py').read_text())
    items = select_verifier(m)
    s = ast.unparse(adapt_dominance(adapt_need_naive(ast.Module(body=items, type_ignores=[]))))
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
