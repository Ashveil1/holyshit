"""P7: induce step-programs from END-TO-END examples only (no traces, no hand-given
READ/FACT/WRITE/ADV/HALT policy, no carry abstraction, no derivation rules).

GIVEN (the minimal prior, stated honestly):
  * a scan machine: walk the input tape(s) one cell at a time, one integer register r (init 0)
  * each step: output o=f(x,y,r), update r=g(x,y,r)
  * output mode in {tape, tape+final r, final h(r)}, read dir and write dir in {fwd,bwd}
  * an arithmetic DSL: + - * // % < > == min max ite, leaves x y r and consts 0 1 2 3 10
LEARNED: which dirs/mode, and the programs f,g, by enumerative search (shortest first)
  from a few I/O pairs of 1-3 cells; tested on unseen, much longer inputs.
Run: python3 induce.py
"""
import numpy as np, itertools, random, time, sys
XR, YR, RLO, RHI = 10, 10, -10, 30
NR = RHI - RLO + 1
gx, gy, gr = np.meshgrid(np.arange(XR), np.arange(YR), np.arange(RLO, RHI + 1), indexing='ij')
def idx(x, y, r): return (x * YR + y) * NR + (r - RLO)
LEAVES = {'x': gx.ravel(), 'y': gy.ravel(), 'r': gr.ravel()}
for c in (0, 1, 2, 3, 10): LEAVES[str(c)] = np.full(gx.size, c)
BIN = {'+': np.add, '-': np.subtract, '*': np.multiply, '//': None, '%': None,
       '<': lambda a, b: (a < b) * 1, '>': lambda a, b: (a > b) * 1, '==': lambda a, b: (a == b) * 1,
       'min': np.minimum, 'max': np.maximum}
def build(maxsize, cap=60000, lib=()):
    bank = {}; seen = {}; bysize = {}
    def add(e, t, s):
        if (t.min() < -999) or (t.max() > 999): return
        t = t.astype(np.int16); k = hash(t.tobytes())
        if k in seen: return
        seen[k] = 1; bysize.setdefault(s, []).append((e, t))
    for k, t in LEAVES.items(): add(k, t.astype(np.int64), 1)
    for s in range(2, maxsize + 1):
        for sa in range(s - 2, 0, -1):
            sb = s - 1 - sa
            if sb < 1: continue
            for ea, ta in bysize.get(sa, []):
                ta = ta.astype(np.int32)
                for eb, tb in bysize.get(sb, []):
                    tb = tb.astype(np.int32)
                    if len(bysize.get(s, [])) >= cap: break
                    for op, fn in BIN.items():
                        if op in ('+', '*', 'min', 'max', '==') and repr(ea) > repr(eb): continue
                        if op == '//' or op == '%':
                            if (tb == 0).any(): continue
                            t = np.floor_divide(ta, tb) if op == '//' else np.mod(ta, tb)
                        else: t = fn(ta, tb)
                        add((op, ea, eb), t, s)
        if 4 <= s <= 6:  # ite(c,a,b) = 1+sc+sa+sb
            for sc in range(1, s - 2):
                for sa in range(1, s - 1 - sc):
                    sb = s - 1 - sc - sa
                    if sb < 1: continue
                    for ec, tc in bysize.get(sc, []):
                        if tc.min() < 0 or tc.max() > 1 and sc > 3: pass
                        for ea, ta in bysize.get(sa, []):
                            for eb, tb in bysize.get(sb, []):
                                add(('ite', ec, ea, eb), np.where(tc != 0, ta, tb), s)
        for (lop, lc) in lib:  # learned library ops: (op, const) applied to any expr, cost 1 more than the child
            for ea, ta in list(bysize.get(s - 1, [])):
                c = int(lc); ta32 = ta.astype(np.int32)
                add((lop, ea, lc), np.floor_divide(ta32, c) if lop == '//' else np.mod(ta32, c) if lop == '%' else None, s) if lop in ('//', '%') else None
        if len(bysize.get(s, [])) > cap: bysize[s] = bysize[s][:cap]
        print('  dsl size', s, len(bysize.get(s, [])), file=sys.stderr)
    return bysize
def src(e):
    if isinstance(e, str): return e
    if e[0] == 'ite': return f'({src(e[2])} if {src(e[1])} else {src(e[3])})'
    if e[0] in ('min', 'max'): return f'{e[0]}({src(e[1])},{src(e[2])})'
    if e[0] in ('<', '>', '=='): return f'(1 if {src(e[1])}{e[0]}{src(e[2])} else 0)'
    return f'({src(e[1])}{e[0]}{src(e[2])})'
def fn(e): return eval(f'lambda x,y,r: {src(e)}')
# ---------- machine ----------
def run(prog, xs, ys):
    rd, wr, mode, f, g = prog
    n = len(xs); order = range(n) if rd == 'fwd' else range(n - 1, -1, -1)
    r = 0; out = []
    for i in order:
        x, y = xs[i], (ys[i] if ys else 0)
        if mode != 'final': out.append(f(x, y, r))
        r = g(x, y, r)
    if mode == 'final': return [f(0, 0, r)]
    if mode == 'tape+r': out.append(r)
    return out if wr == 'fwd' else out[::-1]
# ---------- tasks (digit lists MSB-first) ----------
def num(ds): return int(''.join(map(str, ds))) if ds else 0
def digs(v, n): return [int(c) for c in str(v).zfill(n)]
def mk(task, rng, n):
    if task in ('add', 'sub', 'compare'):
        a, b = rng.randrange(10**n), rng.randrange(10**n)
        if task == 'sub' and rng.random() < .5:
            k = rng.randrange(n); a = rng.randrange(1, 10**n) // 10**k * 10**k; b = rng.randrange(0, a + 1)
        if task == 'sub' and a < b: a, b = b, a
        if task == 'compare' and rng.random() < .6:
            k = rng.randrange(n + 1); b = int(str(a).zfill(n)[:k] + ''.join(str(rng.randrange(10)) for _ in range(n - k))) if k else b
        xs, ys = digs(a, n), digs(b, n)
        o = digs(a + b, n + 1) if task == 'add' else digs(a - b, n) if task == 'sub' else [1 if a > b else 0]
        return xs, ys, o
    if task in ('mul1', 'addmod'):
        a = rng.randrange(10**n); m = rng.randrange(10); xs = digs(a, n)
        if task == 'mul1': return xs, [m] * n, digs(a * m, n + 1)
        b = rng.randrange(10**n); ys = digs(b, n); return xs, ys, [(p + q) % 10 for p, q in zip(xs, ys)]
    xs = [rng.randrange(10) for _ in range(n)]
    o = {'reverse': xs[::-1], 'copy': xs[:], 'inc': [(v + 1) % 10 for v in xs], 'count3': [sum(v == 3 for v in xs)],
         'sumdigits': [sum(xs)], 'max': [max(xs)], 'parity_sum': [sum(xs) % 2], 'first_gt_last': [1 if xs[0] > xs[-1] else 0]}[task]
    return xs, None, o
TASKS = ['copy', 'inc', 'reverse', 'count3', 'sumdigits', 'max', 'parity_sum', 'add', 'sub', 'compare']
_CACHE = {}
def search(train, bysize, maxs):
    """shortest total size first; returns (prog, sizeG, sizeF, nconsistent_tried)"""
    pairs = [(xs, ys, o) for xs, ys, o in train]
    two = pairs[0][1] is not None
    if 'Ft' not in _CACHE:
        n = sum(len(v) for v in bysize.values()); Ft = np.empty((n, gx.size), np.int16); banks = []; i = 0
        for s in sorted(bysize):
            for e, t in bysize[s]: Ft[i] = t; banks.append((s, e, None)); i += 1
            bysize[s] = []
        _CACHE.update(Ft=Ft, banks=banks, Fs=np.array([b[0] for b in banks]))
    Ft, banks, Fs = _CACHE['Ft'], _CACHE['banks'], _CACHE['Fs']
    best = None
    for mode in ('tape', 'tape+r', 'final'):
        L = len(pairs[0][2])
        for rd in ('fwd', 'bwd'):
            for wr in (('fwd', 'bwd') if mode != 'final' else ('fwd',)):
                if mode != 'final' and not all(len(o) == len(xs) + (mode == 'tape+r') for xs, _, o in pairs): continue
                if mode == 'final' and not all(len(o) == 1 for _, _, o in pairs): continue
                if mode == 'tape' and wr == 'bwd' and rd == 'fwd': pass
                for gi, (sg, eg, _) in enumerate(banks):
                    tg = Ft[gi]
                    if best and sg >= best[0]: break
                    if mode == 'final' and False: pass
                    cons = {}; ok = True
                    for xs, ys, o in pairs:
                        n = len(xs); order = list(range(n)) if rd == 'fwd' else list(range(n - 1, -1, -1))
                        tape_o = list(o) if wr == 'fwd' else list(o)[::-1]
                        r = 0
                        for k, i in enumerate(order):
                            x, y = xs[i], (ys[i] if ys else 0)
                            key = idx(x, y, r)
                            if mode != 'final':
                                if cons.setdefault(key, tape_o[k]) != tape_o[k]: ok = False; break
                            r = int(tg[key])
                            if not (RLO <= r <= RHI): ok = False; break
                        if not ok: break
                        if mode == 'tape+r':
                            if tape_o[n] != r: ok = False; break  # final carry emitted raw: f(r)=r only if o==r
                        if mode == 'final':
                            key = idx(0, 0, r)
                            if cons.setdefault(key, o[0]) != o[0]: ok = False; break
                    if not ok: continue
                    keys = np.array([k for k in cons if not isinstance(k, tuple)]); vals = np.array([cons[k] for k in keys])
                    if len(keys) == 0: continue
                    m = (Ft[:, keys] == vals).all(axis=1)
                    # additionally penalise f depending on y when single tape: irrelevant
                    cand = np.where(m)[0]
                    if len(cand):
                        fi = cand[np.argmin(Fs[cand])]
                        tot = sg + Fs[fi]
                        if best is None or tot < best[0]:
                            best = (tot, (rd, wr, mode, fn(banks[fi][1]), fn(eg)), (src(banks[fi][1]), src(eg)))
    return best
if __name__ == '__main__':
    maxs = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    only = sys.argv[2:] or TASKS
    t0 = time.time(); bysize = build(maxs); print('dsl built', round(time.time() - t0, 1), 's', sum(len(v) for v in bysize.values()), 'distinct exprs')
    for task in only:
        rng = random.Random(1)
        train = [mk(task, rng, rng.choice([1, 2, 3, 4] if task in ('sub', 'compare') else [1, 2, 3])) for _ in range(40 if task in ('sub', 'compare') else 20)]
        t1 = time.time(); best = search(train, bysize, maxs); dt = time.time() - t1
        if not best: print(f'{task:12s} NOT FOUND (size<= {maxs}) {dt:.0f}s'); continue
        prog = best[1]; res = []
        for n in (4, 6, 10, 20, 50):
            ok = 0
            for _ in range(200):
                xs, ys, o = mk(task, rng, n)
                if task == 'count3' and n == 50: pass
                ok += run(prog, xs, ys) == o
            res.append(f'{n}:{ok/2:.0f}%')
        # unseen same-length held-out
        ok = sum(run(prog, *mk(task, rng, 3)[:2]) == mk(task, random.Random(0), 3)[2] for _ in range(0))
        print(f'{task:12s} f={best[2][0]}  g={best[2][1]}  {prog[0]}/{prog[1]}/{prog[2]} size={best[0]} {dt:.0f}s  gen: ' + ' '.join(res), flush=True)
