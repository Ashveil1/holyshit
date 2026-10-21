"""P24 / cur7: library learning on top of P14. After the curriculum is learned, mine reusable fragments (step-pair patterns shared by >=2 learned skills) and use them to ORDER the search for new tasks (macro candidates first). Metric: programs tried and success vs the P14 ordering, same cap.
P14 / cur6: learn the loop skeletons themselves.
Instead of hand-given direct/fold/while skeletons, ONE generic linear-recursion schema is searched:
    f(a,b) = base(a,b)                      if cond(a,b)
           = comb(a,b, f(step0(a,b), step1(a,b)))   otherwise      (comb = identity => tail loop)
    answer = post(f(x, init))   with init in {y, 1, 0, 2}, post in {id, iszero, nonzero}
A while loop, a fold, a counting loop, a bounded range loop are all instances; the search picks cond, base, both
step expressions, comb and post from examples alone. Library grows: each learned function becomes an op.
GIVEN: the schema, int-level primitives add, sub (no negatives), lt (these were learned as digit-tape machines
in P7-P11; here they run on Python ints for speed), expression grammar (leaves a,b,1,0 + one binary op),
cond forms (lt / not-lt / iszero / nonzero), post set, curriculum order, task I/O format (x,y)->out.
python3 cur6.py SEED [ablation]  ablation in: notail (no comb), nopair (one step arg only), nolib (no learned ops), nocombe"""
import sys, random, math, time, itertools, functools
sys.setrecursionlimit(100000)
CAP = [400]
CAPF = [400]
PROG = False
VALID = []
class Fail(Exception): pass
def p_add(a, b): return a + b
def p_sub(a, b):
    if a < b: raise Fail('neg')
    return a - b
LIB = {'add': p_add, 'sub': p_sub}
LEAVES = ['a', 'b', 'one', 'zero']
@functools.lru_cache(maxsize=300000)
def ev(e, a, b):
    if e == 'a': return a
    if e == 'b': return b
    if e == 'one': return 1
    if e == 'zero': return 0
    return LIB[e[0]](ev(e[1], a, b), ev(e[2], a, b))
def cev(c, a, b):
    k = c[0]
    if k == 'lt': return ev(c[1], a, b) < ev(c[2], a, b)
    if k == 'nlt': return not ev(c[1], a, b) < ev(c[2], a, b)
    if k == 'z': return ev(c[1], a, b) == 0
    return ev(c[1], a, b) != 0
def run(spec, x, init, cap=None):
    cond, base, s0, s1, comb = spec; cap = cap or CAP[0]
    a, b = x, init; stack = []
    while not cev(cond, a, b):
        if comb is not None: stack.append((a, b))
        a, b = ev(s0, a, b), ev(s1, a, b)
        if len(stack) > cap or (comb is None and len(stack) == 0 and False): raise Fail('deep')
        cap -= 1
        if cap < -10 ** 9: raise Fail
        if comb is None and cap <= 0: raise Fail('deep')
    v = ev(base, a, b)
    if comb is not None:
        op, e, order = comb
        for (a, b) in reversed(stack):
            ee = ev(e, a, b); v = LIB[op](ee, v) if order == 0 else LIB[op](v, ee)
    return v
POST = {'id': lambda v: v, 'iszero': lambda v: 1 if v == 0 else 0, 'nz': lambda v: 0 if v == 0 else 1}
def inits_for(init, y): return {'y': y, 'one': 1, 'zero': 0, 'two': 2}[init]
def conds_list():
    cs = []
    for p in LEAVES:
        for q in LEAVES:
            if p != q and ('a' in (p, q) or 'b' in (p, q)): cs += [('lt', p, q), ('nlt', p, q)]
    for p in ('a', 'b'): cs += [('z', p), ('nzc', p)]
    return cs
MACROS = []
def mine_macros(progs):
    """progs: {task: (init,(cond,base,s0,s1,comb),post)}. Macro = step pair (s0,s1) shared by >=2 tasks."""
    from collections import Counter
    c = Counter()
    for t, (init, spec, post) in progs.items():
        cond, base, s0, s1, comb = spec; c[(str(s0), str(s1))] += 1
    MACROS[:] = [eval(k0) for (k0, k1), n in []] or []
    out = []
    for (k, n) in c.items():
        if n >= 2: out.append(eval(k))
    MACROS[:] = out
    return out
def search(train, abl, tag=''):
    ops = [o for o in LIB if not (abl == 'nolib' and o not in ('add', 'sub'))]
    E1 = list(LEAVES) + [(o, p, q) for o in ops for p in LEAVES for q in LEAVES if p != q or o in ('add',)]
    conds = conds_list(); bases = list(LEAVES)
    combs = [None] if abl == 'notail' else None
    comb_list = [None]
    if abl != 'notail':
        comb_list += [(o, e, 0) for o in ops for e in E1] + [(o, e, 1) for o in ops if o not in ('add',) for e in E1]
    steps_pair = [(s0, s1) for s0 in E1 for s1 in E1]
    E1p = [e for e in E1 if isinstance(e, str) or e[0] in ('add', 'sub')]
    steps_single = [(s, 'b') for s in E1p] + [('a', s) for s in E1p]
    if abl == 'macro' and MACROS:
        def pri(st):
            for i, (m0, m1) in enumerate(MACROS):
                if st[0] == m0 and st[1] == m1: return i
            return len(MACROS)
        steps_pair = sorted(steps_pair, key=pri); steps_single = sorted(steps_single, key=pri)
    t0 = time.time(); tried = 0
    x0, y0, r0 = train[0]
    comb_list.sort(key=lambda c: 0 if c is None else (1 if isinstance(c[1], str) else 2))
    for ci, comb in enumerate(comb_list):
        if ci % 20 == 0 and PROG: print(f'   comb {ci}/{len(comb_list)} {comb} tried {tried} {time.time()-t0:.0f}s', flush=True)
        for init in ('y', 'one', 'zero', 'two'):
            st = steps_pair if (comb is None and abl != 'nopair') else steps_single
            if comb is not None and abl == 'nocombe': continue
            if tried > 6_000_000: return None, tried, time.time() - t0
            for cond in conds:
                for base in bases:
                    for (s0, s1) in st:
                        tried += 1; spec = (cond, base, s0, s1, comb)
                        try: v0 = run(spec, x0, inits_for(init, y0))
                        except Fail: continue
                        except (KeyError, ZeroDivisionError, RecursionError, OverflowError): continue
                        pm = [pn for pn, pf in POST.items() if pf(v0) == r0]
                        if not pm: continue
                        for pn in pm:
                            ok = True
                            for x, y, r in train[1:]:
                                try:
                                    if POST[pn](run(spec, x, inits_for(init, y))) != r: ok = False; break
                                except (Fail, KeyError, RecursionError, OverflowError): ok = False; break
                            if ok and VALID:
                                for x, y, r in VALID:
                                    try:
                                        if POST[pn](run(spec, x, inits_for(init, y))) != r: ok = False; break
                                    except (Fail, KeyError, RecursionError, OverflowError, ZeroDivisionError): ok = False; break
                            if ok: return (init, spec, pn), tried, time.time() - t0
        ev.cache_clear() if len(ev.cache_info()) and ev.cache_info().currsize > 3_000_000 else None
    return None, tried, time.time() - t0
def show_e(e): return e if isinstance(e, str) else '(' + ' '.join(show_e(t) for t in e) + ')'
def show_prog(p):
    init, (cond, base, s0, s1, comb), pn = p
    return f"init b={init}; if {show_e(cond)} -> {base}; else step ({show_e(s0)},{show_e(s1)}); comb={comb if comb is None else (comb[0], show_e(comb[1]), comb[2])}; post={pn}"
def make_fn(p):
    init, spec, pn = p
    def f(x, y): return POST[pn](run(spec, x, inits_for(init, y), cap=CAPF[0]))
    return f
isp = lambda n: int(n > 1 and all(n % d for d in range(2, int(n ** .5) + 1)))
def gen(task, rng, scale):
    s = 10 ** scale
    if task == 'mod': y = rng.randrange(1, max(2, s)); x = rng.randrange(0, s * 3 if scale <= 2 else s); return x, y, x % y
    if task == 'mul': x = rng.randrange(0, s); y = rng.randrange(0, 30 if scale <= 2 else s); return x, y, x * y
    if task == 'div': y = rng.randrange(1, max(2, s)); x = rng.randrange(0, s * 3 if scale <= 2 else s * 3); return x, y, x // y
    if task == 'power': x = rng.randrange(0, 8 if scale <= 2 else 12); y = rng.randrange(0, 4 if scale <= 2 else 5); return x, y, x ** y
    if task == 'gcd':
        g = rng.randrange(1, 10 ** max(1, scale // 2)); a = g * rng.randrange(1, s); b = g * rng.randrange(1, s); return a, b, math.gcd(a, b)
    if task == 'isprime': x = rng.randrange(2, 60 if scale <= 2 else 10 ** min(scale, 3)); return x, rng.randrange(1, 50), isp(x)
    if task == 'fact': x = rng.randrange(0, 7 if scale <= 2 else 11); return x, rng.randrange(1, 50), math.factorial(x)
    if task == 'sumto': x = rng.randrange(0, 30 if scale <= 2 else s); return x, rng.randrange(1, 50), x * (x + 1) // 2
    if task == 'absdiff': x = rng.randrange(0, s); y = rng.randrange(0, s); return x, y, abs(x - y)
    if task == 'max': x = rng.randrange(0, s); y = rng.randrange(0, s); return x, y, max(x, y)
    if task == 'min': x = rng.randrange(0, s); y = rng.randrange(0, s); return x, y, min(x, y)
    if task == 'square': x = rng.randrange(0, 12 if scale <= 2 else 30); return x, rng.randrange(1, 50), x * x
    if task == 'cube': x = rng.randrange(0, 8 if scale <= 2 else 15); return x, rng.randrange(1, 50), x ** 3
    if task == 'even': x = rng.randrange(0, s * 3); return x, rng.randrange(1, 50), int(x % 2 == 0)
    if task == 'choose2': x = rng.randrange(0, 20 if scale <= 2 else 60); return x, rng.randrange(1, 50), x * (x - 1) // 2
    if task == 'sumsq': x = rng.randrange(0, 12 if scale <= 2 else 40); return x, rng.randrange(1, 50), x * (x + 1) * (2 * x + 1) // 6
    if task == 'dblfact':
        x = rng.randrange(0, 10 if scale <= 2 else 16); v = 1
        for i in range(x, 0, -2): v *= i
        return x, rng.randrange(1, 50), v
    if task == 'lcm': x = rng.randrange(1, 30); y = rng.randrange(1, 30); return x, y, x * y // math.gcd(x, y)
CURR = ['mod', 'mul', 'div', 'power', 'gcd', 'isprime', 'fact', 'sumto']
if __name__ == '__main__':
    PROG = True
    seed = int(sys.argv[1]); abl = sys.argv[2] if len(sys.argv) > 2 else ''
    NEW = ['absdiff', 'max', 'min', 'square', 'cube', 'even', 'choose2', 'sumsq', 'dblfact', 'lcm']
    only = sys.argv[3].split(',') if len(sys.argv) > 3 else CURR
    CURR = CURR + NEW
    import json, os
    FOUNDPROG = {}
    sv = f'/tmp/c7_prog_{seed}_{abl}.json'; saved = json.load(open(sv)) if os.path.exists(sv) else {}
    def tup(e): return tuple(tup(t) for t in e) if isinstance(e, list) else e
    rng = random.Random(seed); found = 0
    for task in [t for t in ['mod','mul','div','power','gcd','max','min','absdiff','isprime','fact','sumto','square','cube','even','choose2'] if t in only]:
        if task not in only: continue
        train = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
        if task in saved: p = tup(saved[task]); tried = dt = 0
        else:
            VALID[:] = []
            if 'val' in abl:
                vr = random.Random(5000 + seed); VALID[:] = [gen(task, vr, sc) for sc in (1, 2) for _ in range(16)]
            p, tried, dt = search(train, abl)
        if p and task not in saved: saved[task] = p; json.dump(saved, open(sv, 'w'))
        if p: FOUNDPROG[task] = p
        if task == 'sumto' and abl == 'macro':
            print('mined macros:', mine_macros(FOUNDPROG), flush=True)
        if not p: print(f'seed{seed} {abl} {task}: NOT FOUND tried {tried} {dt:.0f}s', flush=True); continue
        f = make_fn(p); te = random.Random(1000 + seed); res = {}; CAPF[0] = 20000
        for sc in (1, 2, 3, 4):
            ok = 0
            for _ in range(40):
                x, y, r = gen(task, te, sc)
                try: ok += int(f(x, y) == r)
                except (Fail, KeyError, RecursionError, OverflowError): pass
            res[sc] = ok
        print(f'seed{seed} {abl} {task}: FOUND {show_prog(p)} tried {tried} {dt:.0f}s unseen/40 by scale {res}', flush=True)
        CAPF[0] = 400; ev.cache_clear()
        if task in ('mod', 'mul', 'div', 'power', 'gcd', 'max', 'min') and res[2] >= 36: LIB[task] = (lambda ff: (lambda a, b: ff(a, b)))(f)
