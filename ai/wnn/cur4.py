"""P12b / level 4: (a) learn div (quotient <=9) as a counting loop on learned sub/cmp,
(b) learn lcm as a straight-line composition of learned mul, div, gcd.
Usage: python3 cur4.py [removed_ops]   (learned programs are cached in /tmp/progs4.json)"""
import sys, json, os, random, time, itertools
import cur3 as K
from cur3 import *
CACHE = '/tmp/progs4.json'
def lcm_data(rng, n):
    import math
    g = rng.randrange(1, 10 ** max(1, n // 2)); p = rng.randrange(1, 10 ** max(1, n - n // 2)); q = rng.randrange(1, 10 ** max(1, n - n // 2))
    if rng.random() < .3: g = 1
    a, b = g * p, g * q
    return a, b, a * b // math.gcd(a, b)
def learn(name, ops):
    c = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    if name in c: return tuple(tuple(x) if isinstance(x, list) else x for x in c[name]) if False else json.loads(json.dumps(c[name]), object_hook=None)
    prog, res, tried, dt = K.search(name, ops)
    if not prog: return None
    t = test(name, prog, res)
    print(name, 'FOUND', show(prog[2]), show(prog[3]), show(prog[4]), 'inits', prog[0], prog[1], 'res', res, 'tried', tried, 'unseen', t, flush=True)
    c[name] = [prog, res]; json.dump(c, open(CACHE, 'w'))
    return [prog, res]
def tup(e): return tuple(tup(x) for x in e) if isinstance(e, list) else e
if __name__ == '__main__':
    ablate = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] else []
    K.MUL, K.MOD = relearn_level2()
    K.INITL = ('x', 'y', 'one', 'zero')
    ops = {'add', 'sub', 'mul', 'mod', 'shift', 'cmp'}
    fns = {}
    for name in ('div', 'gcd'):
        K.INITL = ('x', 'y', 'one', 'zero') if name == 'div' else ('x', 'y', 'one')
        r = learn(name, ops - ({'sub'} if False else set()))
        assert r, name + ' not learned'
        prog, res = tup(r[0]), r[1]
        fns[name] = (lambda p, rs: (lambda a, b: run_prog(p, a, b, 400)[rs]))(prog, res)
    # straight-line search over learned ops
    def lib(name):
        return {'mul': lambda a, b: K.MUL(a, b), 'div': lambda a, b: fns['div'](a, b), 'gcd': lambda a, b: fns['gcd'](a, b)}[name]
    use = [o for o in ('mul', 'div', 'gcd') if o not in ablate]
    rng = random.Random(5); train = [lcm_data(rng, rng.choice([1, 2])) for _ in range(25)]
    leaves = ['x', 'y']; lvl = [(l, 1) for l in leaves]; tried = 0
    def ev(e, a, b):
        if isinstance(e, str): return a if e == 'x' else b
        return lib(e[0])(ev(e[1], a, b), ev(e[2], a, b))
    E = list(leaves)
    for size in range(2):
        new = [(o, p, q) for o in use for p in E for q in E if p != q or o == 'mul']
        E = E + [e for e in new if e not in E]
    found = None
    for e in E:
        tried += 1
        try:
            if all(d2n(ev(e, n2d(a), n2d(b))) == r for a, b, r in train): found = e; break
        except Exception: pass
    if not found: print('lcm ops-removed', ablate, 'NOT FOUND, exprs tried', tried); sys.exit()
    rng = random.Random(777); out = {}
    for n in (2, 4, 6, 8):
        ok = 0
        for _ in range(40):
            a, b, r = lcm_data(rng, n)
            try: ok += d2n(ev(found, n2d(a), n2d(b))) == r
            except Exception: pass
        out[n] = ok
    print('lcm ops-removed', ablate, 'FOUND', found, 'exprs tried', tried, 'unseen', out)
