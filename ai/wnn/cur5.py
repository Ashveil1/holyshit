"""S1+S2: finish the basic-arithmetic library, then solve unseen tasks from (input, output) examples with NO hint.
S1 (learned from examples): max, min (ite over learned cmp), is-prime (fold skeleton over d=2..x-1).
    div, gcd, mul, mod come from cur4/cur3 (learned loops). iszero(e)=not cmp(0,e) is GIVEN glue.
S2: for each unseen task only (x,y)->out pairs are shown. Search = breadth-first over expressions (depth<=2) of ALL
    library ops; first expression consistent with the 25 training pairs wins. Measure held-out accuracy at 1/2/3 digits.
python3 cur5.py [removed_lib_ops]"""
import sys, json, random, math, time, itertools
import cur3 as K
from cur3 import *
sys.setrecursionlimit(10000); sys.set_int_max_str_digits(0)
def tup(e): return tuple(tup(x) for x in e) if isinstance(e, list) else e
def tape_bool(v): return 1 if v else 0
class Lib:
    def __init__(s):
        K.MUL, K.MOD = relearn_level2()
        c = json.load(open('/tmp/progs4.json'))
        s.prog = {k: (tup(v[0]), v[1]) for k, v in c.items()}
        s.cache = {}
    def call(s, op, *a):
        k = (op,) + a
        if k in s.cache:
            r = s.cache[k]
            if isinstance(r, Exception): raise r
            return r
        try: r = s._call(op, *a)
        except Exception as e: s.cache[k] = ValueError(str(e)); raise ValueError(str(e))
        s.cache[k] = r; return r
    def _call(s, op, *a):
        if LB.cap and any(v > LB.cap for v in a): raise ValueError('cap')
        if op == 'iszero': return 1 if a[0] == 0 else 0
        x, y = a
        X, Y = n2d(x), n2d(y)
        if op == 'add': return d2n(K.L.add(X, Y))
        if op == 'sub':
            if x < y: raise ValueError('neg')
            return d2n(K.L.sub(X, Y))
        if op == 'mul': return d2n(K.MUL(X, Y))
        if op in ('mod', 'div', 'gcd'):
            if y == 0: raise ValueError('zero')
            if op == 'mod': return d2n(K.MOD(X, Y))
            p, r = s.prog[op]
            return d2n(run_prog(p, X, Y, 400)[r])
        if op in ('max', 'min'):
            c, a, b = s.mm[op]; v = {'x': x, 'y': y}
            return v[a] if K.L.cmp(n2d(v[c[0]]), n2d(v[c[1]])) else v[b]
        raise KeyError(op)
LB = None
def learn_maxmin():
    out = {}
    rng = random.Random(1); tr = [(rng.randrange(0, 100), rng.randrange(0, 100)) for _ in range(25)]
    for name, f in (('max', max), ('min', min)):
        for c in itertools.product('xy', repeat=2):
            for a, b in itertools.product('xy', repeat=2):
                if c[0] == c[1]: continue
                def g(x, y, c=c, a=a, b=b):
                    v = {'x': n2d(x), 'y': n2d(y)}
                    return d2n(v[a]) if K.L.cmp(v[c[0]], v[c[1]]) else d2n(v[b])
                if all(g(x, y) == f(x, y) for x, y in tr):
                    out[name] = (c, a, b); break
            if name in out: break
    return out
def learn_isprime(ops_ok=('add', 'mul', 'mod', 'sub')):
    rng = random.Random(2)
    isp = lambda n: n > 1 and all(n % d for d in range(2, int(n ** .5) + 1))
    pr = [n for n in range(2, 80) if isp(n)]; co = [n for n in range(4, 80) if not isp(n)]
    xs = rng.sample(pr, 12) + rng.sample(co, 13)
    leaves = ['acc', 'd', 'x', 'one', 'zero']
    E1 = [(o, a, b) for o in ops_ok for a in leaves for b in leaves if a != b]
    E2 = [(o, a, b) for o in ops_ok for a in leaves for b in E1] + [(o, b, a) for o in ops_ok for a in leaves for b in E1]
    cand = leaves + E1 + E2
    def ev(e, env):
        if isinstance(e, str): return env[e]
        return LB.call(e[0], ev(e[1], env), ev(e[2], env))
    tried = 0
    for init in ('one', 'zero'):
        for f in cand:
            for gname in ('acc', 'iszero', 'nz'):
                tried += 1; ok = True
                for x in xs:
                    try:
                        acc = 1 if init == 'one' else 0
                        for d in range(2, x): acc = ev(f, {'acc': acc, 'd': d, 'x': x, 'one': 1, 'zero': 0})
                        r = acc if gname == 'acc' else (LB.call('iszero', acc) if gname == 'iszero' else 1 - LB.call('iszero', acc))
                    except ValueError: ok = False; break
                    if r != int(isp(x)): ok = False; break
                if ok: return (init, f, gname), tried, isp
    return None, tried, isp
def run_isprime(prog, x):
    init, f, gname = prog
    def ev(e, env):
        if isinstance(e, str): return env[e]
        return LB.call(e[0], ev(e[1], env), ev(e[2], env))
    acc = 1 if init == 'one' else 0
    for d in range(2, x): acc = ev(f, {'acc': acc, 'd': d, 'x': x, 'one': 1, 'zero': 0})
    return acc if gname == 'acc' else (LB.call('iszero', acc) if gname == 'iszero' else 1 - LB.call('iszero', acc))
if __name__ == '__main__':
    removed = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] else []
    LB = Lib(); LB.cap = 10 ** 200
    mm = learn_maxmin(); LB.mm = mm; print('S1 max/min learned (cond,then,else):', mm, flush=True)
    t0 = time.time(); ip, tried, isp = learn_isprime(); print('S1 is-prime learned:', ip, 'tried', tried, f'{time.time()-t0:.0f}s', flush=True)
    LB.cap = None; LB.cache.clear()
    if ip:
        te = random.Random(9); xs = [te.randrange(2, 2000) for _ in range(200)]
        print('  is-prime unseen x<2000:', sum(run_isprime(ip, x) == int(isp(x)) for x in xs), '/200', flush=True)
        # library entry: isprime
        orig = LB._call
        def _call2(op, *a, orig=orig):
            if op == 'isprime':
                if a[0] > 2100: raise ValueError('big')
                return run_isprime(ip, a[0])
            return orig(op, *a)
        LB._call = _call2
    BIN = [o for o in ('add', 'sub', 'mul', 'mod', 'div', 'gcd', 'max', 'min') if o not in removed]
    UN = [o for o in ('iszero', 'isprime') if o not in removed and (o != 'isprime' or ip)]
    rng = random.Random(5)
    def pairs(n, digs):
        out = []
        for _ in range(n):
            nd = rng.choice(digs); y = rng.randrange(1, 10 ** nd); x = rng.randrange(1, 10 ** nd)
            if rng.random() < .4: x = y * rng.randrange(1, 10)
            out.append((x, y))
        return out
    isp_ = lambda n: int(n > 1 and all(n % d for d in range(2, int(n ** .5) + 1)))
    TASKS = {
     'lcm': lambda x, y: x * y // math.gcd(x, y),
     'divisible(x by y)': lambda x, y: int(x % y == 0),
     'larger minus smaller': lambda x, y: abs(x - y),
     'larger mod smaller': lambda x, y: max(x, y) % min(x, y),
     'x*x mod y': lambda x, y: x * x % y,
     'x^2+y^2': lambda x, y: x * x + y * y,
     'is x+y prime': lambda x, y: isp_(x + y),
     'x and y both prime': lambda x, y: isp_(x) * isp_(y),
     'coprime (gcd==1)': lambda x, y: int(math.gcd(x, y) == 1),
     'gcd plus larger': lambda x, y: math.gcd(x, y) + max(x, y),
    }
    train_in = pairs(25, [1, 2]); test_in = {n: pairs(40, [n]) for n in (1, 2, 3)}
    # level sets (as expression trees) with value vectors over training inputs
    def vec(e, ins):
        if e == 'x': return [x for x, y in ins]
        if e == 'y': return [y for x, y in ins]
        if e == 'one': return [1] * len(ins)
        return None
    def ev(e, x, y):
        if e == 'x': return x
        if e == 'y': return y
        if e == 'one': return 1
        if len(e) == 2: return LB.call(e[0], ev(e[1], x, y))
        return LB.call(e[0], ev(e[1], x, y), ev(e[2], x, y))
    def safe(e, x, y):
        try: return ev(e, x, y)
        except ValueError: return None
    L0 = ['x', 'y', 'one']
    def grow(E):
        new = [(o, a, b) for o in BIN for a in E for b in E if a != b or o in ('mul', 'add')]
        new += [(o, a) for o in UN for a in E]
        return new
    t0 = time.time(); L1 = L0 + grow(L0)
    print('lib ops', BIN + UN, 'level1 size', len(L1), flush=True)
    V1 = {e: tuple(safe(e, x, y) for x, y in train_in) for e in L1}
    L2 = []  # candidates generated on demand with vectors
    def vec_of(e):
        if e in V1: return V1[e]
        return tuple(safe(e, x, y) for x, y in train_in)
    total = 0; solved = 0
    for name, f in TASKS.items():
        target = tuple(f(x, y) for x, y in train_in); found = None; tried = 0
        for e in L1:
            tried += 1
            if V1[e] == target: found = e; break
        if not found:
            for e in grow(L1):
                tried += 1
                # cheap prefilter on first input
                x0, y0 = train_in[0]
                if safe(e, x0, y0) != target[0]: continue
                if vec_of(e) == target: found = e; break
        if not found and name == 'is x+y prime':
            e0 = ('isprime', ('add', 'x', 'y')); print('DBG', [(x, y, safe(e0, x, y), t) for (x, y), t in zip(train_in, target) if safe(e0, x, y) != t][:5], flush=True)
        if not found: print(f'{name}: NOT FOUND (depth<=2) tried {tried}', flush=True); total += 1; continue
        acc = {}
        for n, ins in test_in.items():
            acc[n] = sum(safe(found, x, y) == f(x, y) for x, y in ins)
        def sh(e): return e if isinstance(e, str) else '(' + ' '.join(sh(t) for t in e) + ')'
        ok = all(v >= 38 for v in acc.values()); solved += ok; total += 1
        print(f'{name}: found {sh(found)} tried {tried}  held-out/40 by digits {acc}  {"OK" if ok else "poor"}', flush=True)
    print(f'S2 removed={removed}: generalising solutions {solved}/{total}  {time.time()-t0:.0f}s', flush=True)
