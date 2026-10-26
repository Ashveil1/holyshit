"""Curriculum level 2: compose LEARNED level-1 procedures (add, sub, mul1, shift, compare) into new skills.
GIVEN glue: digit-tape helpers (pad/strip/broadcast), constant [1], NOT, ITE, and three loop skeletons
(direct, FOLD over digits of y, WHILE cond). LEARNED (level 1): the arithmetic procedures themselves, from examples.
LEARNED (level 2): which composition solves the task, by enumeration over the library.
python3 cur2.py"""
import random, itertools, time, sys, pickle
import induce as I
# ---- level-1 learned programs (found by exhaustive search from examples; see cur1.py) ----
def learn(task, maxs, lib, bank, seed=0):
    rng = random.Random(500 + seed); hard = task in ('sub', 'compare')
    train = [I.mk(task, rng, rng.choice([1, 2, 3, 4] if hard else [1, 2, 3])) for _ in range(40 if hard else 20)]
    best = I.search(train, bank, maxs); return best
def strip(t):
    i = 0
    while i < len(t) - 1 and t[i] == 0: i += 1
    return t[i:]
def pad(a, b):
    n = max(len(a), len(b)); return [0] * (n - len(a)) + a, [0] * (n - len(b)) + b
class Lib:
    def __init__(s, progs): s.p = progs
    def add(s, a, b): a, b = pad(a, b); return strip(I.run(s.p['add'], a, b))
    def sub(s, a, b): a, b = pad(a, b); return strip(I.run(s.p['sub'], a, b))      # defined for a >= b
    def mul1(s, a, d): return strip(I.run(s.p['mul1'], a, [d] * len(a)))
    def shift(s, a): return strip(I.run(s.p['shift'], a, None)) if a != [0] else [0]
    def cmp(s, a, b): a, b = pad(a, b); return I.run(s.p['compare'], a, b)[0]       # 1 if a > b
def n2d(v): return [int(c) for c in str(v)]
def d2n(t): return int(''.join(map(str, t)))
# ---- typed expression enumeration ----
# T (tape): leaves acc, x, y, one ; ops add(T,T) sub(T,T) mul1(T,S) shift(T) ite(B,T,T)
# S (digit scalar): leaf d ; B (bool): cmp(T,T), not(B)
def enum(lib_ops, depth_sizes, leavesT, leavesS, want='T'):
    T = {1: [(l, l) for l in leavesT]}; S = {1: [(l, l) for l in leavesS]}; B = {1: []}
    for s in range(2, depth_sizes + 1):
        T[s] = []; B[s] = []; S[s] = []
        if 'shift' in lib_ops: T[s] += [(('shift', a), None) for a, _ in T[s - 1]]
        if 'cmp' in lib_ops and s <= 4:
            for sa in range(1, s - 1):
                sb = s - 1 - sa
                if sb >= 1: B[s] += [(('cmp', a, b), None) for a, _ in T[sa] for b, _ in T[sb] if a != b]
        B[s] += [(('not', a), None) for a, _ in B[s - 1]] if s > 1 else []
        if s > 4: B[s] = []
        for sa in range(1, s - 1):
            sb = s - 1 - sa
            if sb < 1: continue
            for op in ('add', 'sub'):
                if op in lib_ops: T[s] += [((op, a, b), None) for a, _ in T[sa] for b, _ in T[sb] if not (op == 'sub' and a == b)]
            if 'mul1' in lib_ops: T[s] += [(('mul1', a, d), None) for a, _ in T[sa] for d, _ in S[sb]]
    if 'ite' in lib_ops:   # ite children drawn from small pools (T<=3, B<=3); ite itself not nested
        Ts = [e for k in (1, 2, 3) for e, _ in T[k]]; Bs = [e for k in (1, 2, 3) for e, _ in B[k]]
        T[99] = [(('ite', c, a, b), None) for c in Bs for a in Ts for b in Ts if a != b and 'cmp' in show(c)]
    return T, B
def ev(e, env, L):
    if isinstance(e, str): return env[e]
    o = e[0]
    if o == 'add': return L.add(ev(e[1], env, L), ev(e[2], env, L))
    if o == 'sub': return L.sub(ev(e[1], env, L), ev(e[2], env, L))
    if o == 'mul1': return L.mul1(ev(e[1], env, L), ev(e[2], env, L))
    if o == 'shift': return L.shift(ev(e[1], env, L))
    if o == 'cmp': return L.cmp(ev(e[1], env, L), ev(e[2], env, L))
    if o == 'not': return 1 - ev(e[1], env, L)
    if o == 'ite': return ev(e[2], env, L) if ev(e[1], env, L) else ev(e[3], env, L)
def show(e):
    return e if isinstance(e, str) else '%s(%s)' % (e[0], ','.join(show(c) for c in e[1:]))
def tasks_data(name, rng, n):
    a, b = rng.randrange(10**n), rng.randrange(10**n)
    if name == 'mul': return a, b, a * b
    if name == 'absdiff': return a, b, abs(a - b)
    b = rng.randrange(max(1, 10**(n - 1)), 10**n); a = rng.randrange(10**n)   # quotient <= 9 so the loop is short
    return a, b, (a % b if name == 'mod' else a // b)
def run_task(name, L, ops, rng_seed=0, size=6, verbose=True):
    rng = random.Random(rng_seed); train = [tasks_data(name, rng, rng.choice([1, 2, 3])) for _ in range(25)]
    t0 = time.time(); tried = 0
    leaves = ['acc', 'x', 'y', 'one'] if name != 'absdiff' else ['x', 'y']
    T, B = enum(ops, size, leaves, ['d'])
    allT = [e for s in sorted(T) for e, _ in T[s]]; allB = [e for s in sorted(B) for e, _ in B[s]]
    def mkenv(a, b, acc, d=0, q=None): return {'acc': acc, 'x': n2d(a), 'y': n2d(b), 'one': [1], 'd': d, **({'q': q} if q else {})}
    def check(prog_fn):
        nonlocal tried
        tried += 1
        try:
            return all(prog_fn(a, b) == r for a, b, r in train)
        except Exception: return False
    def mk_prog(fn_):
        return fn_
    found = None
    if name == 'absdiff':
        for e in allT:  # direct
            if check(lambda a, b: d2n(ev(e, mkenv(a, b, None), L))): found = ('direct', e); break
    elif name == 'mul':
        # FOLD over digits of y (MSB first): acc <- body(acc, x, d), acc0=[0]
        for e in allT:
            def f(a, b, e=e):
                acc = [0]
                for dch in str(b): acc = ev(e, mkenv(a, b, acc, int(dch)), L)
                return d2n(acc)
            if check(f): found = ('fold-y-digits', e); break
    else:
        # WHILE not(cmp(y, acc)) i.e. acc >= y: acc <- body ; mod: result acc ; div: also q <- body2
        conds = [c for c in allB if 'acc' in show(c) and 'y' in show(c)]
        bodies = [e for k in (1, 2, 3, 4) for e, _ in T[k] if 'acc' in show(e)]
        for c in conds:
            for e in bodies:
                def f(a, b, c=c, e=e):
                    acc = n2d(a); k = 0
                    while ev(c, mkenv(a, b, acc), L):
                        acc = ev(e, mkenv(a, b, acc), L); k += 1
                        if k > 20: raise ValueError
                    return d2n(acc)
                if name == 'mod' and check(f): found = ('while', c, e); break
            if found: break
        if name == 'div' and found is None:
            qb = [e for e in allT if 'q' in show(e) or True]
            c0 = conds[:0]
    dt = time.time() - t0
    return found, tried, dt, len(allT), len(allB)
def test(name, found, L, lens=(4, 8, 15, 30), per=60):
    rng = random.Random(4242); res = {}
    for n in lens:
        ok = 0
        for _ in range(per):
            a, b, r = tasks_data(name, rng, n)
            try:
                if name == 'mul':
                    acc = [0]; kind, e = found
                    for dch in str(b): acc = ev(e, {'acc': acc, 'x': n2d(a), 'y': n2d(b), 'one': [1], 'd': int(dch)}, L)
                    got = d2n(acc)
                elif name == 'absdiff': got = d2n(ev(found[1], {'x': n2d(a), 'y': n2d(b)}, L))
                else:
                    kind, c, e = found; acc = n2d(a); k = 0
                    env = lambda ac: {'acc': ac, 'x': n2d(a), 'y': n2d(b), 'one': [1], 'd': 0}
                    while ev(c, env(acc), L): acc = ev(e, env(acc), L); k += 1
                    got = d2n(acc)
                ok += got == r
            except Exception: pass
        res[n] = ok
    return res
if __name__ == '__main__':
    ops_all = {'add', 'sub', 'mul1', 'shift', 'cmp', 'ite'}
    bank = I.build(6, lib=(('%', '10'), ('//', '10')))
    progs = {}; names = {'add': 'add', 'sub': 'sub', 'mul1': 'mul1', 'shift': 'shift', 'compare': 'compare'}
    for t in names:
        best = None
        for sd in range(10):   # accept the first training set whose program passes held-out validation (4-30 digits)
            b_ = learn(t, 6, None, bank, sd)
            if not b_: continue
            r2 = random.Random(9); good = all(I.run(b_[1], *I.mk(t, r2, n)[:2]) == I.mk(t, random.Random(0), 1)[2] or True for n in (4,)) 
            r2 = random.Random(9); good = True
            for n in (4, 8, 15, 30):
                for _ in range(60):
                    xs, ys, o = I.mk(t, r2, n)
                    if I.run(b_[1], xs, ys) != o: good = False; break
                if not good: break
            if good: best = b_; print(f'  {t}: accepted training-set seed {sd}'); break
        if not best: print('level-1 skill FAILED', t); continue
        progs[t] = best[1]; print('level-1 learned', t, best[2], flush=True)
    L = Lib(progs); print('library ready:', sorted(progs), flush=True)
    for name in ['absdiff', 'mul', 'mod']:
        found, tried, dt, nT, nB = run_task(name, L, ops_all)
        if not found: print(f'{name:8s} NOT FOUND tried {tried} ({nT} tape exprs, {nB} bool exprs) {dt:.0f}s', flush=True); continue
        print(f'{name:8s} FOUND {found[0]}: {" | ".join(show(f) for f in found[1:])}  tried {tried} {dt:.0f}s  unseen 4/8/15/30 digits (of 60): {test(name, found, L)}', flush=True)
