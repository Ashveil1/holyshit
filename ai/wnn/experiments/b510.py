"""B-510 (F-1): contradiction correction / unlearning with status. LEDGER pre-reg 2026-10-24."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import random, json, re
from collections import defaultdict
import text2prog as P
from text2prog import Learner, gen_set, make, T
from text2prog2 import learn_lexicon, apply_lex

# ---------- Probe A: name-fact store ----------
NAMES = ['anna', 'bob', 'cid', 'dao', 'eli', 'fay', 'gio', 'han']
def probe_a(seed, episodes=200):
    rng = random.Random(seed)
    res = defaultdict(int)
    for _ in range(episodes):
        ncorr = rng.randint(0, 3)
        vals = rng.sample(NAMES, ncorr + 1)
        counts = [rng.randint(1, 4) for _ in vals]          # statements per value
        stmts = []
        for v, c in zip(vals, counts):
            stmts += [('actually ' if stmts else '') + f'my name is {v}'] * c
        latest = vals[-1]
        # arm ACCUM
        acc = defaultdict(int)
        for s in stmts: acc[s.split()[-1]] += 1
        amax = max(acc.values()); accum_ans = sorted(acc)[ [acc[k] for k in sorted(acc)].index(amax) ]
        res['accum'] += accum_ans == latest
        # arm DICT
        d = {}
        for s in stmts: d['name'] = s.split()[-1]
        res['dict'] += d['name'] == latest
        # arm STATUS
        store = []
        for s in stmts:
            v = s.split()[-1]
            if s.startswith('actually'):
                for e in store:
                    if e['key'] == 'name': e['status'] = 'superseded'
            store.append({'key': 'name', 'value': v, 'status': 'active', 'i': len(store)})
        active = [e['value'] for e in store if e['key'] == 'name' and e['status'] == 'active']
        res['status'] += (active[-1] if active else None) == latest
    return {k: round(v / episodes, 4) for k, v in res.items()}

# ---------- Probe B: wrong-then-right number word ----------
def learn_lex_status(L, phases, minv=3, rounds=4):
    """Phases in order; a phase's accepted mapping supersedes prior mapping for that word."""
    lex = {}
    for data in phases:
        new = learn_lexicon(L, [('x', t, a) for t, a in data], minv=minv, rounds=rounds)
        # apply_lex inside learn_lexicon used current lex; new mappings supersede
        lex.update(new)
    return lex

UNARY_OPS = ['fact', 'sumto', 'isprime']
def phase_data(rng, word, val, n):
    """n sentences where `word` stands for number val (unary single-number ops only,
    so ans = OPS[op](val) exactly matches the generator semantics)."""
    out = []
    while len(out) < n:
        op = rng.choice(UNARY_OPS)
        tm = rng.choice(T[op][0])
        text = tm.format(a=word, b=word, c=word)
        out.append((text, int(P.OPS[op](val))))
    return out

def probe_b(seed):
    rng = random.Random(1000 + seed)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 300)])
    W = 'samsara'
    rows = []
    for n1 in (5, 10, 20):
        for n2 in (5, 10, 20):
            r1, r2 = random.Random(seed * 100 + n1), random.Random(seed * 100 + n2 + 50)
            v1, v2 = rng.sample(range(2, 10), 2)
            ph1 = phase_data(r1, W, v1, n1); ph2 = phase_data(r2, W, v2, n2)
            lex_batch = learn_lexicon(L, [('x', t, a) for t, a in ph1 + ph2])
            lex_status = learn_lex_status(L, [ph1, ph2])
            prng = random.Random(7000 + seed)
            ok = {k: 0 for k in ('batch', 'status', 'oracle')}; nq = 20
            for _ in range(nq):
                op = rng.choice(UNARY_OPS); tm = rng.choice(T[op][0])
                wtext = tm.format(a=W, b=W, c=W)
                gold = int(P.OPS[op](v2))
                for name, lex in (('batch', lex_batch), ('status', lex_status), ('oracle', {W: v2})):
                    try:
                        if L.answer(apply_lex(wtext, lex))[0] == gold: ok[name] += 1
                    except Exception: pass
            orc = max(ok['oracle'], 1)
            rows.append({'n1': n1, 'n2': n2,
                         'batch_hit': int(lex_batch.get(W) == v2), 'status_hit': int(lex_status.get(W) == v2),
                         'batch_rel': round(ok['batch'] / orc, 3), 'status_rel': round(ok['status'] / orc, 3),
                         'oracle': round(ok['oracle'] / nq, 3)})
    return rows

if __name__ == '__main__':
    for sd in range(5):
        print(json.dumps({'probe': 'A', 'seed': sd, **probe_a(sd)}), flush=True)
    for sd in range(5):
        for row in probe_b(sd):
            print(json.dumps({'probe': 'B', 'seed': sd, **row}), flush=True)
    print('DONE', flush=True)
