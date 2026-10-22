import json, time
# B-496: exact chained arithmetic 10x P5 (4750 ops). Exact key-value recall:
# the SAME 100-entry successor table serves any chain length; errors cannot
# compound (exact = exact), memory does not grow with chain length.
succ = {x: (x + 1) % 100 for x in range(100)}  # P5 T1 table, unchanged
K = 4750
t0 = time.time()
ok = 0
for a in range(100):
    v = a
    for _ in range(K):
        v = succ[v]
    ok += (v == (a + K) % 100)
dt = time.time() - t0
print(json.dumps({'chain_len': K, 'starts': 100, 'correct': ok,
                  'acc': ok / 100, 'ops': 100 * K, 'wall_s': round(dt, 3),
                  'table_entries': len(succ)}), flush=True)
print('DONE', flush=True)
