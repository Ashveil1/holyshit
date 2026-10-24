"""B-525: Link A - P26 Hebbian grounding feeds the B-521/B-523 lookup (no given animal-name
lexicon). Baby overhears B-521 corpus sentences with co-present animal scenes, grounds names,
then decide() runs on grounded rows. LEDGER pre-reg 2026-10-24."""
import random, json
from collections import defaultdict
from itertools import combinations
from b521 import ANIMALS, ATTRS, gen_corpus, learn, decide

def run(sd, q=8, rounds=3):
    rng = random.Random(sd)
    names = list(ANIMALS)
    # Build corpus WITH scene tags: each sentence is about one primary animal; we re-generate
    # per-animal so the primary is known (gen_corpus mixes, so regenerate per animal here).
    from b521 import FRAMES, FRAMES2, FRAME3
    heard = []  # (sentence, present_set)
    for _ in range(rounds):
        for name in names:
            attrs = sorted(ANIMALS[name])
            sents = []
            for a in attrs:
                for _ in range(q):
                    sents.append(rng.choice(FRAMES).format(x=name, y=a))
            pairs = list(combinations(attrs, 2)); rng.shuffle(pairs)
            for y, z in pairs[:int(0.6 * len(pairs))]:
                sents.append(rng.choice(FRAMES2).format(x=name, y=y, z=z))
            trips = list(combinations(attrs, 3)); rng.shuffle(trips)
            for y, z, w in trips[:max(1, int(0.3 * len(trips)))]:
                sents.append(FRAME3.format(x=name, y=y, z=z, w=w))
            for s in sents:
                present = {name}
                if rng.random() < 0.3:
                    present.add(rng.choice([n for n in names if n != name]))
                heard.append((s, present, name))
    rng.shuffle(heard)
    # Baby: (a) word->animal Hebbian assoc, (b) word->attribute co-occurrence counts
    assoc = defaultdict(lambda: defaultdict(float))
    C = defaultdict(lambda: defaultdict(float))
    sent_primary = []  # parallel to heard: the primary animal of each sentence
    name_rate_denom = defaultdict(float)
    for s, present, primary in heard:
        name_rate_denom[primary] += 1
        toks = s.split()
        for w in toks:
            for n in names:
                assoc[w][n] += 1.0 if n in present else -0.25
            for a in [t for t in toks if t in ATTRS]:
                C[w][a] += 1
    # Grounded vocabulary: best assoc >= 3 and best >= 2x runner-up
    grounded = {}
    for w, row in assoc.items():
        ranked = sorted(row.items(), key=lambda kv: -kv[1])
        if ranked and ranked[0][1] >= 3 and (len(ranked) == 1 or ranked[0][1] >= 2 * ranked[1][1]):
            grounded[w] = ranked[0][0]
    # Amendment 1: name-ness = assoc[w][n] / primary-sentence count of n; names ~0.9, attributes ~0.3
    vocab = {w: n for w, n in grounded.items() if assoc[w][n] / max(name_rate_denom[n], 1) >= 0.5}
    grounding_ok = sum(1 for n in names if vocab.get(n) == n)
    # decide() over grounded rows: build a restricted count table keyed by the GROUNDED ANIMAL
    Cg = defaultdict(lambda: defaultdict(float))
    for w, animal in vocab.items():
        for a in ATTRS:
            Cg[animal][a] += C[w][a]
    def decide_g(probe):
        taught = {a for n in names for a in Cg[n] if Cg[n][a] > 0}
        known = [a for a in probe if a in taught]
        if not known: return 'unknown_all', {}
        ext = sorted(n for n in names if all(Cg[n][a] > 0 for a in known))
        if not ext: return 'no_match', {}
        if len(ext) > 1: return 'ambiguous', {'ext': ext}
        return 'unique', {'answer': ext[0]}
    u_ok = u_n = a_ok = a_n = ab_ok = ab_n = 0
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext_true = sorted(n for n, s in ANIMALS.items() if set(probe) <= s)
            kind, pl = decide_g(probe)
            if not ext_true:
                ab_n += 1; ab_ok += kind == 'no_match'
            elif len(ext_true) == 1:
                u_n += 1; u_ok += (kind == 'unique' and pl['answer'] == ext_true[0])
            else:
                a_n += 1; a_ok += (kind == 'ambiguous' and pl['ext'] == ext_true)
    return {'seed': sd, 'grounding': f'{grounding_ok}/6', 'vocab': sorted(vocab),
            'uniq': round(u_ok / max(u_n, 1), 4), 'amb': round(a_ok / max(a_n, 1), 4),
            'abstain': f'{ab_ok}/{ab_n}'}

if __name__ == '__main__':
    for sd in range(5):
        print(json.dumps(run(sd), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
