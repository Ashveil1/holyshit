"""BABY4 (B-521): two-word composition. Can the baby combine two grounded words into a NOVEL
entity+action pair it never heard, in the right ORDER, using only dialogue statistics?
World: 4 animate entities (mae/pho/cat/dog) x 4 actions (come/stay/eat/sleep) = 16 scenes.
Scene = (entity, action) - 'what' and 'what is happening' are given as separate scene slots
(same level of prior as P26's 'set of present things'). Caregivers speak template Thai,
entity-word before action-word, padded with constant filler words (แล้ว นะ ดู สิ กำลัง เห็น ตรง นั้น ...)
that appear in EVERY scene (ungrounded distractors, incl. distractor verbs).
Train: 480 scenes sampled from a train split of 12 combos; 4 combos held out (one per entity),
every entity and every action still seen in training, so both words of a held-out pair are grounded
but the PAIR is never heard. Learner: P27h-style Hebbian grounding (no reward channel - P27h controls
showed grounding comes from overhearing alone) + order statistics counted over MEANING CLASSES:
for adjacent heard words whose current best meaning is known, count (class1, class2) bigrams.
PRE-STAGED CRITERION (before any run): order correct in >= 90% of held-out novel pairs across 5 seeds
(16 decisions; chance = 50%, binomial p(>=15/16) < 5e-5); direct-bigram arm (memorized word-word
bigrams only; ties = no evidence = coin flip) and bag-of-words arm must sit at chance on the same pairs - otherwise the class-level
generalization is not what does it. Also report order accuracy on TRAINED pairs (sanity, expect ~100%).
Usage: python3 baby4.py  (no args; 5 seeds fixed)"""
import random
from collections import defaultdict
ENT = {'mae': 'แม่', 'pho': 'พ่อ', 'cat': 'แมว', 'dog': 'หมา'}
ACT = {'come': 'มา', 'stay': 'อยู่', 'eat': 'กิน', 'sleep': 'นอน'}
M = list(ENT) + list(ACT)
def cls(m): return 'E' if m in ENT else 'A'
TEMPLATES = [
    'A: {E} {V} แล้ว นะ | B: ใช่ {E} {V} เลย',
    'A: ดู สิ {E} กำลัง {V} | B: เห็น แล้ว {E} {V} จริง',
    'A: {E} {V} ตรง นั้น | B: {E} {V} แล้ว จัง',
    'A: นั่น {E} {V} นะ | B: ใช่ ดู {E} กำลัง {V} อยู่ ตรง นี้',
    'A: {E} กำลัง {V} เลย | B: {E} {V} แล้ว เหรอ',
]
def dialogue(rng, e, a):
    t = rng.choice(TEMPLATES).format(E=ENT[e], V=ACT[a])
    return [w for w in t.replace('A:', ' ').replace('B:', ' ').replace('|', ' ').split() if w]
class Baby4:
    def __init__(s):
        s.assoc = defaultdict(lambda: defaultdict(float)); s.heard = 0
        s.oc = defaultdict(int)   # (class1, class2) order counts between grounded neighbors
        s.wb = defaultdict(int)   # (word1, word2) direct bigram counts
    def best(s, w):
        if w not in s.assoc: return None
        m, sc = max(s.assoc[w].items(), key=lambda kv: kv[1])
        tot = sum(max(0.0, v) for v in s.assoc[w].values())
        return m if sc > 0 and sc >= 1.5 * (tot - sc) else None  # confident grounding only
    def hear(s, words, e, a):
        present = {e, a}
        for w in words:
            s.heard += 1
            for m in M: s.assoc[w][m] += 1.0 if m in present else -0.25
        for w1, w2 in zip(words, words[1:]):
            s.wb[(w1, w2)] += 1
            m1, m2 = s.best(w1), s.best(w2)
            if m1 and m2: s.oc[(cls(m1), cls(m2))] += 1
    def word_for(s, m):
        best, bs = None, 0.5
        for w in s.assoc:
            sc = s.assoc[w][m] - 0.5 * sum(s.assoc[w][o] for o in M if o != m)
            if sc > bs: best, bs = w, sc
        return best
    def say2(s, e, a, arm):
        we, wa = s.word_for(e), s.word_for(a)
        if we is None or wa is None: return None
        if arm == 'class': fwd = s.oc[('E', 'A')] >= s.oc[('A', 'E')]
        elif arm == 'bigram':
            c_f, c_b = s.wb[(we, wa)], s.wb[(wa, we)]
            fwd = (random.random() < 0.5) if c_f == c_b else c_f > c_b  # novel pair: no bigram evidence -> coin flip
        else: fwd = random.random() < 0.5  # bag-of-words: right words, coin-flip order
        return (we, wa) if fwd else (wa, we)
def run(seed):
    rng = random.Random(1000 + seed)
    combos = [(e, a) for e in ENT for a in ACT]
    held = [(e, rng.choice(list(ACT))) for e in ENT]  # one novel pair per entity
    train = [c for c in combos if c not in held]
    random.Random(500 + seed).shuffle(train)
    b = Baby4()
    for _ in range(480):
        e, a = rng.choice(train)
        b.hear(dialogue(rng, e, a), e, a)
    res = {}
    for arm in ('class', 'bigram', 'bag'):
        res[arm] = sum(b.say2(e, a, arm) == (ENT[e], ACT[a]) for e, a in held)
    tr = sum(b.say2(e, a, 'class') == (ENT[e], ACT[a]) for e, a in train)
    grnd = sum(b.word_for(m) == (ENT | ACT)[m] for m in M)
    return held, res, tr, len(train), grnd, len(M), b.oc
if __name__ == '__main__':
    tot = {'class': 0, 'bigram': 0, 'bag': 0}; nd = 0
    for seed in range(5):
        held, res, tr, ntr, grnd, nm, oc = run(seed)
        print(f'seed{seed} held={[(e, a) for e, a in held]} class {res["class"]}/4 bigram {res["bigram"]}/4 bag {res["bag"]}/4 | trained-order {tr}/{ntr} grounding {grnd}/{nm} | order-counts E>A {oc[("E","A")]} A>E {oc[("A","E")]}', flush=True)
        for k in tot: tot[k] += res[k]
        nd += len(held)
    print(f'TOTAL held-out novel pairs: class {tot["class"]}/{nd} bigram {tot["bigram"]}/{nd} bag {tot["bag"]}/{nd} (chance ~{nd//2})')
    print('CRITERION: class >=', int(0.9 * nd), '=', 'MET' if tot['class'] >= 0.9 * nd else 'NOT MET')
