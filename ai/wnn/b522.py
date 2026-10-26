"""B-522: decisive learned-vs-copied tests (the requester follow-up to B-521). Frames INDUCED from corpus
(slot replacement: name->X, attr->A, pattern counting), retrieval-copier baseline arm.
LEDGER pre-reg 2026-10-24. T1 compositional gap, T2 impossible conjunction, T3 novel-animal
composition, T4 unknown-word distractor."""
import random, json
from collections import defaultdict, Counter
from itertools import combinations

ANIMALS = {
 'นก': {'ปีก', 'หาง', 'ตา', 'จะงอยปาก'},
 'ค้างคาว': {'ปีก', 'ขน', 'ตา', 'หู'},
 'ผีเสื้อ': {'ปีก', 'เกล็ด', 'ตา'},
 'หมา': {'ขน', 'ขา', 'ตา', 'หาง'},
 'ปลา': {'ครีบ', 'หาง', 'ตา', 'เกล็ด'},
 'แมว': {'ขน', 'ขา', 'ตา', 'หาง', 'หู'},
}
NEW_ANIMAL = {'ช้าง': {'งา', 'ขา', 'ตา', 'หู'}}
FRAMES = ["{x} มี {y}", "{x} นั้น มี {y}", "ดู {y} ของ {x}", "{y} ของ {x} สวย"]
FRAMES2 = ["{x} มี {y} และ {z}", "{y} และ {z} ของ {x}"]
FRAME3 = "{x} มี {y} และ {z} และ {w}"
ATTRS = sorted({a for s in ANIMALS.values() for a in s})
ALL_ANIMALS = dict(ANIMALS); ALL_ANIMALS.update(NEW_ANIMAL)

def gen_corpus(rng, q, gaps=None, add_new_singles=False):
    """gaps: {animal: (a,b)} pair that must never co-occur in any sentence."""
    sents = []
    for name, attrs in ANIMALS.items():
        attrs = sorted(attrs)
        for a in attrs:
            for _ in range(q):
                sents.append(rng.choice(FRAMES).format(x=name, y=a))
        gap = set(gaps[name]) if gaps and name in gaps else set()
        pairs = list(combinations(attrs, 2)); rng.shuffle(pairs)
        for y, z in pairs[:int(0.6 * len(pairs))]:
            if gap and gap <= {y, z}: continue
            sents.append(rng.choice(FRAMES2).format(x=name, y=y, z=z))
        trips = list(combinations(attrs, 3)); rng.shuffle(trips)
        for y, z, w in trips[:max(1, int(0.3 * len(trips)))]:
            if gap and gap <= {y, z, w}: continue
            sents.append(FRAME3.format(x=name, y=y, z=z, w=w))
    if add_new_singles:
        for a in sorted(NEW_ANIMAL['ช้าง']):
            for _ in range(q):
                sents.append(rng.choice(FRAMES).format(x='ช้าง', y=a))
    rng.shuffle(sents)
    return sents

def learn(sents, world):
    C = defaultdict(lambda: defaultdict(float)); tot = defaultdict(float)
    for s in sents:
        toks = s.split()
        for n in [t for t in toks if t in world]:
            tot[n] += 1
            for a in [t for t in toks if t in ATTRS_ALL]: C[n][a] += 1
    return C, tot

ATTRS_ALL = sorted({a for s in ALL_ANIMALS.values() for a in s})

def induce(sents, world):
    """Pattern counting: name token -> X, each attr token -> A. Returns Counter of patterns."""
    pats = Counter()
    for s in sents:
        toks = s.split()
        if not any(t in world for t in toks): continue
        pat = tuple('X' if t in world else ('A' if t in ATTRS_ALL else t) for t in toks)
        pats[pat] += 1
    return pats

def best_pattern(pats, k):
    cands = [(c, p) for p, c in pats.items() if p.count('A') == k and p.count('X') == 1]
    if not cands: return None
    return max(cands)[1]

def describe(C, pats, name, target):
    """Fill the most frequent k-attr induced pattern; attrs ordered by per-animal count desc."""
    pat = best_pattern(pats, len(target))
    if pat is None: return None
    ordered = sorted(target, key=lambda a: -C[name][a])
    it = iter(ordered)
    return ' '.join(name if t == 'X' else (next(it) if t == 'A' else t) for t in pat)

def sent_attrs(s):
    return {t for t in s.split() if t in ATTRS_ALL}

def exact_correct(sent, name, target):
    if sent is None: return False
    toks = sent.split()
    return name in toks and sent_attrs(sent) == set(target)

def copier(sents, name, target):
    """Best corpus sentence containing name, ranked by overlap with target (ties: corpus order)."""
    best, bestov = None, -1
    for s in sents:
        if name not in s.split(): continue
        ov = len(sent_attrs(s) & set(target))
        if ov > bestov: best, bestov = s, ov
    return best

def score(C, tot, probe, world):
    return {n: sum(C[n][a] for a in probe) / max(tot[n], 1e-9) for n in world}

def run(sd, q=8):
    rng = random.Random(sd)
    out = {'seed': sd, 'q': q}
    # ---------- T2 + T4 on full 6-animal corpus ----------
    sents_full = gen_corpus(rng, q)
    C, tot = learn(sents_full, ANIMALS)
    uniq_tops, empty_tops = [], []
    for probe in combinations(ATTRS, 2):
        ext = {n for n, s in ANIMALS.items() if set(probe) <= s}
        if not ext: continue
        sc = score(C, tot, probe, ANIMALS); top = max(sc.values())
        if len(ext) == 1: uniq_tops.append(top)
        else: pass
    empty_pairs = [p for p in combinations(ATTRS_ALL, 2)
                   if not any(set(p) <= s for s in ALL_ANIMALS.values())]
    empty_pairs = [p for p in empty_pairs if all(a in ATTRS for a in p)]  # 6-animal world only
    for probe in empty_pairs:
        sc = score(C, tot, probe, ANIMALS); empty_tops.append(max(sc.values()))
    uniq_tops.sort(); empty_tops.sort()
    med = lambda v: v[len(v)//2]
    out['t2_med_uniq_top'] = round(med(uniq_tops), 4)
    out['t2_med_empty_top'] = round(med(empty_tops), 4)
    out['t2_ratio'] = round(med(empty_tops) / med(uniq_tops), 4)
    out['t2_n_empty'] = len(empty_pairs)
    # T4: unknown-word distractor
    rng4 = random.Random(900 + sd); t4_ok = t4_n = 0
    for r in (1, 2):
        for probe in combinations(ATTRS, r):
            ext = {n for n, s in ANIMALS.items() if set(probe) <= s}
            if not ext: continue
            noisy = list(probe) + ['เขา']
            sc = score(C, tot, noisy, ANIMALS); top = max(sc, key=sc.get)
            t4_n += 1; t4_ok += top in ext
    out['t4_validity'] = round(t4_ok / max(t4_n, 1), 4); out['t4_n'] = t4_n
    # ---------- T1 compositional gap ----------
    gaps = {}
    for name, attrs in ANIMALS.items():
        pairs = list(combinations(sorted(attrs), 2))
        gaps[name] = rng.choice(pairs)
    sents_gap = gen_corpus(random.Random(sd), q, gaps=gaps)
    Cg, totg = learn(sents_gap, ANIMALS)
    pats_g = induce(sents_gap, ANIMALS)
    t1_ok = t1_n = 0; cop_ok = 0; cop_cov = []
    for name, gp in gaps.items():
        target = set(gp)
        m = describe(Cg, pats_g, name, target)
        t1_n += 1; t1_ok += exact_correct(m, name, target)
        c = copier(sents_gap, name, target)
        if c is not None:
            cop_cov.append(len(sent_attrs(c) & target) / len(target))
            if exact_correct(c, name, target): cop_ok += 1
    out['t1_model'] = f'{t1_ok}/{t1_n}'; out['t1_copier_exact'] = cop_ok
    out['t1_copier_cov'] = round(sum(cop_cov) / len(cop_cov), 4)
    # ---------- T3 novel animal ----------
    sents_new = gen_corpus(random.Random(sd), q, add_new_singles=True)
    Cn, totn = learn(sents_new, ALL_ANIMALS)
    pats_n = induce(sents_new, ALL_ANIMALS)
    for k, target in ((2, {'งา', 'ขา'}), (3, {'งา', 'ขา', 'หู'})):
        m = describe(Cn, pats_n, 'ช้าง', target)
        c = copier(sents_new, 'ช้าง', target)
        out[f't3_k{k}_model'] = exact_correct(m, 'ช้าง', target)
        out[f't3_k{k}_model_sent'] = m
        out[f't3_k{k}_copier_exact'] = exact_correct(c, 'ช้าง', target)
    sc = score(Cn, totn, {'งา'}, ALL_ANIMALS)
    out['t3b_revID_งา'] = max(sc, key=sc.get)
    return out

if __name__ == '__main__':
    for sd in range(5):
        print(json.dumps(run(sd), ensure_ascii=False), flush=True)
    print('DONE', flush=True)
