"""B-523: root-cause + fix for impossible-combination lookup (the requester follow-up to B-522 T2 FAIL).
Part 1 verifies the mechanism (per-attribute decomposition of empty-pair top scores).
Part 2 replaces additive lookup with a three-way decision over the SAME learned counts:
UNKNOWN (word never taught anywhere) / NO MATCH (not taught together) / AMBIGUOUS (full
extension) / UNIQUE. LEDGER pre-reg 2026-10-24."""
import random, json
from collections import defaultdict
from itertools import combinations
from b521 import ANIMALS, ATTRS, gen_corpus

def learn(sents, shuffle_attrs=False, rng=None):
    C = defaultdict(lambda: defaultdict(float)); tot = defaultdict(float)
    for s in sents:
        toks = s.split()
        for n in [t for t in toks if t in ANIMALS]:
            tot[n] += 1
            for a in [t for t in toks if t in ATTRS]: C[n][a] += 1
    if shuffle_attrs:
        perm = ATTRS[:]; rng.shuffle(perm)
        C2 = defaultdict(lambda: defaultdict(float))
        for n in C:
            for i, a in enumerate(ATTRS):
                if C[n][a]: C2[n][perm[i]] = C[n][a]
        return C2, tot
    return C, tot

def old_score(C, tot, probe):
    return {n: sum(C[n][a] for a in probe) / max(tot[n], 1e-9) for n in ANIMALS}

def decide(C, probe):
    """Three-way decision over learned counts. Returns (kind, payload)."""
    taught_anywhere = {a for n in ANIMALS for a in C[n] if C[n][a] > 0}
    known = [a for a in probe if a in taught_anywhere]
    unknown = [a for a in probe if a not in taught_anywhere]
    if not known:
        return 'unknown_all', {'unknown': unknown}
    ext = sorted(n for n in ANIMALS if all(C[n][a] > 0 for a in known))
    if not ext:
        return 'no_match', {'unknown': unknown}
    if len(ext) > 1:
        return 'ambiguous', {'ext': ext, 'unknown': unknown}
    return 'unique', {'answer': ext[0], 'unknown': unknown}

def run(sd, q=8):
    rng = random.Random(sd)
    sents = gen_corpus(rng, q)
    C, tot = learn(sents)
    out = {'seed': sd}
    # ---- Part 1: root-cause measurement ----
    empty_pairs = [p for p in combinations(ATTRS, 2)
                   if not any(set(p) <= s for s in ANIMALS.values())]
    cover1 = 0
    for probe in empty_pairs:
        sc = old_score(C, tot, probe); top = max(sc, key=sc.get)
        if sum(1 for a in probe if C[top][a] > 0) == 1: cover1 += 1
    out['rootcause_top_covers_exactly_1_of_2'] = f'{cover1}/{len(empty_pairs)}'
    # ---- Part 2: fixed decision rule ----
    t1 = t2_ok = t2_n = t3_ok = t3_n = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext_true = sorted(n for n, s in ANIMALS.items() if set(probe) <= s)
            kind, pl = decide(C, probe)
            if not ext_true:
                if r == 2: t1 += (kind == 'no_match')
            elif len(ext_true) == 1:
                t2_n += 1; t2_ok += (kind == 'unique' and pl['answer'] == ext_true[0])
            else:
                t3_n += 1; t3_ok += (kind == 'ambiguous' and pl['ext'] == ext_true)
    out['t1_abstain_empty_pairs'] = f'{t1}/{len(empty_pairs)}'
    out['t2_unique_correct'] = f'{t2_ok}/{t2_n}'
    out['t3_ambiguous_exact_ext'] = f'{t3_ok}/{t3_n}'
    # T4 unknown word
    t4_ok = t4_n = t4_flag = 0
    for r in (1, 2):
        for probe in combinations(ATTRS, r):
            ext_true = {n for n, s in ANIMALS.items() if set(probe) <= s}
            if not ext_true: continue
            kind, pl = decide(C, list(probe) + ['เขา'])
            t4_n += 1
            t4_flag += ('เขา' in pl.get('unknown', []))
            if kind == 'unique': t4_ok += pl['answer'] in ext_true
            elif kind == 'ambiguous': t4_ok += set(pl['ext']) == ext_true
    out['t4_unknown_flagged'] = f'{t4_flag}/{t4_n}'
    out['t4_valid_on_known_part'] = f'{t4_ok}/{t4_n}'
    # T5 shuffled control: unique-ID accuracy under the new rule
    Cs, _ = learn(sents, shuffle_attrs=True, rng=random.Random(100 + sd))
    c_ok = c_n = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext_true = sorted(n for n, s in ANIMALS.items() if set(probe) <= s)
            if len(ext_true) != 1: continue
            kind, pl = decide(Cs, probe)
            c_n += 1; c_ok += (kind == 'unique' and pl['answer'] == ext_true[0])
    out['t5_ctrl_unique'] = round(c_ok / max(c_n, 1), 4)
    # example for the report
    out['example_beak_fur'] = decide(C, {'จะงอยปาก', 'ขน'})
    out['example_wing'] = decide(C, {'ปีก'})
    return out

if __name__ == '__main__':
    for sd in range(5):
        print(json.dumps(run(sd), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
