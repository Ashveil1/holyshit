"""B-515 (F-6): OOPS-style doubling scheduler over cur7's comb generators vs P14 baseline ordering.
Lists captured verbatim from cur7.search via LIST_CAPTURE; test body copied verbatim. LEDGER pre-reg 2026-10-24."""
import sys, json, time
import cur7
from cur7 import (search, run, inits_for, POST, Fail, boundary, gen, ADV, VALID, LIB, EXCL,
                  LIST_CAPTURE as _LC)
import cur7 as C

ABL = 'init10,baselib,simp,adv'
CAP = 6_000_000

def setup(task, seed=0):
    rng = C.random.Random(seed)
    train = [gen(task, rng, rng.choice([1, 2])) for _ in range(25)]
    for t0 in ('mod', 'mul', 'div', 'power', 'gcd', 'max', 'min'): LIB.pop(t0, None)
    search._baselib_done = False
    EXCL.clear(); EXCL.add(task)
    VALID[:] = []; ADV[:] = boundary(task)
    return train

def capture_lists(train):
    C.LIST_CAPTURE = {}
    search(train, ABL, tried_cap=0)
    lists = dict(C.LIST_CAPTURE); C.LIST_CAPTURE = None
    return lists

def test_spec(spec, init, train):
    """Verbatim copy of cur7.search's per-candidate test body (r0 screen -> staged train -> VALID -> ADV).
    Returns pn on success else None. PROF bookkeeping omitted (diagnostics only)."""
    x0, y0, r0 = train[0]
    try: v0 = run(spec, x0, inits_for(init, y0))
    except Fail: return None
    except (KeyError, ZeroDivisionError, RecursionError, OverflowError): return None
    pm = [pn for pn, pf in POST.items() if pf(v0) == r0]
    for pn in pm:
        ok = True
        stages = (train[1:6], train[6:]) if 'sub' in ABL else (train[1:],)
        for stage in stages:
            if not ok: break
            for x, y, r in stage:
                try:
                    if POST[pn](run(spec, x, inits_for(init, y))) != r: ok = False; break
                except (Fail, KeyError, RecursionError, OverflowError): ok = False; break
        if ok and VALID:
            for x, y, r in VALID:
                try:
                    if POST[pn](run(spec, x, inits_for(init, y))) != r: ok = False; break
                except (Fail, KeyError, RecursionError, OverflowError, ZeroDivisionError): ok = False; break
        if ok and ADV:
            for x, y, r in ADV:
                try:
                    if POST[pn](run(spec, x, inits_for(init, y))) != r: ok = False; break
                except (Fail, KeyError, RecursionError, OverflowError, ZeroDivisionError): ok = False; break
        if ok: return pn
    return None

def gen_enum(comb, init, L):
    st = L['steps_pair'] if comb is None else L['steps_single']
    for cond in L['conds']:
        for base in L['bases']:
            for (s0, s1) in st:
                yield (cond, base, s0, s1, comb)

def search_oops(train, L, phase_cap, cap=CAP):
    """Doubling scheduler. phase_cap(phase) -> cumulative per-generator tried cap.
    Sanity mode: lambda p: cap (single phase = baseline order). OOPS: 256*2**p."""
    t0 = time.time(); tried = 0
    gens = [(comb, init) for comb in L['combs'] for init in L['inits']]
    arms = [{'it': gen_enum(c, i, L), 'init': i, 'tried': 0, 'dead': False} for c, i in gens]
    phase = 0
    while tried <= cap:
        pc = phase_cap(phase)
        active = False
        for a in arms:
            if a['dead'] or a['tried'] >= pc: continue
            active = True
            while a['tried'] < pc and tried <= cap:
                try: spec = next(a['it'])
                except StopIteration:
                    a['dead'] = True; break
                a['tried'] += 1; tried += 1
                pn = test_spec(spec, a['init'], train)
                if pn is not None:
                    return (a['init'], spec, pn), tried, time.time() - t0
        if not active: break
        phase += 1
    return None, tried, time.time() - t0

if __name__ == '__main__':
    mode = sys.argv[1]  # sanity | baseline | oops
    for task in sys.argv[2].split(','):
        train = setup(task)
        t0 = time.time()
        if mode == 'baseline':
            p, tried, dt = search(train, ABL, tried_cap=CAP)
        else:
            L = capture_lists(train)
            pc = (lambda p: CAP) if mode == 'sanity' else (lambda p: 256 * 2 ** p)
            p, tried, dt = search_oops(train, L, pc)
        row = {'mode': mode, 'task': task, 'found': p is not None, 'tried': tried, 'dt': round(dt, 1)}
        if p is not None:
            row['prog'] = C.show_prog(p)
            f = C.make_fn(p); C.CAPF[0] = 20000
            te = C.random.Random(1000)
            acc = {}
            for sc in (1, 2, 3, 4):
                ok = 0
                for _ in range(40):
                    x, y, r = gen(task, te, sc)
                    try: ok += f(x, y) == r
                    except Exception: pass
                acc[str(sc)] = ok
            row['unseen'] = acc
        print(json.dumps(row), flush=True)
