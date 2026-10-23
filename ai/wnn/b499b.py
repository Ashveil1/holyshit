"""B-499 design amendment arm: endpoint cells only (n=2, n=25) per remaining task.
Nested-prefix monotonicity makes found(n) non-decreasing in n, so equal endpoints
prove the whole row flat; middle cells run only on endpoint mismatch. LEDGER B-499 amendment.
Appends to logs/b499_stdout.log (same JSONL protocol as b499.py)."""
import json, random, time
import cur7

def run_cell(task, n, seed, cap=6_000_000):
    for k in [k for k in cur7.LIB if k not in ('add', 'sub')]: del cur7.LIB[k]
    cur7.EXCL.clear(); cur7.EXCL.add(task); cur7.search._baselib_done = False
    cur7.VALID[:] = []; cur7.ADV[:] = []
    cur7.ev.cache_clear()
    rng = random.Random(seed)
    train = [cur7.gen(task, rng, rng.choice([1, 2])) for _ in range(25)]  # same draw as b499.py
    vr = random.Random(5000 + seed)
    cur7.VALID[:] = [cur7.gen(task, vr, sc) for sc in (1, 2) for _ in range(16)]
    t0 = time.time(); p, tried, _ = cur7.search(train[:n], 'baselib val', tried_cap=cap); dt = time.time() - t0
    gen = None
    if p is not None:
        f = cur7.make_fn(p); te = random.Random(1000 + seed); gen = {}; cur7.CAPF[0] = 20000
        for sc in (1, 2, 3, 4):
            ok = 0
            for _ in range(40):
                x, y, r = cur7.gen(task, te, sc)
                try: ok += int(f(x, y) == r)
                except Exception: pass
            gen[sc] = ok
        cur7.CAPF[0] = 400; cur7.ev.cache_clear()
    return {'task': task, 'n': n, 'found': p is not None, 'tried': tried, 'dt': round(dt, 1),
            'prog': cur7.show_prog(p) if p else None, 'gen': gen, 'arm': 'b499b-endpoint'}

cells = [(t, n) for t in ('div', 'power', 'gcd', 'isprime', 'fact', 'sumto') for n in (2, 25)]  # splice 07:45: mul 25 already checkpointed (f9cca93); skipped after container restart
out = open('logs/b499_stdout.log', 'a', buffering=1)
for task, n in cells:
    r = run_cell(task, n, 0)
    out.write(json.dumps(r) + '\n')
    print(json.dumps({'done_cell': (task, n), 'tried': r['tried'], 'dt': r['dt']}), flush=True)
out.write('DONE\n')
print('DONE', flush=True)
