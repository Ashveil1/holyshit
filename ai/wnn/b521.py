"""B-521: attribute<->concept feasibility (the requester's bird question). Reverse-identify an animal from
an UNORDERED attribute set, and generate NON-VERBATIM combination descriptions (learned frame +
selected content). Co-occurrence counts only. LEDGER pre-reg 2026-10-24 + Amendment 1."""
import random, json
from collections import defaultdict
from itertools import combinations

ANIMALS = {
 'นก': {'ปีก', 'หาง', 'ตา', 'จะงอยปาก'},
 'ค้างคาว': {'ปีก', 'ขน', 'ตา', 'หู'},
 'ผีเสื้อ': {'ปีก', 'เกล็ด', 'ตา'},
 'หมา': {'ขน', 'ขา', 'ตา', 'หาง'},
 'ปลา': {'ครีบ', 'หาง', 'ตา', 'เกล็ด'},
 'แมว': {'ขน', 'ขา', 'ตา', 'หาง', 'หู'},
}
FRAMES = ["{x} มี {y}", "{x} นั้น มี {y}", "ดู {y} ของ {x}", "{y} ของ {x} สวย"]
FRAMES2 = ["{x} มี {y} และ {z}", "{y} และ {z} ของ {x}"]
FRAME3 = "{x} มี {y} และ {z} และ {w}"
ATTRS = sorted({a for s in ANIMALS.values() for a in s})

def gen_corpus(rng, q):
    sents = []
    for name, attrs in ANIMALS.items():
        attrs = sorted(attrs)
        for a in attrs:
            for _ in range(q):
                sents.append(rng.choice(FRAMES).format(x=name, y=a))
        pairs = list(combinations(attrs, 2)); rng.shuffle(pairs)
        for y, z in pairs[:int(0.6 * len(pairs))]:
            sents.append(rng.choice(FRAMES2).format(x=name, y=y, z=z))
        trips = list(combinations(attrs, 3)); rng.shuffle(trips)
        for y, z, w in trips[:max(1, int(0.3 * len(trips)))]:
            sents.append(FRAME3.format(x=name, y=y, z=z, w=w))
    rng.shuffle(sents)
    return sents

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

def score(C, tot, probe):
    return {n: sum(C[n][a] for a in probe) / max(tot[n], 1e-9) for n in ANIMALS}


def decide(C, probe):
    """B-523 fixed lookup: three-way decision over the learned counts.
    UNKNOWN words (never taught with any animal) are reported and excluded;
    NO MATCH when no taught animal covers all known probe attributes (semantics:
    'not taught together', not world-impossibility); AMBIGUOUS returns the full
    extension; UNIQUE answers. The counts are learned; this rule is designed
    architecture (same status as the old argmax) - not learned behavior."""
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

def t1(C, tot, legacy=False):
    uniq_ok = uniq_n = amb_ok = amb_n = 0
    abstain_ok = abstain_n = 0
    wing_sc = score(C, tot, {'ปีก'}); sw = sorted(wing_sc.values(), reverse=True)
    wing_margin = (sw[0] - sw[1]) / max(sw[0], 1e-9)
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext = {n for n, s in ANIMALS.items() if set(probe) <= s}
            if legacy:
                if not ext: continue
                sc = score(C, tot, probe); top = max(sc, key=sc.get)
                if len(ext) == 1: uniq_n += 1; uniq_ok += top in ext
                else: amb_n += 1; amb_ok += top in ext
            else:
                # B-523 fixed path. amb metric STRENGTHENED: exact extension, not top-in-ext.
                if not ext:
                    kind, _ = decide(C, probe)
                    abstain_n += 1; abstain_ok += kind == 'no_match'
                    continue
                kind, pl = decide(C, probe)
                if len(ext) == 1: uniq_n += 1; uniq_ok += (kind == 'unique' and pl['answer'] in ext)
                else: amb_n += 1; amb_ok += (kind == 'ambiguous' and set(pl['ext']) == ext)
    return uniq_ok / max(uniq_n, 1), amb_ok / max(amb_n, 1), wing_margin, abstain_ok, abstain_n

def t2(C, tot, sents):
    corpus = set(sents); P = R = nov = 0; produced_ex = []
    for name, true_attrs in ANIMALS.items():
        ranked = sorted(ATTRS, key=lambda a: -C[name][a])
        top3, top2 = ranked[:3], ranked[:2]
        P += len(set(top3) & true_attrs) / 3; R += len(set(top3) & true_attrs) / len(true_attrs)
        s2 = FRAMES2[0].format(x=name, y=top2[0], z=top2[1])
        s3 = FRAME3.format(x=name, y=top3[0], z=top3[1], w=top3[2])
        nov += (s2 not in corpus) / 2 + (s3 not in corpus) / 2
        if name == 'นก': produced_ex = [s2, s3]
    return P / 6, R / 6, nov / 6, produced_ex

def run(sd, q, legacy=False):
    rng = random.Random(sd)
    sents = gen_corpus(rng, q)
    C, tot = learn(sents)
    u, a, wm, ab_ok, ab_n = t1(C, tot, legacy=legacy); p, r, nv, ex = t2(C, tot, sents)
    Cs, _ = learn(sents, shuffle_attrs=True, rng=random.Random(100 + sd))
    us, as_, _, _, _ = t1(Cs, tot, legacy=legacy)
    d = {'seed': sd, 'q': q, 't1_uniq': round(u, 4), 't1_amb': round(a, 4), 'wing_margin': round(wm, 3),
         't2_prec': round(p, 4), 't2_rec': round(r, 4), 't2_novelty': round(nv, 4),
         'ctrl_uniq': round(us, 4), 'ctrl_amb': round(as_, 4), 'bird_example': ex,
         'lookup': 'legacy' if legacy else 'decide_b523'}
    if not legacy: d['t1_abstain_empty'] = f'{ab_ok}/{ab_n}'
    return d

if __name__ == '__main__':
    import sys
    legacy = '--legacy' in sys.argv  # reproduces the pre-B-523 additive-argmax lookup
    for q in (3, 8):
        for sd in range(5):
            print(json.dumps(run(sd, q, legacy=legacy), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
