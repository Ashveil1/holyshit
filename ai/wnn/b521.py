"""B-521: attribute<->concept feasibility (Ash's bird question). Reverse-identify an animal from
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

def t1(C, tot):
    uniq_ok = uniq_n = amb_ok = amb_n = 0
    wing_sc = score(C, tot, {'ปีก'}); sw = sorted(wing_sc.values(), reverse=True)
    wing_margin = (sw[0] - sw[1]) / max(sw[0], 1e-9)
    for r in (1, 2, 3):
        for probe in combinations(ATTRS, r):
            ext = {n for n, s in ANIMALS.items() if set(probe) <= s}
            if not ext: continue
            sc = score(C, tot, probe); top = max(sc, key=sc.get)
            if len(ext) == 1: uniq_n += 1; uniq_ok += top in ext
            else: amb_n += 1; amb_ok += top in ext
    return uniq_ok / max(uniq_n, 1), amb_ok / max(amb_n, 1), wing_margin

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

def run(sd, q):
    rng = random.Random(sd)
    sents = gen_corpus(rng, q)
    C, tot = learn(sents)
    u, a, wm = t1(C, tot); p, r, nv, ex = t2(C, tot, sents)
    Cs, _ = learn(sents, shuffle_attrs=True, rng=random.Random(100 + sd))
    us, as_, _ = t1(Cs, tot)
    return {'seed': sd, 'q': q, 't1_uniq': round(u, 4), 't1_amb': round(a, 4), 'wing_margin': round(wm, 3),
            't2_prec': round(p, 4), 't2_rec': round(r, 4), 't2_novelty': round(nv, 4),
            'ctrl_uniq': round(us, 4), 'ctrl_amb': round(as_, 4), 'bird_example': ex}

if __name__ == '__main__':
    for q in (3, 8):
        for sd in range(5):
            print(json.dumps(run(sd, q), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
