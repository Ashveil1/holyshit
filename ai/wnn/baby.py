"""BABY (Ash's caregiver experiment, small honest version).
World: 6 situation types (mother, father, milk, ball, cat, dog). Each interaction: a scene (one situation present,
plus noise: a second random situation co-present with p=0.3) and a caregiver utterance. Learner: from scratch,
no pretrained anything - Hebbian word<->situation association counts + production by best association.
Caregiver: scripted Thai; says the matching word with p=0.7 (else a random other word or silence).
Conditions: (1) single-word utterances, (2) words embedded in 2-4 word babble sentences (order/noise).
Controls: chance production; shuffled caregiver (negative control).
Pre-stated FIRST-WORD criterion: after day d, on 200 HELD-OUT scenes (fresh seed) for the most-taught word,
the learner produces that word in >=80% of matching scenes AND produces it in <=20% of 200 non-matching scenes.
Report: first day the criterion is met, per seed and condition; plus all-word held-out accuracy vs chance.
python3 baby.py"""
import random
from collections import defaultdict
SIT = {'mae': 'แม่', 'pho': 'พ่อ', 'nom': 'นม', 'ball': 'ลูกบอล', 'cat': 'แมว', 'dog': 'หมา'}
FILLER = ['จ๊ะ', 'นะ', 'ดู', 'สิ', 'เอา', 'ไหม', 'มา', 'กัน']
def scene(rng):
    s = rng.choice(list(SIT)); extra = rng.random() < 0.3
    s2 = rng.choice([x for x in SIT if x != s]) if extra else None
    return s, {s, s2} - {None}
def utter(rng, s, mode, shuffled):
    w = SIT[s] if not shuffled else SIT[rng.choice(list(SIT))]
    if rng.random() > 0.7: w = SIT[rng.choice(list(SIT))]
    if rng.random() < 0.1: return []
    if mode == 'single': return [w]
    n = rng.choice([2, 3, 4]); out = [w] + [rng.choice(FILLER) for _ in range(n - 1)]; rng.shuffle(out)
    return out
class Baby:
    def __init__(s): s.assoc = defaultdict(lambda: defaultdict(float)); s.wcnt = defaultdict(float)
    def hear(s, words, present):
        for w in words:
            s.wcnt[w] += 1
            for sit in SIT:
                s.assoc[w][sit] += 1.0 if sit in present else -0.25
    def say(s, present):
        best, bs = None, 0.5
        for w in SIT.values():
            sc = sum(s.assoc[w][sit] for sit in present) - 0.5 * sum(s.assoc[w][sit] for sit in SIT if sit not in present)
            if sc > bs: best, bs = w, sc
        return best
def run(mode, shuffled, seed, days=14, per_day=100):
    rng = random.Random(seed); b = Baby(); main_word_sit = 'mae'
    for d in range(1, days + 1):
        for _ in range(per_day):
            s, present = scene(rng); b.hear(utter(rng, s, mode, shuffled), present)
        r = random.Random(9000 + seed)
        hit = sum(b.say(scene(r,)[1] if False else p) == SIT[s] for s, p in (scene(r) for _ in range(200)))
        non = sum(b.say(p) == SIT[main_word_sit] for s, p in (scene(r) for _ in range(200)) if s != main_word_sit)
        mae = sum(b.say(p) == SIT['mae'] for s, p in (scene(r) for _ in range(200)) if s == 'mae')
        if d in (1, 3, 7, 14) or (mae / 200 >= 0.8 and non / 200 <= 0.2):
            pass
        if mae / 200 >= 0.8 and non / 200 <= 0.2:
            return d, mae / 200, non / 200, hit / 200
    return None, mae / 200, non / 200, hit / 200
if __name__ == '__main__':
    print('first-word = "แม่" produced in >=80% of held-out mother-scenes AND <=20% of non-mother scenes; 100 scenes/day')
    for mode in ('single', 'babble'):
        for shuf in (False, True):
            res = [run(mode, shuf, sd) for sd in range(5)]
            days = [r[0] for r in res]; allw = [r[3] for r in res]
            print(f'{mode:6s} shuffled={shuf}: first-word day {days} | all-6-words held-out acc {sum(allw)/5:.2f} (chance ~0.17)', flush=True)
