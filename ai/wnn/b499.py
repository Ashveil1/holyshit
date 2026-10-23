"""B-499: fewest-examples curve, curriculum8 - n in {2,4,8,16,25} nested prefixes of ONE seed-0 draw. LEDGER B-499."""
import json, random, time
import cur7

def run_cell(task, n, seed, cap=6_000_000):
    for k in [k for k in cur7.LIB if k not in ('add', 'sub')]: del cur7.LIB[k]
    cur7.EXCL.clear(); cur7.EXCL.add(task); cur7.search._baselib_done = False
    cur7.VALID[:] = []; cur7.ADV[:] = []
    cur7.ev.cache_clear()
    rng = random.Random(seed)
    train = [cur7.gen(task, rng, rng.choice([1, 2])) for _ in range(25)]  # same draw for every n
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
            'prog': cur7.show_prog(p) if p else None, 'gen': gen}

for task in ('mod', 'mul', 'div', 'power', 'gcd', 'isprime', 'fact', 'sumto'):
    for n in (2, 4, 8, 16, 25):
        print(json.dumps(run_cell(task, n, 0)), flush=True)
print('DONE', flush=True)
