"""BABY2: two-caregiver version of the requester's experiment. Two scripted speakers (A,B) talk to EACH OTHER about a shared
simulated scene; the baby (from-scratch Hebbian associative learner, no pretrained anything) overhears. Once the baby
babbles words, caregivers reply contingently (correct word -> 'ใช่ <word>' + association boost; wrong -> 'ไม่ใช่' + penalty)
= Turing's reward channel on top of the language channel.
Conditions: 'single' (one-word utterances), 'dialogue' (two speakers, 2-4 word lines, echo replies). Control: shuffled.
FIRST-WORD criterion (pre-stated, fixed): on 200 held-out scenes, the baby produces แม่ in >=80% of mother-primary
scenes AND in <=20% of non-mother scenes. Also report: all-6-word held-out accuracy vs chance (~0.17), and the
contingent-reply effect (with vs without reward channel).
python3 baby2.py"""
import random
from collections import defaultdict
SIT = {'mae': 'แม่', 'pho': 'พ่อ', 'nom': 'นม', 'ball': 'ลูกบอล', 'cat': 'แมว', 'dog': 'หมา'}
FILLER = ['จ๊ะ', 'นะ', 'ดู', 'สิ', 'เอา', 'ไหม', 'มา', 'กัน', 'แล้ว', 'หน่อย']
def scene(rng):
    s = rng.choice(list(SIT)); s2 = rng.choice([x for x in SIT if x != s]) if rng.random() < 0.3 else None
    return s, {s, s2} - {None}
def word_for(rng, s, shuffled):
    w = SIT[rng.choice(list(SIT))] if shuffled or rng.random() > 0.7 else SIT[s]
    return w
def dialogue(rng, s, mode, shuffled):
    w = word_for(rng, s, shuffled)
    if rng.random() < 0.1: return []
    if mode == 'single': return [w]
    la = [w] + [rng.choice(FILLER) for _ in range(rng.choice([1, 2]))]; rng.shuffle(la)
    out = list(la)
    if rng.random() < 0.7:
        lb = [w if rng.random() < 0.8 else rng.choice(FILLER), rng.choice(FILLER)]; rng.shuffle(lb); out += lb
    return out
class Baby:
    def __init__(s): s.assoc = defaultdict(lambda: defaultdict(float)); s.wcnt = defaultdict(float); s.spoke = 0; s.heard = 0
    def hear(s, words, present):
        for w in words:
            s.wcnt[w] += 1; s.heard += 1
            for sit in SIT: s.assoc[w][sit] += 1.0 if sit in present else -0.25
    def reward(s, w, present, good):
        for sit in SIT:
            if w in SIT.values(): s.assoc[w][sit] += (2.0 if sit in present else -0.5) if good else (-1.0 if sit in present else 0.0)
    def say(s, present):
        best, bs = None, 0.5
        for w in SIT.values():
            sc = sum(s.assoc[w][sit] for sit in present) - 0.5 * sum(s.assoc[w][sit] for sit in SIT if sit not in present)
            if sc > bs: best, bs = w, sc
        return best
def run(mode, shuffled, reward_on, seed, days=14, per_day=100):
    rng = random.Random(seed); b = Baby()
    for d in range(1, days + 1):
        for _ in range(per_day):
            s, present = scene(rng); b.hear(dialogue(rng, s, mode, shuffled), present)
            if reward_on:
                w = b.say(present)
                if w is not None:
                    b.spoke += 1; good = w == SIT[s]
                    if reward_on == 'randfb': good = rng.random() < 0.5
                    if good:
                        echo = [w, rng.choice(FILLER)] if rng.random() < 0.8 else ['ใช่']
                        rng.shuffle(echo); b.hear(echo, present)   # reply as they reply to each other
                    elif reward_on != 'randfb': b.hear(['ไม่ใช่'], present)
                    b.reward(w, present, good)
        r = random.Random(9000 + seed)
        rows = [scene(r) for _ in range(200)]
        n_m = sum(1 for s, _ in rows if s == 'mae'); n_nm = 200 - n_m
        mae = sum(b.say(p) == SIT['mae'] for s, p in rows if s == 'mae') / max(1, n_m)
        non = sum(b.say(p) == SIT['mae'] for s, p in rows if s != 'mae') / max(1, n_nm)
        hit = sum(b.say(p) == SIT[s] for s, p in rows) / 200
        if mae >= 0.8 and non <= 0.2: return d, round(mae, 2), round(non, 2), round(hit, 2)
    return None, round(mae, 2), round(non, 2), round(hit, 2)
if __name__ == '__main__':
    print('criterion: >=80% of held-out mother scenes get "แม่", <=20% of other scenes; 100 scenes/day, 5 seeds')
    for mode in ('single', 'dialogue'):
        for shuf, rew in ((False, True), (False, False), (False, 'randfb'), (True, True), (True, 'randfb')):
            res = [run(mode, shuf, rew, sd) for sd in range(5)]
            print(f'{mode:8s} shuffled={shuf} reward={rew}: first-word day {[r[0] for r in res]} (mae/non {res[0][1]}/{res[0][2]}) | all-word acc {sum(r[3] for r in res)/5:.2f} vs chance ~0.17', flush=True)
