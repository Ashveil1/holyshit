"""B-187: negative examples - chit-chat with numbers but no op should be rejected (abstain).
Baseline always-answer. Rules: r1 abstain if no known features; r2 abstain if avg log-lik per feature < T.
Success: false-answer rate < 10% on chit-chat with op acc drop <= 2pts. tok n=150, 5 seeds."""
import math, random
from text2prog import Learner, gen_set, evaluate, HYP, run_hyp, feats, numbers_of
CHAT = ["i saw {a} birds in the park", "my friend has {a} cats and {b} dogs", "the meeting lasted {a} hours",
        "we walked {a} kilometers yesterday", "she bought {a} apples and {b} oranges for the party",
        "the movie starts at {a} pm", "there were {a} people at the concert", "his dog is {a} years old",
        "วัน นี้ อากาศ ดี มาก {a} คน มา เที่ยว", "เขา มี รถ {a} คัน สี แดง"]
def chat_rows(rng, n):
    return [rng.choice(CHAT).format(a=rng.randrange(1, 20), b=rng.randrange(1, 20)) for _ in range(n)]
def scored(L, text):
    fs = [f for f in feats(text, L.kind) if f in L.tot]
    best, bs = None, -1e18
    for h in HYP:
        sc = sum(math.log((L.cnt[f].get(h, 0) + 0.05) / (L.tot[f] + 0.05 * len(HYP))) for f in fs)
        if sc > bs: best, bs = h, sc
    return best, bs, len(fs)
def run(sd, T):
    rng = random.Random(sd)
    L = Learner('tok'); L.fit([(t, a) for _, t, a in gen_set(rng, 0, 150)])
    r = random.Random(100 + sd); rows = gen_set(r, 1, 300, big=True)
    op_ok = 0
    for _, text, ans in rows:
        h, sc, nf = scored(L, text)
        if nf == 0 or (nf and sc / nf < T): continue
        try: op_ok += run_hyp(h, numbers_of(text)) == ans
        except Exception: pass
    chats = chat_rows(random.Random(700 + sd), 300); false = 0
    for text in chats:
        h, sc, nf = scored(L, text)
        if nf == 0 or (nf and sc / nf < T): continue
        false += 1
    return op_ok / 300, false / 300
if __name__ == '__main__':
    for T in (-1e9, -2.5, -2.0, -1.5, -1.0):
        o, f = zip(*[run(sd, T) for sd in range(5)])
        print(f'T={T:>6}: op acc {sum(o)/5:.3f} | false-answer {sum(f)/5:.3f}', flush=True)
