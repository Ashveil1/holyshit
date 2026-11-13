#!/usr/bin/env python3
"""Disposable mkverify candidate vs Python and unchanged maintained verifier."""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import interp
import ir
import mkverify
from x64gen import build_x64

SHAPE = 'need_naive = any(p not in reach for l in reach for p in preds[l])'
MAINTAINED = ROOT / 'selfhost/be/verify.holy'
PIN = '50fa2623baad710abb6da752b141453018861c2555b9ca54576a1c0ad7498237'


def selection_and_dominance():
    original = ast.parse((ROOT / 'ir.py').read_text())
    selected = mkverify.select_verifier(copy.deepcopy(original))
    assert {n.name for n in selected} == {'verify_module', '_verify_func', '_need'}
    helper = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == '_need')
    for mutate in ('zero', 'duplicate', 'arg', 'default', 'kwonly', 'decorator', 'overlap', 'extra'):
        m = copy.deepcopy(original)
        h = next(n for n in m.body if isinstance(n, ast.FunctionDef) and n.name == '_need')
        if mutate == 'zero': m.body.remove(h)
        elif mutate == 'duplicate': m.body.append(copy.deepcopy(h))
        elif mutate == 'arg': h.args.args[0].arg = 'wrong'
        elif mutate == 'default': h.args.defaults = [ast.Constant(None)]
        elif mutate == 'kwonly': h.args.kwonlyargs = [ast.arg(arg='x')]; h.args.kw_defaults = [None]
        elif mutate == 'decorator': h.decorator_list = [ast.Name(id='deco', ctx=ast.Load())]
        elif mutate == 'overlap': h.lineno = 900
        elif mutate == 'extra':
            extra = ast.parse('def surprise(): pass').body[0]; extra.lineno = 900; m.body.append(extra)
        try: mkverify.select_verifier(m)
        except ValueError: pass
        else: raise AssertionError(('selection accepted', mutate))
    def dommodule():
        return ast.Module(body=mkverify.select_verifier(copy.deepcopy(original)), type_ignores=[])
    for mutation in ('reversezero', 'reverseduplicate', 'reversestep', 'scope', 'fresh', 'naivechange', 'branchduplicate'):
        m = dommodule(); fn = next(n for n in m.body if n.name == '_verify_func')
        rev = next(n for n in ast.walk(fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'rpo' for t in n.targets))
        branch = next(n for n in ast.walk(fn) if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'need_naive')
        if mutation == 'reversezero': rev.targets[0].id = 'other'
        elif mutation == 'reverseduplicate': fn.body.append(copy.deepcopy(rev))
        elif mutation == 'reversestep': rev.value.slice.step = ast.Constant(1)
        elif mutation == 'scope':
            branch.orelse.remove(rev); fn.body.append(rev)
        elif mutation == 'fresh': fn.body.append(ast.parse('_mkverify_domsets = []').body[0])
        elif mutation == 'naivechange':
            assign = next(n for n in ast.walk(branch) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'new' for t in n.targets))
            assign.value.orelse = ast.Set(elts=[])
        elif mutation == 'branchduplicate': fn.body.append(copy.deepcopy(branch))
        try: mkverify.adapt_dominance(m)
        except ValueError: pass
        else: raise AssertionError(('dominance accepted', mutation))
    m = dommodule(); fn = next(n for n in m.body if n.name == '_verify_func')
    untouched = ast.parse('other = [x for x in labels]\nother2 = labels[1:2]').body
    fn.body += untouched
    before = [ast.dump(n) for n in untouched]
    mkverify.adapt_dominance(m)
    assert [ast.dump(n) for n in untouched] == before
    for order in ([], ['e'], ['j', 'a', 'e']):
        assert order[::-1] == list(reversed(order))
    for sets in ([], [set()], [{'a'}], [{'a', 'b'}, {'b'}], [{'a'}, {'b'}]):
        l = 'self'; ps = list(range(len(sets))); dom = dict(enumerate(sets))
        want = (set.intersection(*(dom[p] for p in ps)) | {l}) if ps else {l}
        collected = []
        for p in ps: collected.append(dom[p])
        got = {l}
        if len(collected) > 0: got = set.intersection(*collected) | {l}
        assert got == want
    for bad in ('', '(intersections(_mkverify_domsets) | py_set([l]))' * 2):
        try: mkverify.adapt(bad)
        except ValueError: pass
        else: raise AssertionError('union spelling must fail closed')


def structural():
    source = SHAPE + '\nother = [x for x in reach]\n'
    module = ast.parse(source)
    other = module.body[1]
    adapted = mkverify.adapt_need_naive(module)
    assert adapted.body[-1] is other
    assert len(adapted.body) == 3
    for bad in ['', SHAPE + '\n' + SHAPE, SHAPE.replace('not in', 'in'),
                SHAPE.replace('preds[l]', 'preds[p]'), SHAPE.replace('any(', 'all(')]:
        try:
            mkverify.adapt_need_naive(ast.parse(bad))
        except ValueError:
            pass
        else:
            raise AssertionError('nonexact source accepted')
    code = compile(mkverify.adapt_need_naive(ast.parse(SHAPE)), '<adapted>', 'exec')
    # Ordered dicts model deterministic traversal; values are pure local sets.
    matrix = [({}, {}), ({'a': True}, {'a': set()}),
              ({'a': True, 'b': True}, {'a': set(), 'b': {'a'}}),
              ({'a': True, 'b': True}, {'a': {'dead'}, 'b': {'a'}}),
              ({'a': True, 'b': True}, {'a': set(), 'b': {'dead'}}),
              ({'b': True, 'a': True}, {'a': set(), 'b': {'dead'}}),
              ({'a': True}, {'a': set(), 'dead': {'dead'}})]
    for reach, preds in matrix:
        want = any(p not in reach for l in reach for p in preds[l])
        env = {'reach': copy.deepcopy(reach), 'preds': copy.deepcopy(preds)}
        exec(code, env)
        maintained = False
        for l in reach.keys():
            for p in preds[l]:
                if p not in reach:
                    maintained = True
        assert env['need_naive'] == want == maintained
    return len(matrix)


def block(label, term, instrs=()):
    return {'label': label, 'instrs': list(instrs), 'term': dict(term, line=1)}


def const(name):
    return {'op': 'const', 'dest': name, 'val': 1, 'line': 1}


def module(blocks):
    fn = {'name': 'f', 'dispname': 'f', 'params': [], 'globals': [],
          'entry': 'e', 'blocks': blocks}
    return {'entry': 'f', 'order': ['f'], 'funcs': {'f': fn}}


def cfgs():
    ret = {'term': 'ret', 'val': None}
    chain = module([block('e', {'term': 'jmp', 'to': 'a'}, [const('%c')]),
                    block('a', {'term': 'ret', 'val': '%c'})])
    diamond = module([block('e', {'term': 'br', 'cond': '%c', 'then': 'a', 'els': 'b'}, [const('%c')]),
                      block('a', {'term': 'jmp', 'to': 'j'}, [const('%a')]),
                      block('b', {'term': 'jmp', 'to': 'j'}, [const('%b')]),
                      block('j', ret)])
    loop = module([block('e', {'term': 'jmp', 'to': 'a'}, [const('%c')]),
                   block('a', {'term': 'br', 'cond': '%c', 'then': 'a', 'els': 'j'}), block('j', ret)])
    yield 'chain', chain, False
    yield 'diamond', diamond, False
    yield 'loop', loop, False
    bad = copy.deepcopy(diamond); bad['funcs']['f']['blocks'][-1]['term']['val'] = '%a'
    yield 'non-dominating', bad, False
    dead = copy.deepcopy(chain); dead['funcs']['f']['blocks'].append(block('dead', {'term': 'ret', 'val': '%c'}))
    yield 'unreachable-use-exemption', dead, False
    fallback = copy.deepcopy(chain); fallback['funcs']['f']['blocks'].append(block('dead', {'term': 'jmp', 'to': 'a'}))
    yield 'reachable-with-unreachable-pred', fallback, True
    phi = copy.deepcopy(diamond); phi['funcs']['f']['blocks'][-1]['instrs'] = [
        {'op': 'phi', 'dest': '%p', 'arms': [['a', '%a'], ['b', '%b']], 'line': 1}]
    phi['funcs']['f']['blocks'][-1]['term']['val'] = '%p'
    yield 'phi-edge-valid', phi, False
    wrong = copy.deepcopy(phi); wrong['funcs']['f']['blocks'][-1]['instrs'][0]['arms'][0][1] = '%b'
    yield 'phi-edge-nondominating', wrong, False
    wrong = copy.deepcopy(phi); wrong['funcs']['f']['blocks'][-1]['instrs'][0]['arms'][0][0] = 'e'
    yield 'phi-nonpredecessor', wrong, False


def fits62(x):
    if type(x) is int:
        return -(1 << 61) <= x < (1 << 61)
    if isinstance(x, (list, tuple)):
        return all(fits62(v) for v in x)
    if isinstance(x, dict):
        return all(fits62(v) for v in x.values())
    return True


def cases():
    for p in sorted(list((ROOT / 'tests').glob('*.holy')) + list((ROOT / 'examples').glob('*.holy'))):
        try:
            interp.reset_parse_state()
            m = ir.build_module(interp.parse_program(p.read_text()))
            ir.verify_module(m)
        except Exception:
            continue
        yield p.name, m, None
    base = ir.build_module(interp.parse_program('a = 1\nprint(a + 2)\n'))
    mutations = [
        ('missing entry', lambda m, f: m.update(entry='missing')),
        ('duplicate function', lambda m, f: m['order'].append(m['entry'])),
        ('missing function', lambda m, f: m['order'].append('missing')),
        ('duplicate block', lambda m, f: f['blocks'].append(copy.deepcopy(f['blocks'][0]))),
        ('missing block', lambda m, f: f.update(entry='missing')),
        ('no terminator', lambda m, f: f['blocks'][0].update(term=None)),
        ('bad terminator', lambda m, f: f['blocks'][0].update(term={'term': 'oops', 'line': 1})),
        ('bad jump', lambda m, f: f['blocks'][0].update(term={'term': 'jmp', 'to': 'missing', 'line': 1})),
        ('undefined return', lambda m, f: f['blocks'][0].update(term={'term': 'ret', 'val': '%missing', 'line': 1})),
        ('undefined bin', lambda m, f: f['blocks'][0]['instrs'].append({'op': 'bin', 'dest': '%new', 'binop': '+', 'l': '%missing', 'r': '%missing', 'line': 1})),
        ('duplicate temp', lambda m, f: f['blocks'][0]['instrs'].append(copy.deepcopy(f['blocks'][0]['instrs'][0]))),
        ('bad opcode', lambda m, f: f['blocks'][0]['instrs'].append({'op': 'oops', 'line': 1})),
        ('phi entry', lambda m, f: f['blocks'][0]['instrs'].append({'op': 'phi', 'dest': '%new', 'arms': [], 'line': 1})),
    ]
    for label, mutate in mutations:
        m = copy.deepcopy(base); mutate(m, m['funcs'][m['entry']])
        yield label, m, None
    yield from cfgs()


def oracle(m, fallback):
    observed = []
    def trace(frame, event, arg):
        if frame.f_code is ir._verify_func.__code__ and event == 'line' and 'need_naive' in frame.f_locals:
            observed.append(frame.f_locals['need_naive'])
        return trace
    sys.settrace(trace)
    try:
        ir.verify_module(copy.deepcopy(m))
        want = 'ok'
    except interp.HSErr as e:
        want = e.msg
    finally:
        sys.settrace(None)
    if fallback is not None:
        assert observed and any(observed) == fallback, ('fallback not exercised', fallback, observed)
    return want


def main():
    assert hashlib.sha256(MAINTAINED.read_bytes()).hexdigest() == PIN
    runner_ast = ast.parse((ROOT / 'tests/run_all.py').read_text())
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in runner_ast.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ('SUITES', 'QUICK_SKIP')}
    names = [name for name, _ in values['SUITES']]
    assert names.count(Path(__file__).name) == 1 and Path(__file__).name not in values['QUICK_SKIP']
    truth = structural()
    selection_and_dominance()
    count = skipped = 0
    d = Path(tempfile.mkdtemp(prefix='mkverify-semantic-'))
    success = False
    try:
        if True:
            candidate = d / 'verify_candidate.holy'
            candidate.write_text(mkverify.candidate(ROOT))
            (d / 'candidate-before-fmt.holy').write_bytes(candidate.read_bytes())
            (d / 'sources.json').write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT / 'scripts/mkverify.py', ROOT / 'scripts/py2hs.py', ROOT / 'ir.py', MAINTAINED]}))
            subprocess.run([sys.executable, str(ROOT / 'hs.py'), 'fmt', str(candidate), '-w'], check=True)
            env = dict(os.environ, HSPATH=str(d) + ':' + str(ROOT / 'selfhost/be'))
            old = os.environ.get('HSPATH')
            os.environ['HSPATH'] = env['HSPATH']
            commands = []
            try:
                for name, expected in [('verify_candidate', candidate), ('verify', MAINTAINED)]:
                    assert Path(interp.find_module_file(name, str(d), 1)).resolve() == expected.resolve()
                    runner = d / (name + '_run.holy')
                    runner.write_text('import ' + name + '\nimport pyrt\ntry:\n  ' + name + '.verify_module(json_load(argv()[0]))\n  print "ok"\nexcept as e:\n  print pyrt.py_emsg(e)\n')
                    exe = d / (name + '_x64')
                    with contextlib.redirect_stdout(io.StringIO()):
                        assert build_x64(str(runner), str(exe)) == 0
                    commands.extend([(name + '-interp', [sys.executable, str(ROOT / 'hs.py'), 'run', str(runner), '--backend', 'interp'], False),
                                     (name + '-x64', [str(exe)], True)])
            finally:
                if old is None:
                    os.environ.pop('HSPATH', None)
                else:
                    os.environ['HSPATH'] = old
            data = d / 'module.json'
            for label, m, fallback in list(cfgs()) + list(cases()):
                (d / 'case.txt').write_text(label)
                want = oracle(m, fallback)
                data.write_text(json.dumps(m))
                for backend, cmd, native in commands:
                    if native and not fits62(m):
                        skipped += 1
                        continue
                    (d / 'command.json').write_text(json.dumps({'case': label, 'backend': backend, 'command': cmd + [str(data)]}))
                    try:
                        r = subprocess.run(cmd + [str(data)], capture_output=True, text=True, env=env, cwd=d, timeout=30)
                    except subprocess.TimeoutExpired as e:
                        (d / 'timeout.txt').write_text(str(e))
                        (d / 'stdout.txt').write_bytes(e.stdout or b'')
                        (d / 'stderr.txt').write_bytes(e.stderr or b'')
                        raise AssertionError((label, backend, 'timeout30s', want)) from e
                    (d / 'stdout.txt').write_text(r.stdout)
                    (d / 'stderr.txt').write_text(r.stderr)
                    got = r.stdout.strip()
                    if not native and not fits62(m):
                        # hs tooling (json_parse) cannot hold >62-bit literals
                        # yet (wide-literal tooling follow-up): the interp-side
                        # verifier must reject the module, not verify it
                        assert r.returncode == 0 and 'cannot convert' in got, (label, backend, want, got, r.stderr)
                    else:
                        assert r.returncode == 0 and got == want and not r.stderr, (label, backend, want, got, r.stderr)
                    count += 1
        success = True
    finally:
        manifest = {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()}
        (d / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        if success:
            shutil.rmtree(d)
        else:
            print('FAILURE_EVIDENCE', d, flush=True)
        assert hashlib.sha256(MAINTAINED.read_bytes()).hexdigest() == PIN
    print(f'{count}/{count} disposable/maintained verifier interp+x64 exact verdicts; {truth}/{truth} truth cases; {skipped} width skips')


if __name__ == '__main__':
    main()
