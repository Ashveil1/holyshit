"""P9: evolutionary search for step-programs with K registers (genetic programming).
GIVEN: scan machine (walk the tape), integer registers r0..r(K-1) init 0, arithmetic DSL,
       output mode inferred from the shape of the examples (tape / tape+r0 / final r0-expression).
LEARNED: read/write direction, per-register update trees g_i, output tree f, and how many
       registers are actually used. No traces; fitness = partial credit on end-to-end examples.
Guidance: operator/leaf sampling prior can be set from solved programs (--prior), and mutation can wrap a subtree in a mined library op (%10, //10).
Run: python3 gp.py TASK[,TASK..] [--seeds 10] [--evals 60000] [--K 3] [--random]"""
import random, sys, time, math, json
OPS2 = ['+', '-', '*', '//', '%', '<', '>', '==', 'min', 'max']
CONSTS = [0, 1, 2, 3, 10]
def fd(a, b): return a // b if b else 0
def fm(a, b): return a % b if b else 0
def clip(v): return -10**6 if v < -10**6 else 10**6 if v > 10**6 else v
def src(e):
    if isinstance(e, (str, int)): return str(e)
    o = e[0]
    if o == 'ite': return f'({src(e[2])} if {src(e[1])} else {src(e[3])})'
    if o in ('min', 'max'): return f'{o}({src(e[1])},{src(e[2])})'
    if o == '//': return f'fd({src(e[1])},{src(e[2])})'
    if o == '%': return f'fm({src(e[1])},{src(e[2])})'
    if o in ('<', '>', '=='): return f'(1 if {src(e[1])}{o}{src(e[2])} else 0)'
    return f'({src(e[1])}{o}{src(e[2])})'
def size(e): return 1 if not isinstance(e, tuple) else 1 + sum(size(c) for c in e[1:])
class Ctx:
    def __init__(s, K, leaves, ops_prior=None, lib=True):
        s.K = K; s.leaves = leaves; s.lib = lib
        s.ops = ops_prior or {o: 1.0 for o in OPS2 + ['ite']}
        s.regs = [f'r{i}' for i in range(K)]
    def leaf(s, rng):
        return rng.choice(s.leaves) if rng.random() < .7 else rng.choice(CONSTS)
    def tree(s, rng, d):
        if d == 0 or rng.random() < .3: return s.leaf(rng)
        o = rng.choices(list(s.ops), list(s.ops.values()))[0]
        if o == 'ite': return ('ite', s.tree(rng, d - 1), s.tree(rng, d - 1), s.tree(rng, d - 1))
        return (o, s.tree(rng, d - 1), s.tree(rng, d - 1))
def paths(e, p=()):
    yield p
    if isinstance(e, tuple):
        for i, c in enumerate(e[1:], 1): yield from paths(c, p + (i,))
def get(e, p):
    for i in p: e = e[i]
    return e
def put(e, p, n):
    if not p: return n
    l = list(e); l[p[0]] = put(e[p[0]], p[1:], n); return tuple(l)
def mutate_tree(e, ctx, rng):
    ps = list(paths(e)); p = rng.choice(ps); sub = get(e, p); r = rng.random()
    if r < .35: return put(e, p, ctx.tree(rng, 2))
    if r < .55 and isinstance(sub, tuple) and sub[0] in OPS2: return put(e, p, (rng.choice(OPS2),) + sub[1:])
    if r < .7 and not isinstance(sub, tuple): return put(e, p, ctx.leaf(rng))
    if r < .85 and ctx.lib: return put(e, p, (rng.choice(['%', '//']), sub, 10))   # mined library wrap
    if isinstance(sub, tuple): return put(e, p, rng.choice(sub[1:]))             # unwrap
    return put(e, p, ctx.leaf(rng))
class G:  # genome
    __slots__ = ('rd', 'wr', 'g', 'f', 'fit', 'fn')
    def __init__(s, rd, wr, g, f): s.rd, s.wr, s.g, s.f = rd, wr, tuple(g), f; s.fit = None; s.fn = None
    def key(s): return (s.rd, s.wr, s.g, s.f)
    def nodes(s): return size(s.f) + sum(size(x) for x in s.g)
_FN = {}
def compile_g(gn, K):
    k = (tuple(src(x) for x in gn.g), src(gn.f), K)
    if len(_FN) > 20000: _FN.clear()
    if k not in _FN:
        a = ','.join(['x', 'y'] + [f'r{i}' for i in range(K)])
        _FN[k] = eval(f'lambda {a}: ({src(gn.f)},' + ','.join(src(x) for x in gn.g) + ',)', {'fd': fd, 'fm': fm, 'min': min, 'max': max})
    return _FN[k]
def run(gn, K, xs, ys, mode, fn=None):
    fn = fn or compile_g(gn, K); n = len(xs); order = range(n) if gn.rd == 'fwd' else range(n - 1, -1, -1)
    r = [0] * K; out = []
    for i in order:
        res = fn(xs[i], ys[i] if ys else 0, *r)
        if mode != 'final': out.append(res[0])
        r = [clip(v) for v in res[1:]]
    if mode == 'final': return [fn(0, 0, *r)[0]]
    if mode == 'tape+r': out.append(r[0])
    return out if gn.wr == 'fwd' else out[::-1]
def fitness(gn, K, data, mode):
    fn = compile_g(gn, K); tot = 0.0
    try:
        for xs, ys, o in data:
            p = run(gn, K, xs, ys, mode, fn)
            if len(p) != len(o): continue
            if mode == 'final':
                tot += 1.0 if p[0] == o[0] else 0.3 / (1 + abs(p[0] - o[0]))
            else: tot += sum(a == b for a, b in zip(p, o)) / len(o)
    except Exception: return 0.0
    return tot / len(data)
def detect_mode(data):
    if all(len(o) == 1 for _, _, o in data): return 'final'
    if all(len(o) == len(xs) for xs, _, o in data): return 'tape'
    if all(len(o) == len(xs) + 1 for xs, _, o in data): return 'tape+r'
    raise ValueError('unsupported output shape')
def evolve(data, K, evals, seed, rand_only=False, pop=300, lib=True, prior=None):
    rng = random.Random(seed); two = data[0][1] is not None
    leaves = ['x'] + (['y'] if two else []) + [f'r{i}' for i in range(K)]
    ctx = Ctx(K, leaves, prior, lib); mode = detect_mode(data)
    def rand_g():
        g = [(f'r{i}' if rng.random() < .5 else ctx.tree(rng, 3)) for i in range(K)]
        return G(rng.choice(['fwd', 'bwd']), rng.choice(['fwd', 'bwd']), g, ctx.tree(rng, 3))
    def ev(gn):
        if gn.fit is None: gn.fit = fitness(gn, K, data, mode) - 0.002 * gn.nodes()
        return gn.fit
    P = [rand_g() for _ in range(pop)]; n = 0; best = None
    while n < evals:
        for gn in P:
            if gn.fit is None: n += 1
            ev(gn)
        P.sort(key=lambda g: -g.fit)
        if best is None or P[0].fit > best.fit: best = P[0]
        if P[0].fit > 0.999 - 0.002 * P[0].nodes() and fitness(P[0], K, data, mode) >= 0.9999: return P[0], n, mode
        if rand_only: P = [rand_g() for _ in range(pop)]; continue
        nxt = P[:10]
        while len(nxt) < pop:
            a = min(rng.sample(P, 4), key=lambda g: -g.fit)
            c = G(a.rd, a.wr, a.g, a.f); r = rng.random()
            if r < .15:
                b = min(rng.sample(P, 4), key=lambda g: -g.fit); i = rng.randrange(K + 1)
                src_t = b.f if i == K else b.g[i]; sub = get(src_t, rng.choice(list(paths(src_t))))
                tgt = c.f if i == K else c.g[i]; new = put(tgt, rng.choice(list(paths(tgt))), sub)
                if i == K: c.f = new
                else: c.g = c.g[:i] + (new,) + c.g[i + 1:]
            elif r < .2: c.rd = 'bwd' if c.rd == 'fwd' else 'fwd'
            elif r < .25: c.wr = 'bwd' if c.wr == 'fwd' else 'fwd'
            else:
                i = rng.randrange(K + 1)
                if i == K: c.f = mutate_tree(c.f, ctx, rng)
                else: c.g = c.g[:i] + (mutate_tree(c.g[i], ctx, rng),) + c.g[i + 1:]
            if size(c.f) + sum(size(x) for x in c.g) > 60: continue
            nxt.append(c)
        P = nxt
    return None, n, mode
# ---------------- tasks ----------------
import induce as I
def mk(task, rng, n):
    if task in ('second_max', 'alt_sum', 'count_max', 'max_minus_min', 'count_gt_first', 'run_parity', 'second_min_pos'):
        xs = [rng.randrange(10) for _ in range(n)]
        o = {'second_max': lambda: [sorted(xs)[-2]], 'alt_sum': lambda: [sum(v if i % 2 == 0 else -v for i, v in enumerate(xs))],
             'count_max': lambda: [xs.count(max(xs))], 'max_minus_min': lambda: [max(xs) - min(xs)],
             'count_gt_first': lambda: [sum(v > xs[0] for v in xs)],
             'run_parity': lambda: [sum(xs[:i + 1]) % 2 for i in range(n)]}[task]()
        return xs, None, o
    return I.mk(task, rng, n)
def lens(task): return [2, 3, 4, 5, 6] if task in ('second_max', 'alt_sum', 'count_max', 'max_minus_min', 'count_gt_first') else [1, 2, 3, 4]
def make_train(task, n_tr, seed):
    rng = random.Random(1000 + seed); return [mk(task, rng, rng.choice(lens(task))) for _ in range(n_tr)]
def test(task, gn, K, mode):
    rng = random.Random(99); out = {}
    for n in (4, 6, 10, 20, 50):
        ok = 0
        for _ in range(100):
            xs, ys, o = mk(task, rng, n)
            try: ok += run(gn, K, xs, ys, mode) == o
            except Exception: pass
        out[n] = ok
    return out
if __name__ == '__main__':
    a = sys.argv[1:]; tasks = a[0].split(','); opt = lambda k, d: (a[a.index(k) + 1] if k in a else d)
    seeds = int(opt('--seeds', 10)); evals = int(opt('--evals', 60000)); K = int(opt('--K', 3)); rnd = '--random' in a
    for task in tasks:
        res = []; t0 = time.time()
        for s in range(seeds):
            data = make_train(task, 60, s)
            gn, n, mode = evolve(data, K, evals, s, rnd)
            if gn is None: res.append(None); continue
            t = test(task, gn, K, mode); res.append((n, t, ([src(x) for x in gn.g], src(gn.f), gn.rd, gn.wr)))
        ok = [r for r in res if r and min(r[1].values()) >= 99]
        solved = [r for r in res if r]
        print(f'{task:15s} K={K} {"random" if rnd else "GP"} train-solved {len(solved)}/{seeds}  generalizes(>=99% at all lens incl 50) {len(ok)}/{seeds}  mean evals(solved) {sum(r[0] for r in solved)/max(1,len(solved)):.0f}  {time.time()-t0:.0f}s', flush=True)
        for r in solved[:2]: print('    ', r[2], r[1], flush=True)
