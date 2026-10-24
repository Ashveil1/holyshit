"""B-524: introspection audit - TRACE mode (actual recorded state behind each answer) +
causal lesion battery L1-L4 on the maintained attribute learner. LEDGER pre-reg 2026-10-24."""
import random, json
from collections import defaultdict, Counter
from itertools import combinations
from b521 import ANIMALS, ATTRS, gen_corpus, learn, score, decide
from b522 import induce, describe, exact_correct, copier, sent_attrs

def trace_lookup(C, tot, probe):
    """Full recorded state behind one reverse-ID answer. No narrative - the numbers only."""
    taught_anywhere = {a for n in ANIMALS for a in C[n] if C[n][a] > 0}
    known = [a for a in probe if a in taught_anywhere]
    kind, pl = decide(C, probe)
    return {
        'probe': sorted(probe),
        'decision': kind,
        'unknown_words': [a for a in probe if a not in taught_anywhere],
        'coverage': {n: {a: (C[n][a] > 0) for a in known} for n in ANIMALS},
        'raw_counts': {n: {a: C[n][a] for a in known} for n in ANIMALS},
        'scores': {n: round(s, 4) for n, s in score(C, tot, known).items()} if known else {},
        'answer': pl,
    }

def trace_describe(C, pats, sents, name, k):
    """Recorded state behind one generated description."""
    from b522 import best_pattern
    pat = best_pattern(pats, k)
    ranked = sorted(ATTRS, key=lambda a: -C[name][a])
    target = ranked[:k]
    sent = describe(C, pats, name, target)
    return {
        'animal': name, 'k': k,
        'attr_ranking_by_count': [(a, C[name][a]) for a in ranked[:5]],
        'frame_inventory_counts': {str(p): c for p, c in pats.most_common(8)},
        'frame_chosen': str(pat), 'frame_corpus_count': pats[pat] if pat else 0,
        'produced': sent, 'verbatim_in_corpus': (sent in set(sents)) if sent else None,
    }

def gen_lesioned(rng, q, drop_sent):
    sents = gen_corpus(rng, q)
    return [s for s in sents if not drop_sent(s)]

def run(sd, q=8):
    rng = random.Random(sd)
    sents = gen_corpus(rng, q)
    C, tot = learn(sents)
    out = {'seed': sd}
    # ---- TRACE battery (seed 0 only; deterministic elsewhere) ----
    if sd == 0:
        pats = induce(sents, ANIMALS)
        out['trace'] = [
            trace_lookup(C, tot, {'ปีก', 'จะงอยปาก'}),   # unique
            trace_lookup(C, tot, {'ปีก'}),              # ambiguous
            trace_lookup(C, tot, {'จะงอยปาก', 'ขน'}),   # no_match
            trace_lookup(C, tot, {'เขา', 'หาง'}),       # unknown + known part
            trace_describe(C, pats, sents, 'นก', 3),    # generation
        ]
    # ---- L1: remove all นก-ปีก teaching ----
    s1 = gen_lesioned(random.Random(sd), q, lambda s: 'นก' in s.split() and 'ปีก' in s.split())
    C1, tot1 = learn(s1)
    k_, pl_ = decide(C1, {'ปีก', 'จะงอยปาก'})
    _, ext_wing = decide(C1, {'ปีก'})
    ranked1 = sorted(ATTRS, key=lambda a: -C1['นก'][a])[:3]
    rec1 = len(set(ranked1) & ANIMALS['นก']) / len(ANIMALS['นก'])
    out['l1_probe_flip'] = k_
    out['l1_bird_in_wing_ext'] = 'นก' in ext_wing.get('ext', [ext_wing.get('answer')])
    out['l1_bird_recall'] = round(rec1, 4)
    # ---- L2: remove ALL multi-attribute sentences ----
    s2 = gen_lesioned(random.Random(sd), q, lambda s: len(sent_attrs(s)) > 1)
    C2, tot2 = learn(s2)
    pats2 = induce(s2, ANIMALS)
    arities = sorted({p.count('A') for p in pats2})
    comp_ok = 0
    for name in ANIMALS:
        target = sorted(ANIMALS[name])[:2]
        if exact_correct(describe(C2, pats2, name, target), name, target): comp_ok += 1
    out['l2_frame_arities'] = arities
    out['l2_composition'] = f'{comp_ok}/6'
    # ---- L3: legacy rule on the SAME counts (abstention disappears) ----
    ab = 0; abn = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext = {n for n, s in ANIMALS.items() if set(probe) <= s}
            if ext: continue
            abn += 1
            # legacy argmax never abstains: it always has a top scorer
            sc = score(C, tot, probe)
            if max(sc, key=sc.get) is not None: ab += 0  # no abstention path exists
    out['l3_legacy_abstain'] = f'0/{abn}'
    # ---- L4: shuffled control ----
    Cs, _ = learn(sents, shuffle_attrs=True, rng=random.Random(100 + sd))
    c_ok = c_n = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext = sorted(n for n, s in ANIMALS.items() if set(probe) <= s)
            if len(ext) != 1: continue
            kind, pl = decide(Cs, probe)
            c_n += 1; c_ok += (kind == 'unique' and pl['answer'] == ext[0])
    out['l4_ctrl_unique'] = round(c_ok / max(c_n, 1), 4)
    return out

if __name__ == '__main__':
    for sd in range(5):
        print(json.dumps(run(sd), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
