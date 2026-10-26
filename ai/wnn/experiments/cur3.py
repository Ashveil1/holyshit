"""Curriculum level 3: loops over TWO state variables, built from LEVEL-2 learned skills (mul, mod) found by cur2.
GIVEN: WHILE skeleton `state=(s0,s1) <- inits; while cond(state): state <- (u0(state), u1(state))`; result = s0 or s1;
       constants one=[1], zero=[0]; glue as in cur2. LEARNED: the level-1 procedures (add, sub, mul1, shift, compare),
       level-2 skills (mul = Horner fold, mod = while-subtract; re-learned here by cur2's search), and level 3:
       inits, condition, and the two updates by enumeration (gcd, power).
python3 cur3.py TASKS [ops-to-remove]"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import sys, time, random, itertools
import induce as I, cur2 as C
from cur2 import n2d, d2n, strip, show
P = {'add': ('bwd', 'bwd', 'tape+r', I.fn('((x+(r+y))%10)'), I.fn('((x+(r+y))//10)')),
     'sub': ('bwd', 'bwd', 'tape', I.fn('(((x-y)-r)%10)'), I.fn('(1 if (x-y)<r else 0)')),
     'mul1': ('bwd', 'bwd', 'tape+r', I.fn('((r+(x*y))%10)'), I.fn('((r+(x*y))//10)')),
     'shift': ('fwd', 'fwd', 'tape+r', I.fn('x'), I.fn('y')),
     'compare': ('bwd', 'fwd', 'final', I.fn('r'), I.fn('(1 if (y-x)<r else 0)'))}
L = C.Lib(P)
def cached(fn):
    d = {}
    def g(*a):
        k = tuple(tuple(x) if isinstance(x, list) else x for x in a)
        if k not in d: d[k] = fn(*a)
        return list(d[k]) if isinstance(d[k], list) else d[k]
    return g
def relearn_level2():
    ops = {'add', 'sub', 'mul1', 'shift', 'cmp', 'ite'}
    fm, *_ = C.run_task('mul', L, ops); fd_, *_ = C.run_task('mod', L, ops)
    assert fm and fd_, 'level-2 skills not found'
    em = fm[1]; c, e = fd_[1], fd_[2]
    print('level-2 learned: mul =', show(em), '(fold over digits of y);  mod = while', show(c), ':', show(e), flush=True)
    def mul(a, b):
        acc = [0]
        for d in b: acc = C.ev(em, {'acc': acc, 'x': a, 'y': b, 'one': [1], 'd': d}, L)
        return acc
    def mod(a, b):
        acc = list(a); k = 0
        while C.ev(c, {'acc': acc, 'x': a, 'y': b, 'one': [1]}, L):
            acc = C.ev(e, {'acc': acc, 'x': a, 'y': b, 'one': [1]}, L); k += 1
            if k > 3000: raise ValueError('too many')
        return acc
    return cached(mul), cached(mod)
MUL = MOD = None
INITL = ('x', 'y', 'one')
def ev3(e, env):
    if isinstance(e, str): return env[e]
    o = e[0]
    if o == 'add': return L.add(ev3(e[1], env), ev3(e[2], env))
    if o == 'sub': return L.sub(ev3(e[1], env), ev3(e[2], env))
    if o == 'mul': return MUL(ev3(e[1], env), ev3(e[2], env))
    if o == 'mod': return MOD(ev3(e[1], env), ev3(e[2], env))
    if o == 'shift': return L.shift(ev3(e[1], env))
    if o == 'cmp': return L.cmp(ev3(e[1], env), ev3(e[2], env))
    if o == 'not': return 1 - ev3(e[1], env)
def run_prog(prog, x, y, maxsteps=12):
    i0, i1, cond, u0, u1 = prog
    env = {'x': x, 'y': y, 'one': [1], 'zero': [0]}
    s = [ev3(i0, env), ev3(i1, env)]; k = 0
    while True:
        env['s0'], env['s1'] = s
        if not ev3(cond, env): return s
        s = [ev3(u0, env), ev3(u1, env)]; k += 1
        if k > maxsteps: raise ValueError('loop')
def data(name, rng, n):
    if name == 'div':
        y = rng.randrange(1, 10**n); q = rng.randrange(0, 10); r = rng.randrange(y)
        return y * q + r, y, q
    if name == 'gcd':
        import math
        g = rng.randrange(1, 10**max(1, n // 2)); p = rng.randrange(1, 10**max(1, n - n // 2)); q = rng.randrange(1, 10**max(1, n - n // 2))
        if rng.random() < .3: g = 1
        a, b = g * p, g * q
        return a, b, math.gcd(a, b)
    x = rng.randrange(1, 10**n); k = rng.randrange(0, 5 if n <= 2 else 9)
    return x, k, x ** k
def search(name, ops, seed=0):
    rng = random.Random(seed); lens = [1, 2] if name == 'gcd' else [1, 2]
    train = [data(name, rng, rng.choice(lens)) for _ in range(25)]
    leaves = ['s0', 's1', 'x', 'y', 'one']
    E = [(l, 1) for l in leaves]; bins = [o for o in ('add', 'sub', 'mul', 'mod') if o in ops]
    E += [((o, a, b), 3) for o in bins for a in leaves for b in leaves if a != b]
    if 'shift' in ops: E += [(('shift', a), 2) for a in leaves]
    exprs = [e for e, _ in sorted(E, key=lambda t: t[1])]
    conds = []
    if 'cmp' in ops:
        for a in leaves + ['zero']:
            for b in leaves + ['zero']:
                if a != b and (a in ('s0', 's1') or b in ('s0', 's1')): conds += [('cmp', a, b), ('not', ('cmp', a, b))]
    inits = [(a, b) for a in INITL for b in INITL]
    t0 = time.time(); tried = 0
    for ci, cond in enumerate(conds):
        print(f'  cond {ci+1}/{len(conds)} {show(cond)} tried so far {tried} {time.time()-t0:.0f}s', flush=True)
        for (i0, i1) in inits:
            for u0 in exprs:
                for u1 in exprs:
                    tried += 1; prog = (i0, i1, cond, u0, u1); ok = True; which = None
                    for xx, yy, r in train:
                        try:
                            st = run_prog(prog, n2d(xx), n2d(yy)); got = [d2n(s) for s in st]
                        except Exception: ok = False; break
                        w = [j for j in (0, 1) if got[j] == r]
                        if not w: ok = False; break
                        which = set(w) if which is None else which & set(w)
                        if not which: ok = False; break
                    if ok: return prog, min(which), tried, time.time() - t0
    return None, None, tried, time.time() - t0
def test(name, prog, res, lens=(2, 4, 6, 8), per=40):
    rng = random.Random(777); out = {}
    for n in lens:
        ok = 0
        for _ in range(per):
            a, b, r = data(name, rng, n)
            try: ok += d2n(run_prog(prog, n2d(a), n2d(b), 400)[res]) == r
            except Exception: pass
        out[n] = ok
    return out
if __name__ == '__main__':
    names = sys.argv[1].split(',')
    ablate = sys.argv[2].split(',') if len(sys.argv) > 2 else []
    MUL, MOD = relearn_level2()
    ops = {'add', 'sub', 'mul', 'mod', 'shift', 'cmp'} - set(ablate)
    for name in names:
        prog, res, tried, dt = search(name, ops)
        if not prog: print(f'{name} ops-removed={ablate} NOT FOUND tried {tried} {dt:.0f}s', flush=True); continue
        print(f'{name} ops-removed={ablate} FOUND inits=({show(prog[0])},{show(prog[1])}) while {show(prog[2])}: s0<-{show(prog[3])}; s1<-{show(prog[4])}; result=s{res}  tried {tried} {dt:.0f}s  unseen 2/4/6/8 digits (of 40): {test(name, prog, res)}', flush=True)
