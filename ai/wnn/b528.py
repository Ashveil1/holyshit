"""B-528 (engineered-connectome arm 1): STD-style depletion gate for novelty-aware generation.
ON arm: combination selection score = strength / (1 + beta * taught_count), where taught_count
= P[name][combo] co-occurrence in the overheard corpus (heard = used; engineered habituation
over learned counts - NOT a biological claim). OFF arm = same combo-argmax machinery without
the gate (identical to B-521 T2 top-k selection by sum of counts). SHAM arm = gate applied to
a RANDOM equal-sized set of combos (credit assignment, B-505 lesson). beta = 1 pre-set.
LEDGER pre-reg 2026-10-24."""
import random, json
from collections import defaultdict
from itertools import combinations
from b521 import ANIMALS, ATTRS, FRAMES2, FRAME3, gen_corpus
from b526 import CountBackend, battery

BETA = 1

def learn_pairs(sents):
    C = defaultdict(lambda: defaultdict(float))
    P = defaultdict(lambda: defaultdict(int))
    for s in sents:
        toks = s.split()
        for n in [t for t in toks if t in ANIMALS]:
            aa = [t for t in toks if t in ATTRS]
            for a in aa: C[n][a] += 1
            for r in (2, 3):
                for combo in combinations(sorted(set(aa)), r):
                    P[n][combo] += 1
    return C, P

def select(C, P, name, r, gate, sham_rng=None):
    cands = list(combinations(ATTRS, r))
    if gate == 'sham':
        t = sum(1 for c in cands if P[name].get(c, 0) > 0)
        depressed = set(sham_rng.sample(cands, min(t, len(cands))))
    best, bestsc = None, -1
    for c in cands:
        strength = sum(C[name][a] for a in c)
        if gate == 'on':
            sc = strength / (1 + BETA * P[name].get(c, 0))
        elif gate == 'sham':
            sc = strength / (1 + BETA * (1 if c in depressed else 0))
        else:
            sc = strength
        if sc > bestsc: bestsc, best = sc, c
    return best

def run(sd, q=8):
    rng = random.Random(sd)
    sents = gen_corpus(rng, q)
    corpus = set(sents)
    C, P = learn_pairs(sents)
    out = {'seed': sd}
    for gate in ('off', 'on', 'sham'):
        sham_rng = random.Random(7000 + sd) if gate == 'sham' else None
        P3 = R3 = nov = 0
        for name, true_attrs in ANIMALS.items():
            top2 = select(C, P, name, 2, gate, sham_rng)
            top3 = select(C, P, name, 3, gate, sham_rng)
            P3 += len(set(top3) & true_attrs) / 3
            R3 += len(set(top3) & true_attrs) / len(true_attrs)
            s2 = FRAMES2[0].format(x=name, y=top2[0], z=top2[1])
            s3 = FRAME3.format(x=name, y=top3[0], z=top3[1], w=top3[2])
            nov += (s2 not in corpus) / 2 + (s3 not in corpus) / 2
        out[gate] = {'t2_prec': round(P3 / 6, 4), 't2_rec': round(R3 / 6, 4),
                     't2_novelty': round(nov / 6, 4)}
    # B-523 battery must be unaffected (gate touches generation only; run on the same counts)
    cb = CountBackend()
    for s in sents: cb.observe(s.split())
    b = battery(cb)
    out['battery'] = {k: f'{v[0]}/{v[1]}' for k, v in b.items()}
    return out

if __name__ == '__main__':
    for sd in range(5):
        print(json.dumps(run(sd), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
