import json, time, functools, random, sys
sys.setrecursionlimit(100000)
import cur7

# clean config: pin base library, EXCL target task (one-task process)
cur7.EXCL = {'square'}
rng = random.Random(0)
full = [cur7.gen('square', rng, rng.choice([1, 2])) for _ in range(25)]
train = full[:5]  # R5
CAP = 400000

def run_arm(name):
    cur7.ev.cache_clear() if hasattr(cur7.ev, 'cache_clear') else None
    t0 = time.time()
    res = cur7.search(train, 'baselib', tag=name, tried_cap=CAP)
    dt = time.time() - t0
    found, tried, sdt = res
    row = {'arm': name, 'tried': tried, 'wall': dt, 'found': bool(found),
           'prog': cur7.show_prog(found) if found else None,
           'cache': str(cur7.ev.cache_info()) if hasattr(cur7.ev, 'cache_info') else 'none'}
    print(json.dumps(row, default=str), flush=True)
    return row

raw = cur7.ev.__wrapped__  # underlying uncached function
rows = []
rows.append(run_arm('A_lru300k'))
cur7.ev = functools.lru_cache(maxsize=2000000)(raw)
rows.append(run_arm('B_lru2m'))
cur7.ev = raw
rows.append(run_arm('C_nocache'))
# decision identity check
base = rows[0]
for r in rows[1:]:
    r['decisions_identical'] = (r['tried'] == base['tried'] and r['found'] == base['found'] and r['prog'] == base['prog'])
    print(json.dumps({'check': r['arm'], 'decisions_identical': r['decisions_identical']}), flush=True)
print('DONE', flush=True)
